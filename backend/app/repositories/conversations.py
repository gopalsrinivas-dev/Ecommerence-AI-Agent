from sqlalchemy import select

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.turn import Turn
from app.repositories.base import owned


def conversation(db, identity, actor, lock=False):
    return owned(db, Conversation, identity, actor, lock)


def messages_page(db, identity, limit, cursor):
    query = select(Message).where(Message.conversation_id == identity)
    if cursor:
        query = query.where(Message.id > cursor)
    return list(db.scalars(query.order_by(Message.id).limit(limit + 1)))


def recent_messages(db, identity):
    return list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == identity)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(20)
        )
    )


def turn_for_message(db, identity, client_message_id):
    return db.scalar(
        select(Turn).where(Turn.conversation_id == identity, Turn.client_message_id == client_message_id)
    )
