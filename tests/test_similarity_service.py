import unittest

from app import create_app
from app.models import Post
from app.services.similarity_service import get_related_posts


class SimilarityServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )

    def test_related_posts_exclude_self_and_limit_results(self):
        with self.app.app_context():
            for post in Post.query.order_by(Post.id).all():
                results = get_related_posts(post)

                self.assertLessEqual(len(results), 3)
                self.assertNotIn(post.id, [result["post_id"] for result in results])
                self.assertEqual(
                    len(results),
                    len({result["post_id"] for result in results}),
                )

    def test_seo_post_prefers_other_seo_posts(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Practical SEO Habits for Small Content Teams"
            ).first()

            results = get_related_posts(post)
            titles = [result["title"] for result in results]

            self.assertIn(
                "Balancing Search Intent With Reader Intent in Tutorials",
                titles,
            )
            self.assertIn(
                "How Readability Supports Search Performance",
                titles,
            )
            self.assertTrue(all(result["match_strength"] == "strong" for result in results))

    def test_sparse_cluster_uses_explicit_fallbacks(self):
        with self.app.app_context():
            post = Post.query.filter_by(
                title="Topic Clusters That Make Internal Linking Easier"
            ).first()

            results = get_related_posts(post)

            self.assertGreaterEqual(len(results), 2)
            self.assertEqual(
                results[0]["title"],
                "Measuring Content Quality Beyond Pageviews",
            )
            self.assertTrue(any(result["match_strength"] == "fallback" for result in results[1:]))


if __name__ == "__main__":
    unittest.main()
