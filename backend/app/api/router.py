import uuid

from fastapi import APIRouter, Depends, Query, Request, Response

from app.api.dependencies import database, origin, session
from app.core.config import settings
from app.core.logging import request_id
from app.schemas.action import ActionResponse, ConfirmationResponse
from app.schemas.auth import IdentityResponse, Login
from app.schemas.chat import ChatInput, ChatResponse, ConversationResponse, MessagePage
from app.schemas.order import OrderPage, OrderResponse
from app.services import auth_service, chat_service, order_service, query_service

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=IdentityResponse)
def login(payload: Login, request: Request, response: Response, db=Depends(database)):
    origin(request)
    auth_service.rate_limit(
        db, "login:" + (request.client.host if request.client else "unknown"), settings().auth_rate_limit
    )
    user, raw, csrf = auth_service.login(db, payload.email, payload.password)
    secure = settings().app_env == "production"
    options = dict(secure=secure, samesite="lax", max_age=settings().session_ttl_seconds, path="/")
    response.set_cookie(settings().session_cookie_name, raw, httponly=True, **options)
    response.set_cookie("csrf_token", csrf, httponly=False, **options)
    return {"user": {"id": str(user.id), "email": user.email}, "provider_mode": settings().provider_mode}


@router.get("/auth/me", response_model=IdentityResponse)
def me(auth=Depends(session), db=Depends(database)):
    return auth_service.profile(db, auth)


@router.post("/auth/logout", status_code=204)
def logout(response: Response, auth=Depends(session), db=Depends(database)):
    auth_service.logout(db, auth)
    response.delete_cookie(settings().session_cookie_name, path="/")
    response.delete_cookie("csrf_token", path="/")


@router.get("/orders", response_model=OrderPage)
def orders(
    limit: int = Query(20, ge=1, le=100),
    cursor: uuid.UUID | None = None,
    auth=Depends(session),
    db=Depends(database),
):
    return query_service.orders(db, auth.user_id, limit, str(cursor) if cursor else None)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def order(order_id: str, auth=Depends(session), db=Depends(database)):
    return order_service.status(db, auth.user_id, order_id)


@router.post("/conversations", status_code=201, response_model=ConversationResponse)
def create_conversation(auth=Depends(session), db=Depends(database)):
    return chat_service.create(db, auth.user_id)


@router.get("/conversations/{identity}/messages", response_model=MessagePage)
def messages(
    identity: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    cursor: uuid.UUID | None = None,
    auth=Depends(session),
    db=Depends(database),
):
    return chat_service.history(db, auth.user_id, identity, limit, cursor)


@router.post("/chat/messages", response_model=ChatResponse)
def chat(payload: ChatInput, auth=Depends(session), db=Depends(database)):
    auth_service.rate_limit(db, "chat:" + str(auth.user_id), settings().chat_rate_limit)
    return {**chat_service.send(auth.user_id, payload), "request_id": request_id.get()}


@router.post("/actions/{identity}/confirm", response_model=ConfirmationResponse)
def confirm(identity: uuid.UUID, auth=Depends(session), db=Depends(database)):
    return {**order_service.confirm(db, auth.user_id, identity), "request_id": request_id.get()}


@router.post("/actions/{identity}/dismiss", response_model=ActionResponse)
def dismiss(identity: uuid.UUID, auth=Depends(session), db=Depends(database)):
    return order_service.dismiss(db, auth.user_id, identity)


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db=Depends(database)):
    return query_service.readiness(db)
