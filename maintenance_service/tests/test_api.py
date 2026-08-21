from rest_framework.test import APITestCase


class CalendarApiTests(APITestCase):
    endpoint = "/api/v1/organizations/acme/resources/db-1"

    def test_create_patch_and_read_current_availability(self):
        created = self.client.post(
            f"{self.endpoint}/maintenance-windows",
            {
                "window_id": "weekly-db",
                "effective_from": "2026-01-01T00:00:00Z",
                "timezone": "UTC",
                "rule": {
                    "start": "2026-01-05T01:00:00",
                    "weekdays": ["MO"],
                    "interval": 1,
                    "duration_minutes": 60,
                    "count": 4,
                },
                "priority": 10,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["calendar_revision"], 1)

        patched = self.client.patch(
            f"{self.endpoint}/maintenance-windows/weekly-db",
            {
                "version": 1,
                "effective_from": "2026-01-10T00:00:00Z",
                "rule": {"duration_minutes": 90},
            },
            format="json",
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data["version"], 2)
        self.assertEqual(patched.data["calendar_revision"], 2)

        current = self.client.get(
            f"{self.endpoint}/availability",
            {"from": "2026-01-01T00:00:00Z", "to": "2026-02-01T00:00:00Z"},
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data["calendar_revision"], 2)
        maintenance = [item for item in current.data["intervals"] if item["maintenance"]]
        self.assertEqual(len(maintenance), 4)
        self.assertEqual(maintenance[0]["start"], "2026-01-05T01:00:00Z")

    def test_revision_zero_is_all_available(self):
        response = self.client.get(
            f"{self.endpoint}/availability",
            {"from": "2026-01-01T00:00:00Z", "to": "2026-01-02T00:00:00Z", "revision": 0},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["calendar_revision"], 0)
        self.assertTrue(response.data["intervals"][0]["available"])

    def test_batch_accepts_multiple_window_operations(self):
        response = self.client.post(
            f"{self.endpoint}/maintenance-windows/batch",
            {
                "operations": [
                    {
                        "type": "create",
                        "window_id": "database",
                        "effective_from": "2026-01-01T00:00:00Z",
                        "timezone": "UTC",
                        "rule": {
                            "start": "2026-01-05T01:00:00",
                            "weekdays": ["MO"],
                            "interval": 1,
                            "duration_minutes": 60,
                        },
                        "priority": 10,
                    },
                    {
                        "type": "create",
                        "window_id": "network",
                        "effective_from": "2026-01-01T00:00:00Z",
                        "timezone": "UTC",
                        "rule": {
                            "start": "2026-01-05T03:00:00",
                            "weekdays": ["MO"],
                            "interval": 1,
                            "duration_minutes": 30,
                        },
                        "priority": 5,
                    },
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["results"]), 2)
