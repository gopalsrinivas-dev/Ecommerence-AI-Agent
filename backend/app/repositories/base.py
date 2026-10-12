from sqlalchemy import select

from app.core.exceptions import missing


def owned(db, model, identity, actor, lock=False):
    query = select(model).where(model.id == identity, model.customer_id == actor)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise missing()
    return row
