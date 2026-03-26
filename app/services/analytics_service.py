from collections import Counter

from app.models import Interaction, Post, SEOReport, VisitorSession


VIEW_EVENT = "view"
RECOMMENDATION_CLICK_EVENT = "recommendation_click"


def _safe_average(values, digits=1):
    if not values:
        return 0
    return round(sum(values) / len(values), digits)


def _latest_report_scores():
    latest_reports = (
        SEOReport.query.order_by(SEOReport.created_at.desc(), SEOReport.id.desc()).all()
    )
    latest_scores = {}
    for report in latest_reports:
        latest_scores.setdefault(report.post_id, report.seo_score or 0)
    return latest_scores


def _build_top_posts(latest_scores, limit=5):
    posts = Post.query.order_by(Post.title.asc()).all()
    if not posts:
        return []

    view_counts = Counter()
    click_counts = Counter()
    dwell_times = {}

    for interaction in Interaction.query.all():
        if interaction.event_type == VIEW_EVENT:
            view_counts[interaction.post_id] += 1
            if interaction.dwell_time:
                dwell_times.setdefault(interaction.post_id, []).append(interaction.dwell_time)
        elif interaction.event_type == RECOMMENDATION_CLICK_EVENT:
            click_counts[interaction.post_id] += 1

    ranked = []
    for post in posts:
        ranked.append(
            {
                "post_id": post.id,
                "title": post.title,
                "category": post.category,
                "view_count": view_counts.get(post.id, 0),
                "recommendation_clicks": click_counts.get(post.id, 0),
                "avg_dwell_time": round(_safe_average(dwell_times.get(post.id, []), digits=0)),
                "seo_score": latest_scores.get(post.id),
            }
        )

    ranked.sort(
        key=lambda item: (
            item["view_count"],
            item["recommendation_clicks"],
            item["avg_dwell_time"],
            item["title"],
        ),
        reverse=True,
    )
    return ranked[:limit]


def _build_category_interest():
    interactions = Interaction.query.all()
    if not interactions:
        return []

    category_scores = Counter()
    for interaction in interactions:
        post = interaction.post
        if post is None:
            continue

        base = 1.0 if interaction.event_type == VIEW_EVENT else 1.35
        dwell_boost = min((interaction.dwell_time or 0) / 300.0, 0.45)
        category_scores[post.category] += base + dwell_boost

    ranked = [
        {
            "category": category,
            "score": round(score, 2),
        }
        for category, score in category_scores.most_common()
    ]
    return ranked


def _build_seo_snapshots(limit=6):
    reports = (
        SEOReport.query.order_by(SEOReport.created_at.desc(), SEOReport.id.desc()).all()
    )
    if not reports:
        return []

    latest_by_post = {}
    for report in reports:
        latest_by_post.setdefault(report.post_id, report)

    snapshots = []
    for report in latest_by_post.values():
        post = report.post
        if post is None:
            continue
        snapshots.append(
            {
                "post_id": post.id,
                "title": post.title,
                "category": post.category,
                "seo_score": round(report.seo_score or 0, 1),
                "readability_score": round(report.readability_score or 0, 1),
                "word_count": report.word_count or 0,
                "created_at": report.created_at,
            }
        )

    snapshots.sort(
        key=lambda item: (
            item["seo_score"],
            item["readability_score"],
            item["word_count"],
        ),
        reverse=True,
    )
    return snapshots[:limit]


def _build_recent_activity(limit=6):
    interactions = (
        Interaction.query.order_by(Interaction.timestamp.desc(), Interaction.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "post_id": interaction.post_id,
            "title": interaction.post.title if interaction.post else "Unknown post",
            "category": interaction.post.category if interaction.post else "Unknown",
            "event_type": interaction.event_type,
            "dwell_time": interaction.dwell_time,
            "timestamp": interaction.timestamp,
        }
        for interaction in interactions
    ]


def get_dashboard_data():
    total_posts = Post.query.count()
    total_interactions = Interaction.query.count()
    total_sessions = VisitorSession.query.count()
    total_reports = SEOReport.query.count()

    view_events = Interaction.query.filter_by(event_type=VIEW_EVENT).all()
    recommendation_clicks = Interaction.query.filter_by(
        event_type=RECOMMENDATION_CLICK_EVENT
    ).count()
    avg_dwell_time = round(
        _safe_average(
            [interaction.dwell_time for interaction in view_events if interaction.dwell_time],
            digits=0,
        )
    )

    latest_scores = _latest_report_scores()
    average_seo_score = round(_safe_average(list(latest_scores.values())), 1)

    top_posts = _build_top_posts(latest_scores)
    category_interest = _build_category_interest()

    return {
        "summary": {
            "total_posts": total_posts,
            "total_interactions": total_interactions,
            "total_sessions": total_sessions,
            "recommendation_clicks": recommendation_clicks,
            "avg_dwell_time": avg_dwell_time,
            "average_seo_score": average_seo_score,
            "top_category": category_interest[0]["category"] if category_interest else None,
            "seo_coverage": round((len(latest_scores) / total_posts) * 100, 1) if total_posts else 0,
            "total_reports": total_reports,
        },
        "top_posts": top_posts,
        "category_interest": category_interest,
        "seo_snapshots": _build_seo_snapshots(),
        "recent_activity": _build_recent_activity(),
    }


def get_home_snapshot():
    data = get_dashboard_data()
    summary = data["summary"]
    return {
        "total_posts": summary["total_posts"],
        "total_sessions": summary["total_sessions"],
        "recommendation_clicks": summary["recommendation_clicks"],
        "average_seo_score": summary["average_seo_score"],
        "top_category": summary["top_category"],
    }
