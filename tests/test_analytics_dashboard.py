import tempfile
import unittest
from pathlib import Path

from app import create_app, db
from app.models import Interaction, SEOReport
from app.services.analytics_service import get_dashboard_snapshot


class AnalyticsDashboardTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "analytics-test.db"
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            }
        )
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        self.temp_dir.cleanup()

    def test_dashboard_renders_seeded_metrics(self):
        snapshot = get_dashboard_snapshot()

        self.assertEqual(snapshot["summary"]["total_posts"], 16)
        self.assertEqual(snapshot["summary"]["total_sessions"], 6)
        self.assertEqual(snapshot["summary"]["active_recent_sessions"], 6)
        self.assertEqual(snapshot["summary"]["total_interactions"], 30)
        self.assertTrue(snapshot["top_posts"])

        response = self.client.get("/analytics/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Analytics dashboard", body)
        self.assertIn("Top post performance", body)
        self.assertIn("6 active in 7d", body)

    def test_dashboard_handles_sparse_data_states(self):
        db.session.query(Interaction).delete()
        db.session.query(SEOReport).delete()
        db.session.commit()

        snapshot = get_dashboard_snapshot()
        self.assertFalse(snapshot["has_interactions"])
        self.assertFalse(snapshot["has_seo_reports"])

        response = self.client.get("/analytics/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("No interaction data yet. Browse posts to start filling this chart.", body)
        self.assertIn("Run SEO analysis on posts to populate this quality snapshot.", body)


if __name__ == "__main__":
    unittest.main()
