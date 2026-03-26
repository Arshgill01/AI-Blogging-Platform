import unittest

from app import create_app
from app import db
from app.models import Post
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


if __name__ == "__main__":
    unittest.main()
