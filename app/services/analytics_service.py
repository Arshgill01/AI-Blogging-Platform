from collections import Counter, defaultdict
from datetime import timedelta

from app.models import Interaction, Post, SEOReport, VisitorSession, utcnow


VIEW_EVENT = "view"
RECOMMENDATION_CLICK_EVENT = "recommendation_click"
RECENT_ACTIVITY_DAYS = 7
ACTIVE_SESSION_WINDOW_DAYS = 7
TOP_POST_LIMIT = 5
TOP_CATEGORY_LIMIT = 6
SEO_SNAPSHOT_LIMIT = 8


def _safe_average(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 1)


def _build_latest_seo_map(reports):
    latest_by_post_id = {}
    ordered_reports = sorted(
        reports,
        key=lambda report: (
            report.post_id,
            report.created_at or utcnow(),
            report.id or 0,
        ),
        reverse=True,
    )
    for report in ordered_reports:
        latest_by_post_id.setdefault(report.post_id, report)
    return latest_by_post_id


def _normalize_timestamp(timestamp):
    if timestamp is None:
        return utcnow()
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=utcnow().tzinfo)
    return timestamp


class AnalyticsService:
    def get_dashboard_snapshot(self):
        posts = Post.query.order_by(Post.created_at.desc(), Post.id.desc()).all()
        sessions = VisitorSession.query.order_by(VisitorSession.last_seen.desc()).all()
        interactions = Interaction.query.order_by(Interaction.timestamp.desc(), Interaction.id.desc()).all()
        seo_reports = SEOReport.query.order_by(SEOReport.created_at.desc(), SEOReport.id.desc()).all()

        latest_seo_by_post_id = _build_latest_seo_map(seo_reports)
        post_metrics = self._build_post_metrics(posts, interactions, latest_seo_by_post_id)
        category_metrics = self._build_category_metrics(posts, post_metrics)

        summary = self._build_summary(posts, sessions, interactions, latest_seo_by_post_id)
        recent_activity = self._build_recent_activity(interactions)
        seo_snapshot = self._build_seo_snapshot(posts, latest_seo_by_post_id)
        highlights = self._build_highlights(post_metrics, category_metrics, summary)

        return {
            "summary": summary,
            "highlights": highlights,
            "top_posts": post_metrics[:TOP_POST_LIMIT],
            "category_metrics": category_metrics[:TOP_CATEGORY_LIMIT],
            "seo_snapshot": seo_snapshot[:SEO_SNAPSHOT_LIMIT],
            "recent_activity": recent_activity,
            "chart_data": {
                "top_posts": {
                    "labels": [item["title"] for item in post_metrics[:TOP_POST_LIMIT]],
                    "views": [item["view_count"] for item in post_metrics[:TOP_POST_LIMIT]],
                    "recommendation_clicks": [
                        item["recommendation_clicks"] for item in post_metrics[:TOP_POST_LIMIT]
                    ],
                },
                "categories": {
                    "labels": [item["category"] for item in category_metrics[:TOP_CATEGORY_LIMIT]],
                    "views": [item["view_count"] for item in category_metrics[:TOP_CATEGORY_LIMIT]],
                    "posts": [item["post_count"] for item in category_metrics[:TOP_CATEGORY_LIMIT]],
                },
                "recent_activity": recent_activity,
                "seo_scores": {
                    "labels": [item["title"] for item in seo_snapshot[:SEO_SNAPSHOT_LIMIT]],
                    "scores": [item["seo_score"] for item in seo_snapshot[:SEO_SNAPSHOT_LIMIT]],
                },
            },
            "has_interactions": bool(interactions),
            "has_seo_reports": bool(latest_seo_by_post_id),
        }

    def _build_summary(self, posts, sessions, interactions, latest_seo_by_post_id):
        active_session_threshold = utcnow() - timedelta(days=ACTIVE_SESSION_WINDOW_DAYS)
        total_views = sum(1 for interaction in interactions if interaction.event_type == VIEW_EVENT)
        recommendation_clicks = sum(
            1 for interaction in interactions if interaction.event_type == RECOMMENDATION_CLICK_EVENT
        )
        dwell_values = [interaction.dwell_time for interaction in interactions if interaction.dwell_time]
        seo_scores = [report.seo_score for report in latest_seo_by_post_id.values() if report.seo_score is not None]
        readability_scores = [
            report.readability_score
            for report in latest_seo_by_post_id.values()
            if report.readability_score is not None
        ]

        categories = sorted({(post.category or "Uncategorized") for post in posts})
        posts_with_seo = len(latest_seo_by_post_id)

        return {
            "total_posts": len(posts),
            "total_categories": len(categories),
            "total_sessions": len(sessions),
            "active_recent_sessions": sum(
                1
                for visitor_session in sessions
                if visitor_session.last_seen
                and _normalize_timestamp(visitor_session.last_seen) >= active_session_threshold
            ),
            "total_interactions": len(interactions),
            "total_views": total_views,
            "recommendation_clicks": recommendation_clicks,
            "avg_dwell_time": _safe_average(dwell_values),
            "avg_seo_score": _safe_average(seo_scores),
            "avg_readability": _safe_average(readability_scores),
            "seo_coverage_pct": round((posts_with_seo / len(posts) * 100), 1) if posts else 0.0,
        }

    def _build_post_metrics(self, posts, interactions, latest_seo_by_post_id):
        metrics_by_post_id = {
            post.id: {
                "post_id": post.id,
                "title": post.title,
                "category": post.category or "Uncategorized",
                "view_count": 0,
                "recommendation_clicks": 0,
                "interaction_count": 0,
                "avg_dwell_time": None,
                "engagement_score": 0.0,
                "seo_score": None,
                "readability_score": None,
                "word_count": None,
                "updated_at": post.updated_at or post.created_at,
            }
            for post in posts
        }
        dwell_by_post_id = defaultdict(list)

        for interaction in interactions:
            metric = metrics_by_post_id.get(interaction.post_id)
            if metric is None:
                continue

            metric["interaction_count"] += 1
            if interaction.event_type == VIEW_EVENT:
                metric["view_count"] += 1
            elif interaction.event_type == RECOMMENDATION_CLICK_EVENT:
                metric["recommendation_clicks"] += 1

            if interaction.dwell_time:
                dwell_by_post_id[interaction.post_id].append(interaction.dwell_time)

        for post in posts:
            metric = metrics_by_post_id[post.id]
            metric["avg_dwell_time"] = _safe_average(dwell_by_post_id.get(post.id, []))
            seo_report = latest_seo_by_post_id.get(post.id)
            if seo_report is not None:
                metric["seo_score"] = seo_report.seo_score
                metric["readability_score"] = seo_report.readability_score
                metric["word_count"] = seo_report.word_count

            dwell_score = (metric["avg_dwell_time"] or 0) / 60.0
            metric["engagement_score"] = round(
                metric["view_count"] * 1.0
                + metric["recommendation_clicks"] * 2.0
                + dwell_score * 0.4,
                1,
            )

        ranked_posts = sorted(
            metrics_by_post_id.values(),
            key=lambda item: (
                item["engagement_score"],
                item["view_count"],
                item["recommendation_clicks"],
                item["seo_score"] if item["seo_score"] is not None else -1,
                item["updated_at"] or utcnow(),
            ),
            reverse=True,
        )
        return ranked_posts

    def _build_category_metrics(self, posts, post_metrics):
        metrics_by_category = defaultdict(
            lambda: {
                "category": "Uncategorized",
                "post_count": 0,
                "view_count": 0,
                "interaction_count": 0,
                "recommendation_clicks": 0,
                "avg_dwell_time": None,
                "avg_seo_score": None,
            }
        )
        dwell_by_category = defaultdict(list)
        seo_by_category = defaultdict(list)

        for post in posts:
            category = post.category or "Uncategorized"
            metrics_by_category[category]["category"] = category
            metrics_by_category[category]["post_count"] += 1

        for post_metric in post_metrics:
            category = post_metric["category"] or "Uncategorized"
            category_metric = metrics_by_category[category]
            category_metric["view_count"] += post_metric["view_count"]
            category_metric["interaction_count"] += post_metric["interaction_count"]
            category_metric["recommendation_clicks"] += post_metric["recommendation_clicks"]
            if post_metric["avg_dwell_time"] is not None:
                dwell_by_category[category].append(post_metric["avg_dwell_time"])
            if post_metric["seo_score"] is not None:
                seo_by_category[category].append(post_metric["seo_score"])

        category_metrics = []
        for category, metric in metrics_by_category.items():
            metric["avg_dwell_time"] = _safe_average(dwell_by_category.get(category, []))
            metric["avg_seo_score"] = _safe_average(seo_by_category.get(category, []))
            category_metrics.append(metric)

        category_metrics.sort(
            key=lambda item: (
                item["view_count"],
                item["recommendation_clicks"],
                item["post_count"],
                item["category"],
            ),
            reverse=True,
        )
        return category_metrics

    def _build_recent_activity(self, interactions):
        today = utcnow().date()
        labels = []
        views = []
        recommendation_clicks = []
        lookup = Counter()

        for interaction in interactions:
            if interaction.timestamp is None:
                continue
            lookup[(interaction.timestamp.date(), interaction.event_type)] += 1

        for offset in range(RECENT_ACTIVITY_DAYS - 1, -1, -1):
            day = today - timedelta(days=offset)
            labels.append(day.strftime("%b %d"))
            views.append(lookup[(day, VIEW_EVENT)])
            recommendation_clicks.append(lookup[(day, RECOMMENDATION_CLICK_EVENT)])

        return {
            "labels": labels,
            "views": views,
            "recommendation_clicks": recommendation_clicks,
        }

    def _build_seo_snapshot(self, posts, latest_seo_by_post_id):
        snapshot = []
        for post in posts:
            report = latest_seo_by_post_id.get(post.id)
            if report is None:
                continue
            snapshot.append(
                {
                    "post_id": post.id,
                    "title": post.title,
                    "category": post.category or "Uncategorized",
                    "seo_score": round(report.seo_score, 1) if report.seo_score is not None else None,
                    "readability_score": (
                        round(report.readability_score, 1)
                        if report.readability_score is not None
                        else None
                    ),
                    "word_count": report.word_count,
                }
            )

        snapshot.sort(
            key=lambda item: (
                item["seo_score"] if item["seo_score"] is not None else -1,
                item["readability_score"] if item["readability_score"] is not None else -1,
                item["word_count"] if item["word_count"] is not None else -1,
            ),
            reverse=True,
        )
        return snapshot

    def _build_highlights(self, post_metrics, category_metrics, summary):
        top_post = post_metrics[0] if post_metrics else None
        top_category = category_metrics[0] if category_metrics else None

        return {
            "top_post_title": top_post["title"] if top_post else None,
            "top_post_views": top_post["view_count"] if top_post else 0,
            "top_category": top_category["category"] if top_category else None,
            "top_category_views": top_category["view_count"] if top_category else 0,
            "seo_signal": summary["avg_seo_score"],
        }


analytics_service = AnalyticsService()


def get_dashboard_snapshot():
    return analytics_service.get_dashboard_snapshot()


def get_home_snapshot():
    snapshot = get_dashboard_snapshot()
    summary = snapshot["summary"]
    highlights = snapshot["highlights"]
    return {
        "total_posts": summary["total_posts"],
        "total_sessions": summary["total_sessions"],
        "recommendation_clicks": summary["recommendation_clicks"],
        "average_seo_score": summary["avg_seo_score"] if summary["avg_seo_score"] is not None else "N/A",
        "top_category": highlights["top_category"],
    }
