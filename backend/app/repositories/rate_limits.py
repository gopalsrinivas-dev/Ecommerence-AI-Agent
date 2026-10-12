from sqlalchemy.dialects.postgresql import insert

from app.models.rate_bucket import RateBucket


def increment_rate(db, key, window):
    statement = insert(RateBucket).values(key=key, window=window, count=1)
    returning = statement.on_conflict_do_update(
        index_elements=[RateBucket.key, RateBucket.window], set_={"count": RateBucket.count + 1}
    ).returning(RateBucket.count)
    return db.scalar(returning)
