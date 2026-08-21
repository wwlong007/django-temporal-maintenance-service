from django.test import SimpleTestCase

from maintenance_service.api.fields import (
    OffsetDateTimeField,
    WindowIdField,
    parse_offset_text,
    require_unique_window_ids,
    validate_operation_envelope,
)
from maintenance_service.api.serializers import (
    AvailabilitySerializer,
    WindowBatchSerializer,
    WindowCreateSerializer,
    WindowPatchSerializer,
)
from maintenance_service.application.responses import (
    availability_result,
    batch_result,
    serialize_interval,
    utc_text,
    write_result,
)


def weekly_rule():
    return {
        "start": "2026-01-05T09:00:00",
        "weekdays": ["MO"],
        "interval": 1,
        "duration_minutes": 60,
    }


def create_payload(window_id="db"):
    return {
        "window_id": window_id,
        "effective_from": "2026-01-01T00:00:00Z",
        "timezone": "UTC",
        "rule": weekly_rule(),
        "priority": 10,
    }


class FieldContractTests(SimpleTestCase):
    def test_offset_parser_accepts_z(self):
        self.assertEqual(parse_offset_text("2026-01-01T00:00:00Z").utcoffset().total_seconds(), 0)

    def test_offset_parser_accepts_numeric_offset(self):
        value = parse_offset_text("2026-01-01T09:00:00+09:00")
        self.assertEqual(value.utcoffset().total_seconds(), 9 * 3600)

    def test_offset_parser_rejects_naive_time(self):
        with self.assertRaises(Exception):
            parse_offset_text("2026-01-01T00:00:00")

    def test_window_id_trims_whitespace(self):
        self.assertEqual(WindowIdField().run_validation(" db "), "db")

    def test_window_id_rejects_blank(self):
        with self.assertRaises(Exception):
            WindowIdField().run_validation(" ")

    def test_offset_field_returns_datetime(self):
        value = OffsetDateTimeField().run_validation("2026-01-01T00:00:00Z")
        self.assertIsNotNone(value.tzinfo)

    def test_operation_envelope_accepts_create(self):
        value = {"type": "create", "window_id": "db"}
        self.assertIs(validate_operation_envelope(value), value)

    def test_operation_envelope_rejects_unknown_type(self):
        with self.assertRaises(Exception):
            validate_operation_envelope({"type": "delete", "window_id": "db"})

    def test_unique_window_ids_preserve_input(self):
        values = [{"window_id": "db"}, {"window_id": "cache"}]
        self.assertIs(require_unique_window_ids(values), values)

    def test_unique_window_ids_reject_duplicate(self):
        with self.assertRaises(Exception):
            require_unique_window_ids([{"window_id": "db"}, {"window_id": "db"}])


class SerializerContractTests(SimpleTestCase):
    def test_create_defaults_active(self):
        serializer = WindowCreateSerializer(data=create_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(serializer.validated_data["active"])

    def test_create_requires_offset(self):
        payload = create_payload()
        payload["effective_from"] = "2026-01-01T00:00:00"
        serializer = WindowCreateSerializer(data=payload)
        self.assertFalse(serializer.is_valid())

    def test_patch_accepts_sparse_priority(self):
        serializer = WindowPatchSerializer(
            data={
                "version": 1,
                "effective_from": "2026-01-01T00:00:00Z",
                "priority": 20,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_patch_requires_state_change(self):
        serializer = WindowPatchSerializer(
            data={"version": 1, "effective_from": "2026-01-01T00:00:00Z"}
        )
        self.assertFalse(serializer.is_valid())

    def test_patch_rejects_nonpositive_version(self):
        serializer = WindowPatchSerializer(
            data={
                "version": 0,
                "effective_from": "2026-01-01T00:00:00Z",
                "active": False,
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_availability_accepts_revision_zero(self):
        serializer = AvailabilitySerializer(
            data={
                "from_": "2026-01-01T00:00:00Z",
                "to": "2026-01-02T00:00:00Z",
                "revision": 0,
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_availability_rejects_long_range(self):
        serializer = AvailabilitySerializer(
            data={
                "from_": "2026-01-01T00:00:00Z",
                "to": "2027-02-01T00:00:00Z",
            }
        )
        self.assertFalse(serializer.is_valid())

    def test_batch_accepts_single_create(self):
        serializer = WindowBatchSerializer(
            data={"operations": [{"type": "create", **create_payload()}]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_batch_rejects_duplicate_window(self):
        serializer = WindowBatchSerializer(
            data={
                "operations": [
                    {"type": "create", **create_payload()},
                    {"type": "create", **create_payload()},
                ]
            }
        )
        self.assertFalse(serializer.is_valid())


class ResponseContractTests(SimpleTestCase):
    def test_utc_text_uses_z_suffix(self):
        value = parse_offset_text("2026-01-01T01:00:00+01:00")
        self.assertEqual(utc_text(value), "2026-01-01T00:00:00Z")

    def test_serialize_interval_keeps_flags(self):
        value = serialize_interval(
            {
                "start": parse_offset_text("2026-01-01T00:00:00Z"),
                "end": parse_offset_text("2026-01-01T01:00:00Z"),
                "maintenance": False,
                "available": True,
            }
        )
        self.assertTrue(value["available"])

    def test_availability_result_keeps_revision(self):
        value = availability_result(3, [])
        self.assertEqual(value, {"calendar_revision": 3, "intervals": []})

    def test_batch_result_uses_last_revision(self):
        value = batch_result(
            [
                {"window_id": "db", "calendar_revision": 1},
                {"window_id": "cache", "calendar_revision": 2},
            ]
        )
        self.assertEqual(value["calendar_revision"], 2)

    def test_write_result_uses_window_fields(self):
        window = type("Window", (), {"window_id": "db", "version": 4})()
        moment = parse_offset_text("2026-01-01T00:00:00Z")
        value = write_result(window, 7, moment)
        self.assertEqual(value["window_id"], "db")
        self.assertEqual(value["version"], 4)
        self.assertEqual(value["calendar_revision"], 7)

