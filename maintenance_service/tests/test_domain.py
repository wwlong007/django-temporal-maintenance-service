from datetime import datetime, timedelta, timezone

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from maintenance_service.domain.amendments import (
    apply_changes,
    contains_state_fields,
    merge_patch,
    object_delta,
    state_delta,
)
from maintenance_service.domain.calendar import interval_is_partition, maintenance_sources
from maintenance_service.domain.commit_protocol import describe_commit, operation_positions
from maintenance_service.domain.intervals import build_segments, partition
from maintenance_service.domain.local_time import exists, is_ambiguous, possible_bindings
from maintenance_service.domain.operations import (
    materialize_patch,
    normalize_batch,
    normalize_create,
    normalize_patch,
)
from maintenance_service.domain.query import AvailabilityQuery
from maintenance_service.domain.recurrence import WeeklyRule, expand_weekly
from maintenance_service.domain.rules import (
    parse_local_datetime,
    parse_timezone,
    validate_rule,
    validate_state,
)
from maintenance_service.domain.timeline import merge_records, resolved_snapshots
from maintenance_service.domain.types import (
    AmendmentRecord,
    AvailabilitySegment,
    Occurrence,
    OperationKind,
)


UTC = timezone.utc


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def rule(**changes):
    value = {
        "start": "2026-01-05T09:00:00",
        "weekdays": ["MO"],
        "interval": 1,
        "duration_minutes": 60,
    }
    value.update(changes)
    return value


def state(**changes):
    value = {
        "timezone": "UTC",
        "rule": rule(),
        "priority": 10,
        "active": True,
    }
    value.update(changes)
    return value


class MergePatchTests(SimpleTestCase):
    def test_scalar_is_replaced(self):
        self.assertEqual(merge_patch({"a": 1}, {"a": 2}), {"a": 2})

    def test_nested_object_is_merged(self):
        self.assertEqual(
            merge_patch({"rule": {"interval": 1, "count": 2}}, {"rule": {"count": 3}}),
            {"rule": {"interval": 1, "count": 3}},
        )

    def test_null_removes_a_key(self):
        self.assertEqual(merge_patch({"count": 4}, {"count": None}), {})

    def test_array_is_replaced(self):
        self.assertEqual(
            merge_patch({"weekdays": ["MO"]}, {"weekdays": ["TU", "WE"]}),
            {"weekdays": ["TU", "WE"]},
        )

    def test_inputs_are_not_mutated(self):
        target = {"rule": {"weekdays": ["MO"]}}
        patch = {"rule": {"weekdays": ["TU"]}}
        merge_patch(target, patch)
        self.assertEqual(target["rule"]["weekdays"], ["MO"])
        self.assertEqual(patch["rule"]["weekdays"], ["TU"])

    def test_state_changes_merge_rule_only(self):
        result = apply_changes(state(), {"rule": {"duration_minutes": 90}})
        self.assertEqual(result["rule"]["duration_minutes"], 90)
        self.assertEqual(result["rule"]["weekdays"], ["MO"])

    def test_object_delta_reports_removal(self):
        self.assertEqual(object_delta({"a": 1, "b": 2}, {"a": 1}), {"b": None})

    def test_state_delta_is_nested(self):
        previous = state()
        current = state(rule=rule(duration_minutes=120))
        self.assertEqual(state_delta(previous, current), {"rule": {"duration_minutes": 120}})

    def test_state_field_detection(self):
        self.assertTrue(contains_state_fields({"active": False}))
        self.assertFalse(contains_state_fields({"metadata": {}}))


class RuleValidationTests(SimpleTestCase):
    def test_valid_rule_is_normalized(self):
        self.assertEqual(validate_rule(rule())["start"], "2026-01-05T09:00:00")

    def test_offset_local_time_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_local_datetime("2026-01-05T09:00:00+00:00")

    def test_unknown_timezone_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_timezone("Mars/Olympus")

    def test_empty_weekdays_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_rule(rule(weekdays=[]))

    def test_duplicate_weekdays_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_rule(rule(weekdays=["MO", "MO"]))

    def test_nonpositive_interval_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_rule(rule(interval=0))

    def test_count_and_until_are_exclusive(self):
        with self.assertRaises(ValidationError):
            validate_rule(rule(count=2, until="2026-02-01T00:00:00"))

    def test_priority_must_be_integer(self):
        with self.assertRaises(ValidationError):
            validate_state(state(priority=True))

    def test_active_must_be_boolean(self):
        with self.assertRaises(ValidationError):
            validate_state(state(active=1))


class OperationTests(SimpleTestCase):
    def test_create_defaults_active(self):
        draft = normalize_create(
            {
                "window_id": "db",
                "effective_from": utc("2026-01-01T00:00:00Z"),
                "timezone": "UTC",
                "rule": rule(),
                "priority": 5,
            }
        )
        self.assertEqual(draft.kind, OperationKind.CREATE)
        self.assertTrue(draft.values["active"])

    def test_patch_keeps_only_state_fields(self):
        draft = normalize_patch(
            "db",
            {
                "version": 1,
                "effective_from": utc("2026-01-01T00:00:00Z"),
                "priority": 7,
            },
        )
        self.assertEqual(draft.values, {"priority": 7})

    def test_empty_patch_is_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_patch(
                "db",
                {"version": 1, "effective_from": utc("2026-01-01T00:00:00Z")},
            )

    def test_materialized_patch_has_complete_state(self):
        draft = normalize_patch(
            "db",
            {
                "version": 1,
                "effective_from": utc("2026-01-01T00:00:00Z"),
                "active": False,
            },
        )
        self.assertFalse(materialize_patch(draft, state()).values["active"])

    def test_batch_rejects_duplicate_window(self):
        create = {
            "type": "create",
            "window_id": "db",
            "effective_from": utc("2026-01-01T00:00:00Z"),
            "timezone": "UTC",
            "rule": rule(),
            "priority": 1,
        }
        with self.assertRaises(ValidationError):
            normalize_batch([create, create])

    def test_commit_shape_tracks_ids(self):
        draft = normalize_batch(
            [
                {
                    "type": "create",
                    "window_id": "db",
                    "effective_from": utc("2026-01-01T00:00:00Z"),
                    "timezone": "UTC",
                    "rule": rule(),
                    "priority": 1,
                }
            ]
        )
        shape = describe_commit(draft)
        self.assertEqual(shape.create_ids, ("db",))
        self.assertEqual(operation_positions(draft), {"db": 0})


class RecurrenceTests(SimpleTestCase):
    def test_weekly_rule_parses_duration(self):
        parsed = WeeklyRule.from_state(state())
        self.assertEqual(parsed.duration, timedelta(hours=1))

    def test_weekly_occurrence_is_expanded(self):
        values = expand_weekly(
            state(),
            utc("2026-01-05T00:00:00Z"),
            utc("2026-01-06T00:00:00Z"),
            "db",
        )
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].start, utc("2026-01-05T09:00:00Z"))

    def test_count_limits_occurrences(self):
        values = expand_weekly(
            state(rule=rule(count=2)),
            utc("2026-01-01T00:00:00Z"),
            utc("2026-02-01T00:00:00Z"),
            "db",
        )
        self.assertEqual(len(values), 2)

    def test_until_is_inclusive(self):
        values = expand_weekly(
            state(rule=rule(until="2026-01-12T09:00:00")),
            utc("2026-01-01T00:00:00Z"),
            utc("2026-01-20T00:00:00Z"),
            "db",
        )
        self.assertEqual(len(values), 2)

    def test_utc_local_time_exists(self):
        self.assertTrue(exists("2026-01-05T09:00:00", "UTC"))
        self.assertFalse(is_ambiguous("2026-01-05T09:00:00", "UTC"))
        self.assertEqual(len(possible_bindings("2026-01-05T09:00:00", "UTC")), 1)


class TimelineAndPartitionTests(SimpleTestCase):
    def test_snapshot_uses_latest_same_boundary_record(self):
        moment = utc("2026-01-01T00:00:00Z")
        records = [
            AmendmentRecord(moment, state(priority=1), 1, 1),
            AmendmentRecord(moment, state(priority=2), 2, 2),
        ]
        self.assertEqual(resolved_snapshots(records)[0].state["priority"], 2)

    def test_merge_records_carries_sparse_state(self):
        records = [
            AmendmentRecord(utc("2026-01-01T00:00:00Z"), state(), 1, 1),
            AmendmentRecord(utc("2026-02-01T00:00:00Z"), {"priority": 20}, 2, 2),
        ]
        self.assertEqual(merge_records(records)[1].state["priority"], 20)

    def test_partition_returns_available_range(self):
        values = partition(utc("2026-01-01T00:00:00Z"), utc("2026-01-01T02:00:00Z"), [])
        self.assertEqual(values[0]["available"], True)

    def test_higher_priority_wins(self):
        start = utc("2026-01-01T00:00:00Z")
        end = utc("2026-01-01T02:00:00Z")
        items = [
            Occurrence(start, end, 1, "low"),
            Occurrence(start + timedelta(minutes=30), end, 5, "high"),
        ]
        segments = build_segments(start, end, items)
        self.assertEqual([item.source_window_id for item in segments], ["low", "high"])

    def test_adjacent_equal_segments_merge(self):
        start = utc("2026-01-01T00:00:00Z")
        end = utc("2026-01-01T02:00:00Z")
        items = [
            Occurrence(start, start + timedelta(hours=1), 1, "db"),
            Occurrence(start + timedelta(hours=1), end, 1, "db"),
        ]
        self.assertEqual(len(build_segments(start, end, items)), 1)

    def test_segment_dict_has_exclusive_flags(self):
        item = AvailabilitySegment(
            utc("2026-01-01T00:00:00Z"),
            utc("2026-01-01T01:00:00Z"),
            "db",
        ).as_dict()
        self.assertTrue(item["maintenance"])
        self.assertFalse(item["available"])

    def test_partition_helpers(self):
        start = utc("2026-01-01T00:00:00Z")
        end = utc("2026-01-01T01:00:00Z")
        values = partition(start, end, [Occurrence(start, end, 1, "db")])
        self.assertTrue(interval_is_partition(values, start, end))
        self.assertEqual(maintenance_sources(values), {"db"})

    def test_query_normalizes_utc(self):
        query = AvailabilityQuery.from_values(
            {
                "from": datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))),
                "to": datetime(2026, 1, 2, tzinfo=timezone(timedelta(hours=2))),
            }
        )
        self.assertEqual(query.start.tzinfo, UTC)

    def test_query_rejects_reverse_range(self):
        with self.assertRaises(ValidationError):
            AvailabilityQuery.from_values(
                {
                    "from": utc("2026-01-02T00:00:00Z"),
                    "to": utc("2026-01-01T00:00:00Z"),
                }
            )

