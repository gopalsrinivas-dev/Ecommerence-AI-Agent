from sqlalchemy import select

from app.models.user import User


def user_by_email(db, email):
    return db.scalar(select(User).where(User.email == email))


def user_by_id(db, identity):
    return db.get(User, identity)
