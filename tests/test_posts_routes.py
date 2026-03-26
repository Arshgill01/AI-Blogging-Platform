import unittest

from app import create_app
from app import db
from app.models import Interaction, Post, VisitorSession
from app.services.seo_service import get_latest_post_analysis


class PostRoutesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        cls.client = cls.app.test_client()

    def test_detail_page_renders_related_posts_section(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Practical SEO Habits for Small Content Teams"
            ).first()

        response = self.client.get(f"/posts/{post.id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Related Articles", body)
        self.assertIn("Balancing Search Intent With Reader Intent in Tutorials", body)

    def test_analyze_route_persists_internal_links(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Designing a Lightweight Flask Admin for Writers"
            ).first()
            post_id = post.id

        response = self.client.post(f"/posts/{post_id}/analyze", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Internal Link Suggestions", body)

        with self.app.app_context():
            refreshed_post = db.session.get(Post, post_id)
            analysis = get_latest_post_analysis(refreshed_post)

        self.assertTrue(analysis["internal_links"])
        self.assertEqual(
            analysis["internal_links"][0]["title"],
            "Useful Python Scripts for Cleaning Blog Metadata",
        )

    def test_detail_page_renders_personalized_recommendations_and_logs_page_view(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Practical SEO Habits for Small Content Teams"
            ).first()
            existing_page_views = Interaction.query.filter_by(
                post_id=post.id, event_type="view"
            ).count()

        response = self.client.get(f"/posts/{post.id}")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Reader Personalization", body)
        self.assertIn("Recommended from your reading", body)

        with self.app.app_context():
            updated_page_views = Interaction.query.filter_by(
                post_id=post.id, event_type="view"
            ).count()
            session_count = VisitorSession.query.count()

        self.assertEqual(updated_page_views, existing_page_views + 1)
        self.assertGreaterEqual(session_count, 1)

    def test_recommendation_click_query_logs_click_event(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Designing a Lightweight Flask Admin for Writers"
            ).first()
            existing_clicks = Interaction.query.filter_by(
                post_id=post.id, event_type="recommendation_click"
            ).count()

        response = self.client.get(f"/posts/{post.id}?ref=personalized")

        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            updated_clicks = Interaction.query.filter_by(
                post_id=post.id, event_type="recommendation_click"
            ).count()

        self.assertEqual(updated_clicks, existing_clicks + 1)

    def test_detail_page_deduplicates_rapid_page_view_refreshes(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Topic Clusters That Make Internal Linking Easier"
            ).first()
            existing_page_views = Interaction.query.filter_by(
                post_id=post.id, event_type="view"
            ).count()

        first_response = self.client.get(f"/posts/{post.id}")
        second_response = self.client.get(f"/posts/{post.id}")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)

        with self.app.app_context():
            updated_page_views = Interaction.query.filter_by(
                post_id=post.id, event_type="view"
            ).count()

        self.assertEqual(updated_page_views, existing_page_views + 1)

    def test_engagement_endpoint_updates_view_dwell_time(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Why Fast Page Loads Improve Content Engagement"
            ).first()

        detail_response = self.client.get(f"/posts/{post.id}")
        self.assertEqual(detail_response.status_code, 200)

        response = self.client.post(
            f"/posts/{post.id}/engagement",
            json={"dwell_time_seconds": 42},
        )

        self.assertEqual(response.status_code, 204)

        with self.app.app_context():
            latest_view_event = (
                Interaction.query.filter_by(post_id=post.id, event_type="view")
                .order_by(Interaction.id.desc())
                .first()
            )

        self.assertEqual(latest_view_event.dwell_time, 42)

    def test_posts_index_redirects_to_home_listing(self):
        response = self.client.get("/posts/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

    def test_get_analyze_route_redirects_back_to_post(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Practical SEO Habits for Small Content Teams"
            ).first()

        response = self.client.get(f"/posts/{post.id}/analyze", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Open the post or author form to run SEO analysis.", response.get_data(as_text=True))

    def test_engagement_endpoint_ignores_invalid_dwell_time_payloads(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Why Fast Page Loads Improve Content Engagement"
            ).first()

        detail_response = self.client.get(f"/posts/{post.id}")
        self.assertEqual(detail_response.status_code, 200)

        response = self.client.post(
            f"/posts/{post.id}/engagement",
            json={"dwell_time_seconds": "not-a-number"},
        )

        self.assertEqual(response.status_code, 202)

        with self.app.app_context():
            latest_view_event = (
                Interaction.query.filter_by(post_id=post.id, event_type="view")
                .order_by(Interaction.id.desc())
                .first()
            )

        self.assertIsNone(latest_view_event.dwell_time)

    def test_missing_route_renders_demo_recovery_page(self):
        response = self.client.get("/definitely-missing-page")

        self.assertEqual(response.status_code, 404)
        body = response.get_data(as_text=True)
        self.assertIn("That page does not exist.", body)
        self.assertIn("Author Studio", body)


if __name__ == "__main__":
    unittest.main()
