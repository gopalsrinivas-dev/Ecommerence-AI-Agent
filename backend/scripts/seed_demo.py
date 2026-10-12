from sqlalchemy import select

from app.core.config import settings
from app.core.security import hasher
from app.db.session import SessionLocal
from app.models.base import now
from app.models.order import Order
from app.models.user import User


def seed():
    if settings().app_env == "production":
        raise RuntimeError("Demo seeding is forbidden in production")
    with SessionLocal() as db:
        for email, fixtures in [
            (
                "alex@example.test",
                [
                    ("ORD1001", "Studio headphones", "SHIPPED"),
                    ("ORD1003", "Canvas weekend bag", "CANCELLED"),
                    ("ORD1004", "Everyday mechanical keyboard", "PROCESSING"),
                ],
            ),
            ("sam@example.test", [("ORD1002", "Desk lamp", "DELIVERED")]),
        ]:
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                user = User(email=email, password_hash=hasher.hash("DemoShop!2026"))
                db.add(user)
                db.flush()
            for identity, product, state in fixtures:
                if not db.scalar(select(Order).where(Order.order_id == identity)):
                    db.add(
                        Order(
                            order_id=identity,
                            customer_id=user.id,
                            product_name=product,
                            status=state,
                            cancelled_at=now() if state == "CANCELLED" else None,
                        )
                    )
        db.commit()
    print("Demo customers seeded (existing orders preserved).")


if __name__ == "__main__":
    seed()
