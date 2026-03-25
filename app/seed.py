import json
from datetime import timedelta

import click

from app import db
from app.models import Interaction, Post, SEOReport, VisitorSession, utcnow


SEED_POSTS = [
    {
        "title": "Practical SEO Habits for Small Content Teams",
        "category": "SEO",
        "tags": "seo,content operations,editorial workflow,on-page seo",
        "meta_description": "A realistic SEO workflow for small publishing teams that need consistent wins without enterprise tooling.",
        "content": (
            "Small content teams rarely fail because they lack ideas. They fail because every post is built from scratch, every editor uses a different checklist, and nobody can tell whether a page is improving over time. A practical SEO habit starts before writing. The team should agree on a primary phrase, a reader intent, and one measurable goal for the page. That simple alignment reduces vague posts and makes later optimization much easier.\n\n"
            "The next habit is structural consistency. Writers should know how long an introduction needs to be, when a heading should answer a question directly, and how to place examples that keep the reader moving. Search visibility often improves when pages feel easier to scan, not when they are stuffed with repeated terms. Clear subheads, useful transitions, and descriptive meta descriptions help both readers and future editors understand the role of the post.\n\n"
            "Review cycles also matter. Instead of asking whether a draft sounds smart, ask whether it covers the topic deeply enough to deserve ranking. Does it define the problem, compare options, and give a next step? Can the title promise be understood in a search result? Can a related internal article naturally support the reader? These questions make the content library stronger over time because each post becomes part of a system instead of a one-off asset.\n\n"
            "For an MVP blogging platform, this kind of content is useful because it contains repeated but not identical SEO vocabulary. Terms like title tags, internal links, search intent, and readability appear in context. That overlap creates strong material for keyword extraction and related-post retrieval while still feeling like a believable article a real team might publish."
        ),
    },
    {
        "title": "Writing Meta Descriptions That Earn the Click",
        "category": "SEO",
        "tags": "meta descriptions,click-through rate,search snippets,copywriting",
        "meta_description": "How to write concise meta descriptions that set expectations and improve search click-through rate.",
        "content": (
            "A meta description does not guarantee rankings, but it often decides whether a searcher bothers to visit the page. That makes it a conversion surface, not just an SEO field to fill out at the end. Good descriptions summarize the value of the article in plain language, reflect the actual content on the page, and give the reader a reason to click now instead of later.\n\n"
            "Weak descriptions usually fail in predictable ways. Some are too generic, repeating a title without adding context. Others read like internal notes written by the author rather than copy intended for a busy reader. A strong version typically mentions the audience, the problem, and the outcome in one compact block. If an article explains internal linking for editors, the description should say so directly rather than hiding the point behind marketing language.\n\n"
            "There is also a useful relationship between meta descriptions and editorial quality. When a writer struggles to describe a page in one or two sentences, the post itself may be unfocused. Drafting the snippet early can expose that problem. It forces the team to ask what promise the article is making and whether the body actually delivers on it.\n\n"
            "In a seeded content corpus, meta-description-focused posts help future analysis features because they contain language about snippets, CTR, search results, and editorial clarity. They are close enough to broader SEO topics to be linked together, but distinct enough to create meaningful similarity gradients instead of duplicate documents."
        ),
    },
    {
        "title": "How Readability Supports Search Performance",
        "category": "SEO",
        "tags": "readability,seo,editing,user experience,content quality",
        "meta_description": "Readable articles often perform better because they keep readers engaged and make information easier to absorb.",
        "content": (
            "Readability is often discussed like a cosmetic concern, but it has a direct effect on whether readers stay with a page long enough to get value from it. When sentences run too long, paragraphs stack too densely, or transitions feel abrupt, the article creates friction. A reader who struggles to follow the argument is less likely to keep scrolling, share the piece, or return for another article in the same category.\n\n"
            "Search-focused teams sometimes assume that writing for algorithms requires complexity. In practice, clear language usually wins. A readable post can still be specific, technical, and nuanced. The difference is that the writer introduces terms carefully, varies sentence length, and breaks the page into digestible sections. This makes it easier for both humans and editorial tools to identify the main themes of the article.\n\n"
            "Readability also improves maintenance. When a post is easy to skim, an editor can quickly update examples, refresh a recommendation, or spot outdated phrasing. That matters for growing content libraries because even strong posts decay if nobody can revise them efficiently. A simple style system turns optimization into an ongoing process instead of an annual cleanup project.\n\n"
            "For this blogging platform, readability-oriented content gives the future SEO module useful material to score. It contains sentence-level language, editorial guidance, and overlapping terminology with other SEO and blogging posts. That makes it valuable for both machine-readable analysis and demo-friendly explanations."
        ),
    },
    {
        "title": "Editorial Calendars That Keep a Blog Consistent",
        "category": "Blogging",
        "tags": "blogging,editorial calendar,content planning,publishing cadence",
        "meta_description": "A lightweight editorial calendar can improve consistency, topic balance, and publishing confidence for small blogs.",
        "content": (
            "Consistency is one of the hardest parts of blogging because it depends on planning, not inspiration. Teams often publish in bursts, then go quiet for weeks when urgent work takes over. An editorial calendar solves part of that problem by turning vague intent into visible commitments. Even a simple calendar with topic, target audience, status, and publish date can prevent the blog from drifting into reactive posting.\n\n"
            "The best calendars also protect variety. Without a deliberate plan, a blog can easily overproduce one familiar topic and ignore related categories that readers care about. A balanced calendar helps the team mix tutorial content, opinion pieces, tactical guides, and product education. Over time that variety makes the site more useful for readers and better connected for internal linking.\n\n"
            "Another advantage is that a calendar exposes bottlenecks. If every piece waits on the same editor or subject expert, deadlines will slip no matter how strong the ideas are. Seeing the workflow in one place helps the team split responsibilities and identify which posts are blocked by research, drafting, or review. That makes publishing more predictable.\n\n"
            "This seeded article supports later platform features because it shares concepts with content marketing and SEO posts while keeping a distinct blogging angle. Terms like publishing cadence, topic clusters, editorial workflow, and internal linking create healthy overlap without collapsing every post into the same voice."
        ),
    },
    {
        "title": "When to Refresh an Old Blog Post Instead of Writing a New One",
        "category": "Blogging",
        "tags": "content refresh,blogging,content strategy,evergreen content",
        "meta_description": "Learn when refreshing an existing article is more valuable than producing a brand-new post.",
        "content": (
            "Publishing a new article feels productive, but it is not always the best use of editorial time. Many blogs already have underperforming posts with decent foundations: the topic is relevant, the structure is acceptable, and the search intent is clear. What they lack is freshness. Updating these pieces can be faster and more effective than adding another article that competes for the same audience.\n\n"
            "A practical refresh decision starts with three questions. Is the topic still important to your readers? Does the existing URL have any traction through search, links, or internal references? Can the post be improved with better examples, clearer headings, or more current advice? If the answer is yes, the team should consider revision before expansion.\n\n"
            "Refreshing content also benefits site architecture. Existing posts may already be linked from newsletters, category pages, or related articles. Strengthening that page preserves those connections and can improve the usefulness of your internal link graph. A new post has to earn those connections from scratch.\n\n"
            "For the seeded platform corpus, refresh-oriented content creates a realistic bridge between SEO, blogging, and analytics themes. It talks about URLs, performance, internal references, and editorial tradeoffs in a way that is believable for a content team and helpful for later recommendation systems."
        ),
    },
    {
        "title": "Building Trust With a Clear Author Voice",
        "category": "Blogging",
        "tags": "author voice,blog writing,brand trust,editorial style",
        "meta_description": "A consistent author voice helps a blog feel credible, memorable, and easier to read.",
        "content": (
            "Readers notice voice long before they articulate it. A clear author voice does not mean every post sounds identical, but it does mean the publication feels coherent. The blog should have a recognizable way of explaining ideas, handling nuance, and making recommendations. That consistency builds trust because the reader learns what kind of experience to expect.\n\n"
            "Voice is especially important for technical content. Many useful articles lose readers because they swing between jargon-heavy paragraphs and casual filler without a stable tone. A stronger approach is to keep the language direct, define terms when needed, and use examples that make the advice concrete. Readers stay engaged when the piece feels knowledgeable without becoming performative.\n\n"
            "Editorial teams can support voice by documenting simple rules. Decide whether the publication prefers short introductions, whether headings should be written as promises or questions, and how strongly the writer should recommend specific tools. These choices help guest contributors and new team members sound like part of the same publication.\n\n"
            "This post adds a softer but still practical angle to the corpus. It shares language with readability and content marketing articles while remaining distinct enough to create a meaningful topical cluster around blogging craft."
        ),
    },
    {
        "title": "Choosing AI Writing Tools Without Losing Editorial Control",
        "category": "AI Tools",
        "tags": "ai tools,editorial workflow,content quality,automation",
        "meta_description": "AI writing tools work best when they support editorial teams instead of replacing judgment and review.",
        "content": (
            "AI writing tools are attractive because they promise speed, but speed alone does not improve a content operation. A team still needs editorial standards, clear briefs, and human review. Without those guardrails, automated drafting can flood a blog with generic material that sounds polished at first glance but adds little value for readers.\n\n"
            "A better evaluation framework starts with workflow fit. Can the tool help outline an article, summarize interview notes, or suggest alternate headlines? Can editors see where machine assistance was useful and where it introduced risk? These questions are more practical than abstract debates about whether AI should be used at all. Most teams benefit from selective assistance, not full automation.\n\n"
            "Editorial control also depends on the source material. If your platform is self-contained, the safest AI-assisted workflows are grounded in internal documents, published posts, and structured notes. That reduces factual drift and keeps recommendations aligned with your own content library. It also creates better opportunities for internal linking because the system understands the topics you already cover.\n\n"
            "This article supports later recommendation features because it overlaps with blogging, content marketing, and Python automation topics. Terms like workflow, automation, internal content, and review create natural connections across the seeded corpus."
        ),
    },
    {
        "title": "Prompt Libraries for Repeatable Content Operations",
        "category": "AI Tools",
        "tags": "prompt design,ai tools,content operations,workflow systems",
        "meta_description": "A prompt library helps teams turn ad hoc AI usage into a repeatable and reviewable content workflow.",
        "content": (
            "Teams usually begin using prompts in an informal way. One editor keeps a few lines in a notes app, another copies prompts from old chat history, and nobody knows which version produced the best result. A prompt library turns that messy practice into a shared operational asset. It gives the team a place to store templates for outlining, summarizing, repurposing, and editing content.\n\n"
            "The value is not only convenience. A library creates consistency and auditability. Editors can compare prompt versions, note which instructions produce cleaner outputs, and decide when a prompt should reference title, category, audience, or internal examples. That makes AI assistance easier to evaluate because the workflow becomes visible instead of improvised.\n\n"
            "Prompt libraries work best when each entry has a clear job. One prompt might generate headline variations for a Python tutorial, while another reframes a long article into newsletter copy. The point is to reduce blank-page friction without hiding the need for editorial review. Teams should still refine tone, verify claims, and align the result with the rest of the site.\n\n"
            "For the platform corpus, prompt-library content adds operational AI vocabulary that relates to writing and process rather than software engineering alone. That widens the recommendation graph while preserving coherent topic overlap."
        ),
    },
    {
        "title": "Using AI Summaries to Repurpose Long-Form Posts",
        "category": "AI Tools",
        "tags": "ai summaries,content repurposing,long-form content,editorial efficiency",
        "meta_description": "AI summaries can help teams turn long-form articles into shorter assets without starting from zero.",
        "content": (
            "Long-form articles often contain enough material for several smaller assets, but repurposing them manually can be tedious. AI summaries help by extracting the main points, surfacing repeated themes, and suggesting alternate formats such as email copy, social blurbs, or section previews. That saves time when the source article is already strong and the team wants to extend its reach.\n\n"
            "The key is to treat summarization as a drafting step, not a finished output. Good summaries preserve the core argument and reflect the tone of the original article, but they still need editorial shaping. A short email teaser should emphasize urgency differently than a blog excerpt, and a social post may need a more focused hook than the article introduction.\n\n"
            "Repurposing also improves the value of your content archive. When teams revisit older posts for summaries, they often discover opportunities to refresh examples, strengthen headings, or add internal links to newer material. That turns every reuse cycle into a lightweight content audit.\n\n"
            "This seeded article strengthens the AI Tools cluster while staying connected to blogging and content marketing. It introduces terms like summaries, repurposing, archive value, and long-form content that are useful for both semantic similarity and future personalization."
        ),
    },
    {
        "title": "Topic Clusters That Make Internal Linking Easier",
        "category": "Content Marketing",
        "tags": "topic clusters,internal linking,content marketing,site structure",
        "meta_description": "Organizing posts into topic clusters makes planning, internal linking, and content discovery more effective.",
        "content": (
            "Topic clusters are useful because they give a content library shape. Instead of publishing isolated posts, the team defines a central theme and surrounds it with supporting articles that answer adjacent questions. Readers can move from broad concepts to more specific tactics without leaving the site, and editors gain a clearer map of where future articles should fit.\n\n"
            "Internal linking becomes much easier when those relationships are planned upfront. A pillar article about content strategy can naturally link to supporting posts on editorial calendars, content refreshes, SEO workflows, and analytics. Those links feel helpful rather than forced because the topics already belong together. Search engines also receive a stronger signal about the structure of the site.\n\n"
            "Clusters improve planning discipline as well. When a team knows it is building around a theme, it can avoid duplicate articles and identify gaps earlier. Maybe there is a strong beginner guide but no tactical post for advanced readers. Maybe the SEO category is dense while the AI Tools category still needs connective content. Clusters make those imbalances visible.\n\n"
            "This post is deliberately central within the seed corpus. It overlaps with multiple categories and creates strong candidates for related-post retrieval, which makes it valuable for demoing internal link suggestions later."
        ),
    },
    {
        "title": "Measuring Content Quality Beyond Pageviews",
        "category": "Content Marketing",
        "tags": "content metrics,engagement,pageviews,content marketing,analytics",
        "meta_description": "Pageviews matter, but quality content programs also track engagement, revisit behavior, and content usefulness.",
        "content": (
            "Pageviews are easy to report, which is why they dominate many content discussions. The problem is that they flatten every outcome into one number. A post that attracts curiosity clicks but sends readers away quickly is not providing the same value as a post that earns fewer visits but deeper engagement. Teams need a broader view if they want to understand content quality honestly.\n\n"
            "Useful metrics often come from behavior patterns. Time on page can suggest whether readers actually consume an article. Repeat visits can indicate trust. Recommendation clicks can show that the content journey is working rather than ending after one page. Even a simple view of category popularity can help editors decide where the audience is leaning right now.\n\n"
            "The point is not to build a surveillance-heavy analytics stack. It is to create a small set of signals that reflect usefulness and momentum. These signals become especially powerful when connected to editorial decisions. If readable Python tutorials hold attention while vague opinion posts underperform, the team has a clear direction for the next publishing cycle.\n\n"
            "Within the seed corpus, this article gives later dashboard work natural language around engagement, dwell time, and category performance. It also strengthens the bridge between content strategy and personalization topics."
        ),
    },
    {
        "title": "Useful Python Scripts for Cleaning Blog Metadata",
        "category": "Python",
        "tags": "python,metadata,automation,blog maintenance,data cleanup",
        "meta_description": "Python can automate repetitive metadata cleanup tasks across a growing blog archive.",
        "content": (
            "As a blog grows, metadata problems multiply quietly. Titles drift in style, tags become inconsistent, and meta descriptions are left blank on otherwise solid posts. Python is a good fit for this kind of maintenance because the work is repetitive, the rules are usually clear, and the output can be reviewed before changes are applied. Small scripts can save editors hours of manual cleanup.\n\n"
            "A metadata cleanup script does not need to be complex. It might flag descriptions that are too short, normalize tag casing, or identify posts missing a category. If the content lives in a database, the script can generate a review report before making updates. That keeps the process transparent and reduces the risk of accidental bulk edits.\n\n"
            "This type of automation is valuable for content teams because it creates leverage without replacing judgment. Editors still decide whether a title should change or whether two tags mean the same thing. The script simply surfaces the work in a structured way.\n\n"
            "For the seeded platform, Python-maintenance content overlaps with SEO, web development, and AI operations posts while introducing a more technical vocabulary around scripts, cleanup, and data hygiene. That makes the corpus more realistic and useful for recommendation experiments."
        ),
    },
    {
        "title": "Designing a Lightweight Flask Admin for Writers",
        "category": "Python",
        "tags": "flask,python,admin ui,writer workflow,content management",
        "meta_description": "A lightweight Flask admin can give writers a focused interface without turning the project into a full CMS.",
        "content": (
            "Not every content platform needs a complex admin panel. For many internal tools, a lightweight Flask interface is enough. Writers need a place to create posts, edit metadata, and review analysis results without being distracted by enterprise features they will never use. A smaller admin also reduces implementation risk because the team can focus on the flows that matter most.\n\n"
            "The best lightweight admin interfaces are opinionated. They present a clear form, sensible defaults, and immediate feedback after save. If a writer can add a title, content, category, tags, and meta description in one focused screen, the platform already supports most of the MVP author experience. Additional features can be added later when usage patterns justify them.\n\n"
            "Flask is well suited to this approach because the routing, templating, and database layers stay easy to reason about. The code can remain close to the product behavior, which helps when different agents are extending SEO analysis, recommendation logic, or analytics in parallel.\n\n"
            "This article intentionally mirrors the project stack. It provides believable internal content about Flask and writer workflows, which is useful for both demo coherence and future similarity ranking."
        ),
    },
    {
        "title": "Component Patterns for Faster Blog Page Builds",
        "category": "Web Development",
        "tags": "web development,components,frontend patterns,design systems,blog ui",
        "meta_description": "Reusable UI components help blog teams ship pages faster while keeping the reading experience consistent.",
        "content": (
            "Front-end consistency is often treated as a design concern, but it also affects publishing speed. When a blog relies on a small set of predictable components for cards, callouts, post metadata, and section layouts, teams spend less time reinventing presentation details. That makes it easier to launch new pages without introducing visual drift.\n\n"
            "Component patterns are especially helpful when several contributors work on the same site. A writer or developer can assemble a familiar page structure from existing building blocks rather than improvising every template. Readers benefit too because recurring patterns make the interface easier to scan. They know where to find post summaries, category labels, and navigation cues.\n\n"
            "The goal is not to create a rigid design system for its own sake. The goal is to remove unnecessary variability so the content can stand out. A few reusable patterns often do more for a blog than a large collection of special-case templates.\n\n"
            "In this seeded content set, component-focused writing creates useful overlap with Flask admin and content strategy posts while expanding the web development cluster beyond purely backend topics."
        ),
    },
    {
        "title": "Why Fast Page Loads Improve Content Engagement",
        "category": "Web Development",
        "tags": "performance,web development,page speed,engagement,user experience",
        "meta_description": "Page speed affects engagement because slow experiences interrupt the reader before the content can do its job.",
        "content": (
            "A blog post can be well written and still underperform if the page is slow to load. Readers make quick judgments about responsiveness, especially on mobile devices or unstable connections. If the headline appears late, the layout shifts, or the first interaction feels delayed, many visitors will leave before they evaluate the content itself.\n\n"
            "Performance work does not have to begin with sophisticated optimization. A team can usually make progress by reducing unnecessary assets, serving simpler templates, and avoiding heavy front-end behaviors on content pages. The best-performing blog pages often feel calm because they prioritize readable text and a few useful interface elements instead of layering on effects that compete with the article.\n\n"
            "Speed also amplifies the value of other content investments. A strong SEO title matters more when the reader who clicks can actually reach the page quickly. Internal recommendations work better when the next post opens without friction. Engagement metrics become more meaningful when abandonment is not driven by basic performance issues.\n\n"
            "This article gives the corpus a web-performance angle that still connects to SEO and analytics. It adds vocabulary like page speed, mobile experience, and engagement, which helps future feature work build more convincing relationships between posts."
        ),
    },
    {
        "title": "Balancing Search Intent With Reader Intent in Tutorials",
        "category": "SEO",
        "tags": "search intent,reader intent,tutorial writing,seo,content strategy",
        "meta_description": "Great tutorials satisfy search demand without losing sight of the reader's actual problem and context.",
        "content": (
            "Search intent is a useful framing device, but it becomes limiting when teams treat it like the only signal that matters. Tutorials perform best when they balance what people search for with what they truly need after the click. A reader may search for a narrow technical phrase, yet still need background context, decision criteria, or links to next-step articles once they land on the page.\n\n"
            "That is why strong tutorial writing often combines precision with empathy. The title and headings should align with the query, but the body should acknowledge the reader's situation. Are they a beginner trying to avoid mistakes? Are they an editor building a repeatable process? Are they comparing approaches rather than looking for one instruction? The article becomes more useful when it answers those underlying needs.\n\n"
            "Balancing intent also improves internal linking opportunities. If the tutorial recognizes adjacent questions, it can naturally point readers to deeper posts on metadata cleanup, editorial planning, or AI-assisted workflows. Those links support the session journey without feeling bolted on for SEO alone.\n\n"
            "This final SEO article is intentionally connective. It reinforces shared vocabulary across tutorial content, search strategy, and user experience, which should make later similarity results more believable."
        ),
    },
]

SEED_SESSIONS = [
    {
        "session_token": "reader-seo-ops",
        "first_seen_offset_days": 18,
        "last_seen_offset_days": 1,
        "interactions": [
            ("Practical SEO Habits for Small Content Teams", "view", 320, 18),
            ("Writing Meta Descriptions That Earn the Click", "view", 250, 17),
            ("How Readability Supports Search Performance", "view", 280, 15),
            ("Topic Clusters That Make Internal Linking Easier", "recommendation_click", 210, 12),
            ("Balancing Search Intent With Reader Intent in Tutorials", "view", 300, 2),
        ],
    },
    {
        "session_token": "reader-content-strategy",
        "first_seen_offset_days": 16,
        "last_seen_offset_days": 3,
        "interactions": [
            ("Editorial Calendars That Keep a Blog Consistent", "view", 340, 16),
            ("When to Refresh an Old Blog Post Instead of Writing a New One", "view", 295, 14),
            ("Topic Clusters That Make Internal Linking Easier", "view", 360, 10),
            ("Measuring Content Quality Beyond Pageviews", "view", 265, 7),
            ("Building Trust With a Clear Author Voice", "recommendation_click", 220, 3),
        ],
    },
    {
        "session_token": "reader-ai-workflows",
        "first_seen_offset_days": 12,
        "last_seen_offset_days": 1,
        "interactions": [
            ("Choosing AI Writing Tools Without Losing Editorial Control", "view", 310, 12),
            ("Prompt Libraries for Repeatable Content Operations", "view", 335, 11),
            ("Using AI Summaries to Repurpose Long-Form Posts", "view", 290, 8),
            ("Useful Python Scripts for Cleaning Blog Metadata", "recommendation_click", 205, 5),
            ("Designing a Lightweight Flask Admin for Writers", "view", 245, 1),
        ],
    },
    {
        "session_token": "reader-python-builder",
        "first_seen_offset_days": 11,
        "last_seen_offset_days": 4,
        "interactions": [
            ("Useful Python Scripts for Cleaning Blog Metadata", "view", 355, 11),
            ("Designing a Lightweight Flask Admin for Writers", "view", 315, 10),
            ("Component Patterns for Faster Blog Page Builds", "view", 225, 8),
            ("Why Fast Page Loads Improve Content Engagement", "recommendation_click", 185, 6),
            ("Balancing Search Intent With Reader Intent in Tutorials", "view", 205, 4),
        ],
    },
    {
        "session_token": "reader-web-perf",
        "first_seen_offset_days": 9,
        "last_seen_offset_days": 2,
        "interactions": [
            ("Why Fast Page Loads Improve Content Engagement", "view", 345, 9),
            ("Component Patterns for Faster Blog Page Builds", "view", 300, 8),
            ("Measuring Content Quality Beyond Pageviews", "view", 225, 6),
            ("Topic Clusters That Make Internal Linking Easier", "recommendation_click", 190, 4),
            ("Practical SEO Habits for Small Content Teams", "view", 200, 2),
        ],
    },
    {
        "session_token": "reader-mixed-demo",
        "first_seen_offset_days": 7,
        "last_seen_offset_days": 0,
        "interactions": [
            ("Building Trust With a Clear Author Voice", "view", 240, 7),
            ("Choosing AI Writing Tools Without Losing Editorial Control", "view", 260, 5),
            ("Writing Meta Descriptions That Earn the Click", "recommendation_click", 175, 4),
            ("Measuring Content Quality Beyond Pageviews", "view", 275, 3),
            ("Why Fast Page Loads Improve Content Engagement", "view", 235, 0),
        ],
    },
]


def _build_post(seed_post, index):
    created_at = utcnow() - timedelta(days=(len(SEED_POSTS) - index) * 4)
    return Post(
        title=seed_post["title"],
        content=seed_post["content"],
        category=seed_post["category"],
        tags=seed_post["tags"],
        meta_description=seed_post["meta_description"],
        created_at=created_at,
        updated_at=created_at + timedelta(days=1),
    )


def _estimate_readability(index):
    return round(57.0 + (index % 5) * 3.6, 1)


def _estimate_seo_score(index):
    return round(72.0 + (index % 4) * 4.5, 1)


def _build_seo_report(post, index):
    tag_keywords = [tag.strip() for tag in (post.tags or "").split(",") if tag.strip()]
    suggestions = [
        "Link this post to one adjacent article in the same topic cluster.",
        "Review the opening paragraph to keep the primary topic visible early.",
    ]
    if len(post.meta_description or "") < 120:
        suggestions.append("Expand the meta description slightly for a clearer search snippet.")

    return SEOReport(
        post_id=post.id,
        word_count=len(post.content.split()),
        readability_score=_estimate_readability(index),
        seo_score=_estimate_seo_score(index),
        suggestions_json=json.dumps(suggestions),
        keywords_json=json.dumps(tag_keywords[:4]),
        internal_links_json=json.dumps([]),
        created_at=post.updated_at + timedelta(hours=6),
    )


def _build_sessions_and_interactions(posts_by_title):
    sessions = []
    interactions = []
    base_now = utcnow()

    for session_seed in SEED_SESSIONS:
        session = VisitorSession(
            session_token=session_seed["session_token"],
            first_seen=base_now - timedelta(days=session_seed["first_seen_offset_days"]),
            last_seen=base_now - timedelta(days=session_seed["last_seen_offset_days"]),
        )
        sessions.append(session)

        for title, event_type, dwell_time, days_ago in session_seed["interactions"]:
            post = posts_by_title[title]
            interactions.append(
                Interaction(
                    session_token=session.session_token,
                    post_id=post.id,
                    event_type=event_type,
                    dwell_time=dwell_time,
                    timestamp=base_now - timedelta(days=days_ago),
                )
            )

    return sessions, interactions


def load_seed_data(reset=False):
    if reset:
        db.session.query(SEOReport).delete()
        db.session.query(Interaction).delete()
        db.session.query(VisitorSession).delete()
        db.session.query(Post).delete()
        db.session.commit()

    if Post.query.first():
        return False

    posts = [_build_post(seed_post, index) for index, seed_post in enumerate(SEED_POSTS)]
    db.session.add_all(posts)
    db.session.commit()

    posts_by_title = {post.title: post for post in Post.query.all()}
    seo_reports = [
        _build_seo_report(posts_by_title[seed_post["title"]], index)
        for index, seed_post in enumerate(SEED_POSTS)
    ]
    sessions, interactions = _build_sessions_and_interactions(posts_by_title)

    db.session.add_all(seo_reports)
    db.session.add_all(sessions)
    db.session.add_all(interactions)
    db.session.commit()
    return True


def register_seed_commands(app):
    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Clear existing seeded records before loading demo posts.")
    def seed_command(reset):
        """Populate the database with demo content."""
        inserted = load_seed_data(reset=reset)
        if inserted:
            click.echo(f"Loaded {len(SEED_POSTS)} demo posts across seeded categories.")
        else:
            click.echo("Seed skipped because posts already exist. Use --reset to reload the demo corpus.")
