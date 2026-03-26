import json
import tempfile
import unittest
from pathlib import Path

from app import create_app, db
from app.models import Interaction, Post, SEOReport
from app.services.seo_service import get_latest_seo_report
from app.services.similarity_service import get_internal_link_suggestions, get_related_posts


class SimilarityIntegrationTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
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

    def test_related_posts_are_serializable_and_exclude_self(self):
        post = Post.query.first()

        results = get_related_posts(post, limit=3)

        self.assertTrue(results)
        self.assertLessEqual(len(results), 3)
        self.assertNotIn(post.id, [item["post_id"] for item in results])
        json.dumps(results)

    def test_analyze_route_persists_internal_link_suggestions(self):
        post = Post.query.first()

        response = self.client.post(f"/posts/{post.id}/analyze", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        report = get_latest_seo_report(post)
        self.assertIsNotNone(report)

        internal_links = json.loads(report.internal_links_json)
        self.assertTrue(internal_links)
        self.assertIn("post_id", internal_links[0])
        self.assertIn("title", internal_links[0])

    def test_detail_and_edit_pages_render_similarity_sections(self):
        post = Post.query.first()

        detail_response = self.client.get(f"/posts/{post.id}")
        edit_response = self.client.get(f"/posts/{post.id}/edit")

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(edit_response.status_code, 200)
        self.assertIn(b"Related Articles", detail_response.data)
        self.assertIn(b"Internal Link Suggestions", detail_response.data)
        self.assertIn(b"Internal Link Suggestions", edit_response.data)

    def test_detail_page_handles_sparse_related_content(self):
        posts = Post.query.all()
        keep_post = posts[0]
        db.session.query(Interaction).delete()
        db.session.query(SEOReport).delete()
        for post in posts[1:]:
            db.session.delete(post)
        db.session.commit()

        related_posts = get_related_posts(keep_post, limit=3)
        internal_links = get_internal_link_suggestions(keep_post, limit=4)
        response = self.client.get(f"/posts/{keep_post.id}")

        self.assertEqual(related_posts, [])
        self.assertEqual(internal_links, [])
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"No closely related posts yet", response.data)
        self.assertIn(
            b"Save a few more posts to unlock internal link suggestions for this draft.",
            response.data,
        )


if __name__ == "__main__":
    unittest.main()
