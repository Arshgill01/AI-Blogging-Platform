from sqlalchemy import case, func

from app import db
from app.models import Reaction, VisitorSession, utcnow

LIKE_VALUE = 1
DISLIKE_VALUE = -1


def get_reaction_counts(post_id):
    counts = db.session.query(
        func.sum(
            case(
                (Reaction.value == LIKE_VALUE, 1),
                else_=0
            )
        ).label('likes'),
        func.sum(
            case(
                (Reaction.value == DISLIKE_VALUE, 1),
                else_=0
            )
        ).label('dislikes'),
    ).filter(Reaction.post_id == post_id).first()

    return {
        "likes": counts.likes or 0,
        "dislikes": counts.dislikes or 0,
    }


def get_user_reaction(session_token, post_id):
    reaction = Reaction.query.filter_by(
        session_token=session_token,
        post_id=post_id,
    ).first()

    if reaction is None:
        return 0

    return reaction.value


def set_reaction(session_token, post_id, value):
    if value not in (LIKE_VALUE, DISLIKE_VALUE):
        return None

    ensure_session_exists(session_token)

    existing = Reaction.query.filter_by(
        session_token=session_token,
        post_id=post_id,
    ).first()

    if existing:
        if existing.value == value:
            db.session.delete(existing)
            db.session.commit()
            return 0

        existing.value = value
        db.session.commit()
        return value

    reaction = Reaction(
        session_token=session_token,
        post_id=post_id,
        value=value,
        created_at=utcnow(),
    )
    db.session.add(reaction)
    db.session.commit()
    return value


def toggle_reaction(session_token, post_id):
    current = get_user_reaction(session_token, post_id)
    if current == LIKE_VALUE:
        return set_reaction(session_token, post_id, DISLIKE_VALUE)
    elif current == DISLIKE_VALUE:
        return set_reaction(session_token, post_id, LIKE_VALUE)
    else:
        return set_reaction(session_token, post_id, LIKE_VALUE)


def ensure_session_exists(session_token):
    visitor_session = VisitorSession.query.filter_by(session_token=session_token).first()
    if visitor_session is None:
        visitor_session = VisitorSession(
            session_token=session_token,
            first_seen=utcnow(),
            last_seen=utcnow(),
        )
        db.session.add(visitor_session)
        db.session.commit()