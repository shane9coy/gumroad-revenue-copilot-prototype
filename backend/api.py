from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Union

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from gumroad_merchant.agent_actions import (
    apply_agent_action_tool,
    create_architecture_diagram_action_tool,
    create_roadmap_action_tool,
    create_tracked_campaign_action_tool,
    list_agent_actions_tool,
)
from gumroad_merchant.agent_harness import run_agent_chat
from gumroad_merchant.analytics_dataset import load_analytics_dashboard_payload
from gumroad_merchant.analytics_tools import get_dashboard_summary_tool
from gumroad_merchant.chat_history import (
    append_message,
    archive_session,
    auto_session_title,
    connect as connect_chat_history,
    ensure_schema as ensure_chat_schema,
    ensure_session,
    get_session as get_chat_session_record,
    history_for_agent,
    list_sessions as list_chat_sessions,
    load_messages as load_chat_messages,
    record_turn,
    update_message_status,
    update_session as update_chat_session,
)
from gumroad_merchant.admin_action_preview_tools import (
    build_cli_command_preview,
    get_admin_api_cli_recommendation,
    get_admin_action_preview_summary,
    list_admin_action_templates,
    preview_admin_action,
)
from gumroad_merchant.content_radar_tools import (
    build_marketing_plan_tool,
    draft_campaign_assets_tool,
    get_content_radar_summary_tool,
    list_content_trends_tool,
)
from gumroad_merchant.database import refresh_database, table_count
from gumroad_merchant.observability import clear_trace_context, set_trace_context, trace_event, trace_span
from gumroad_merchant.redis_state import RedisRuntime
from gumroad_merchant.refund_ops_tools import (
    build_dispute_evidence_pack_tool,
    draft_refund_reply_tool,
    get_refund_case_tool,
    get_refund_ops_summary_tool,
    get_refund_prevention_actions_tool,
    list_refund_cases_tool,
)
from gumroad_merchant.retention_saver_tools import (
    build_pause_offer_plan_tool,
    estimate_pause_revenue_saved_tool,
    get_retention_saver_summary_tool,
    list_cancellation_risks_tool,
)
from gumroad_merchant.settings import PROJECT_ROOT, get_settings, openai_key_present
from gumroad_merchant.shortest_qa_tools import (
    generate_shortest_qa_tests,
    get_shortest_qa_summary,
    get_shortest_qa_test,
    list_shortest_qa_suites,
)
from gumroad_merchant.tracked_campaigns import list_tracked_campaigns_tool
from gumroad_merchant.xai_voice import create_voice_client_secret, voice_status


settings = get_settings()
redis_runtime = RedisRuntime(settings.redis_url)
app = FastAPI(title="Gumroad Merchant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:8090",
        "http://127.0.0.1:8090",
        "http://localhost:8009",
        "http://127.0.0.1:8009",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: Optional[str] = Field(default=None, max_length=200)
    product_id: str = Field(default="all", max_length=80)
    date_range: str = Field(default="30", max_length=20)


class ChatCitation(BaseModel):
    type: Literal[
        "summary",
        "product",
        "source",
        "signal",
        "action",
        "help_doc",
        "refund_case",
        "content_trend",
        "retention",
        "admin_action",
        "qa_test",
        "tracked_campaign",
    ]
    id: Optional[Union[int, str]]
    label: str
    excerpt: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    citations: list[ChatCitation]
    model: str
    fallback: bool


class ChatMessageRecord(BaseModel):
    id: int
    session_id: str
    role: Literal["user", "assistant"]
    status: Literal["received", "processing", "completed", "failed"] = "completed"
    content: str
    citations: list[ChatCitation]
    metadata: dict[str, Any]
    created_at: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageRecord]


class ChatSessionResponse(BaseModel):
    session_id: str
    started_at: str


class ChatSessionRecord(BaseModel):
    id: str
    product_id: str
    date_range: str
    title: str
    created_at: str
    updated_at: str
    latest_message_at: Optional[str] = None
    message_count: int
    saved_at: Optional[str] = None
    archived_at: Optional[str] = None


class ChatSessionListResponse(BaseModel):
    recent: list[ChatSessionRecord]
    saved: list[ChatSessionRecord]


class ChatSessionUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=120)
    saved: Optional[bool] = None


class ChatSessionMutationResponse(BaseModel):
    session: ChatSessionRecord


class HealthResponse(BaseModel):
    ok: bool
    profile: str
    products: int
    openai_key_present: bool
    redis: dict[str, Any]
    voice: dict[str, Any]


class DataRefreshResponse(BaseModel):
    ok: bool
    refreshed: bool
    source: str
    source_hash: str
    product_count: int
    traffic_source_rows: int
    customer_sale_rows: int
    refreshed_at: str


class RefundOpsSummaryResponse(BaseModel):
    data: dict[str, Any]


class RefundCaseListResponse(BaseModel):
    cases: list[dict[str, Any]]


class RefundCaseResponse(BaseModel):
    data: dict[str, Any]


class DataEnvelopeResponse(BaseModel):
    data: dict[str, Any]


class ListEnvelopeResponse(BaseModel):
    items: list[dict[str, Any]]


class AnalyticsProductsResponse(BaseModel):
    products: list[dict[str, Any]]
    dashboardData: dict[str, Any]
    source: str
    sourceHash: str
    refreshedAt: str
    trackedCampaignCount: int


class TrackedCampaignRequest(BaseModel):
    product_id: str = Field(default="all", max_length=80)
    date_range: str = Field(default="30", max_length=20)
    title: Optional[str] = Field(default=None, max_length=160)
    source: Optional[str] = Field(default=None, max_length=80)
    medium: Optional[str] = Field(default=None, max_length=80)
    campaign: Optional[str] = Field(default=None, max_length=120)
    destination_url: Optional[str] = Field(default=None, max_length=500)
    reason: Optional[str] = Field(default=None, max_length=800)


class RoadmapRequest(BaseModel):
    product_id: str = Field(default="all", max_length=80)
    date_range: str = Field(default="30", max_length=20)
    horizon_days: int = Field(default=30, ge=30, le=60)


class ArchitectureDiagramRequest(BaseModel):
    diagram_type: str = Field(default="agent-action-system", max_length=80)
    title: Optional[str] = Field(default=None, max_length=160)


def new_session_id() -> str:
    return f"gm-{uuid.uuid4().hex}"


def normalized_session_id(session_id: Optional[str]) -> str:
    cleaned = (session_id or "").strip()
    return cleaned if cleaned else new_session_id()


def normalized_product_id(product_id: Optional[str]) -> str:
    cleaned = (product_id or "all").strip()
    return cleaned or "all"


def normalized_date_range(date_range: Optional[str]) -> str:
    cleaned = (date_range or "30").strip()
    if cleaned in {"30", "90", "180", "all"}:
        return cleaned
    if cleaned.isdigit():
        days = max(1, min(365, int(cleaned)))
        return str(days)
    return "30"


def ensure_runtime_state(force_analytics: bool = False):
    snapshot = refresh_database(settings.db_path, force=force_analytics)
    conn = connect_chat_history(settings.chat_db_path)
    try:
        ensure_chat_schema(conn)
    finally:
        conn.close()
    return snapshot


@app.on_event("startup")
def startup() -> None:
    ensure_runtime_state()


def load_chat_history(session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    conn = connect_chat_history(settings.chat_db_path)
    try:
        return load_chat_messages(conn, session_id, limit=limit)
    finally:
        conn.close()


def persist_chat_turn(
    session_id: str,
    product_id: str,
    date_range: str,
    user_message: str,
    answer: str,
    citations: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    conn = connect_chat_history(settings.chat_db_path)
    try:
        ensure_session(conn, session_id, product_id=product_id, date_range=date_range, title=auto_session_title(user_message))
        record_turn(
            conn,
            session_id=session_id,
            user_message=user_message,
            assistant_answer=answer,
            citations=citations,
            metadata=metadata,
        )
    finally:
        conn.close()


def persist_user_chat_message(
    session_id: str,
    product_id: str,
    date_range: str,
    user_message: str,
    metadata: dict[str, Any],
) -> int:
    conn = connect_chat_history(settings.chat_db_path)
    try:
        ensure_session(conn, session_id, product_id=product_id, date_range=date_range, title=auto_session_title(user_message))
        return append_message(
            conn,
            session_id=session_id,
            role="user",
            content=user_message,
            status="received",
            metadata=metadata,
        )
    finally:
        conn.close()


def persist_assistant_chat_message(
    session_id: str,
    answer: str,
    citations: list[dict[str, Any]],
    metadata: dict[str, Any],
    status: Literal["completed", "failed"] = "completed",
) -> int:
    conn = connect_chat_history(settings.chat_db_path)
    try:
        return append_message(
            conn,
            session_id=session_id,
            role="assistant",
            content=answer,
            status=status,
            citations=citations,
            metadata=metadata,
        )
    finally:
        conn.close()


def mark_chat_message_status(
    message_id: int,
    status: Literal["processing", "completed", "failed"],
    metadata: dict[str, Any],
) -> None:
    conn = connect_chat_history(settings.chat_db_path)
    try:
        update_message_status(conn, message_id=message_id, status=status, metadata=metadata)
    finally:
        conn.close()


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ensure_runtime_state()
    redis_status = redis_runtime.status()
    voice = voice_status(settings)
    return HealthResponse(
        ok=True,
        profile=settings.profile,
        products=table_count(settings.db_path, "products"),
        openai_key_present=openai_key_present(),
        redis={
            "enabled": redis_status.enabled,
            "available": redis_status.available,
            "error": redis_status.error,
        },
        voice={
            "enabled": voice.enabled,
            "configured": voice.configured,
            "reason": voice.reason,
        },
    )


@app.post("/api/agent/data/refresh", response_model=DataRefreshResponse)
def refresh_agent_data(force: bool = Query(default=False)) -> DataRefreshResponse:
    status = ensure_runtime_state(force_analytics=force)
    return DataRefreshResponse(ok=True, **status.as_dict())


@app.get("/api/analytics/products", response_model=AnalyticsProductsResponse)
def analytics_products() -> AnalyticsProductsResponse:
    status = ensure_runtime_state()
    payload = load_analytics_dashboard_payload(settings.db_path)
    return AnalyticsProductsResponse(
        products=payload["products"],
        dashboardData=payload["dashboardData"],
        source=status.source,
        sourceHash=status.source_hash,
        refreshedAt=status.refreshed_at,
        trackedCampaignCount=payload["trackedCampaignCount"],
    )


@app.get("/api/analytics/summary", response_model=DataEnvelopeResponse)
def analytics_summary(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=get_dashboard_summary_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
        )
    )


@app.get("/api/tracked-campaigns", response_model=ListEnvelopeResponse)
def tracked_campaigns(
    product_id: Optional[str] = Query(default="all", max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
) -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(
        items=list_tracked_campaigns_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            limit=limit,
        )
    )


@app.post("/api/tracked-campaigns", response_model=DataEnvelopeResponse)
def create_tracked_campaign(request: TrackedCampaignRequest) -> DataEnvelopeResponse:
    ensure_runtime_state()
    created = create_tracked_campaign_action_tool(
        settings.db_path,
        product_id=normalized_product_id(request.product_id),
        date_range=normalized_date_range(request.date_range),
        title=request.title,
        source=request.source,
        medium=request.medium,
        campaign=request.campaign,
        destination_url=request.destination_url,
        reason=request.reason,
    )
    return DataEnvelopeResponse(data={**created["campaign"], "agent_action": created["action"], "already_applied": created["already_applied"]})


@app.get("/api/agent/actions", response_model=ListEnvelopeResponse)
def agent_actions(
    action_type: str = Query(default="all", max_length=80),
    status: str = Query(default="all", max_length=20),
    product_id: str = Query(default="all", max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
) -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(
        items=list_agent_actions_tool(
            settings.db_path,
            action_type=action_type,
            status=status,
            product_id=normalized_product_id(product_id),
            limit=limit,
        )
    )


@app.post("/api/agent/actions/{action_id}/apply", response_model=DataEnvelopeResponse)
def apply_agent_action(action_id: str) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(data=apply_agent_action_tool(settings.db_path, action_id))


@app.post("/api/roadmaps", response_model=DataEnvelopeResponse)
def create_roadmap(request: RoadmapRequest) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=create_roadmap_action_tool(
            settings.db_path,
            product_id=normalized_product_id(request.product_id),
            date_range=normalized_date_range(request.date_range),
            horizon_days=request.horizon_days,
        )
    )


@app.post("/api/architecture-diagrams", response_model=DataEnvelopeResponse)
def create_architecture_diagram(request: ArchitectureDiagramRequest) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=create_architecture_diagram_action_tool(
            settings.db_path,
            diagram_type=request.diagram_type,
            title=request.title,
        )
    )


@app.get("/api/agent/chat/session", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: Optional[str] = Query(default=None, max_length=200),
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> ChatSessionResponse:
    ensure_runtime_state()
    normalized = normalized_session_id(session_id)
    product = normalized_product_id(product_id)
    date = normalized_date_range(date_range)
    conn = connect_chat_history(settings.chat_db_path)
    try:
        if (session_id or "").strip():
            archived_row = conn.execute(
                "SELECT archived_at FROM chat_sessions WHERE id = ?",
                (normalized,),
            ).fetchone()
            if archived_row and archived_row["archived_at"]:
                normalized = new_session_id()
        ensure_session(conn, normalized, product_id=product, date_range=date, title="Gumroad Merchant")
    finally:
        conn.close()
    redis_runtime.touch_session(normalized, product, date)
    return ChatSessionResponse(session_id=normalized, started_at=datetime.now(timezone.utc).isoformat())


@app.get("/api/agent/chat/sessions", response_model=ChatSessionListResponse)
def get_chat_sessions(
    recent_limit: int = Query(default=10, ge=1, le=25),
    saved_limit: int = Query(default=50, ge=1, le=100),
) -> ChatSessionListResponse:
    ensure_runtime_state()
    conn = connect_chat_history(settings.chat_db_path)
    try:
        sessions = list_chat_sessions(
            conn,
            recent_limit=recent_limit,
            saved_limit=saved_limit,
        )
    finally:
        conn.close()
    return ChatSessionListResponse(
        recent=[ChatSessionRecord(**session) for session in sessions["recent"]],
        saved=[ChatSessionRecord(**session) for session in sessions["saved"]],
    )


@app.patch("/api/agent/chat/sessions/{session_id}", response_model=ChatSessionMutationResponse)
def patch_chat_session(
    session_id: str,
    request: ChatSessionUpdateRequest,
) -> ChatSessionMutationResponse:
    ensure_runtime_state()
    conn = connect_chat_history(settings.chat_db_path)
    try:
        current = get_chat_session_record(conn, session_id)
        if not current:
            raise HTTPException(status_code=404, detail="Chat session was not found.")
        if request.saved is True and int(current.get("message_count") or 0) <= 0:
            raise HTTPException(status_code=409, detail="Send a message before saving this chat session.")
        session = update_chat_session(
            conn,
            session_id=session_id,
            title=request.title,
            saved=request.saved,
        )
    finally:
        conn.close()
    return ChatSessionMutationResponse(session=ChatSessionRecord(**session))


@app.delete("/api/agent/chat/sessions/{session_id}", response_model=ChatSessionMutationResponse)
def delete_chat_session(session_id: str) -> ChatSessionMutationResponse:
    ensure_runtime_state()
    conn = connect_chat_history(settings.chat_db_path)
    try:
        session = archive_session(conn, session_id=session_id)
    finally:
        conn.close()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session was not found.")
    return ChatSessionMutationResponse(session=ChatSessionRecord(**session))


@app.get("/api/agent/chat/history", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
) -> ChatHistoryResponse:
    ensure_runtime_state()
    messages = load_chat_history(session_id, limit=limit)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessageRecord(**message) for message in messages],
    )


@app.post("/api/agent/chat", response_model=ChatResponse)
def agent_chat(request: ChatRequest) -> ChatResponse:
    ensure_runtime_state()
    session_id = normalized_session_id(request.session_id)
    product_id = normalized_product_id(request.product_id)
    date_range = normalized_date_range(request.date_range)
    request_id = f"chat-{uuid.uuid4().hex}"
    trace_token = set_trace_context(
        trace_id=request_id,
        request_id=request_id,
        session_id=session_id,
        product_id=product_id,
        date_range=date_range,
    )
    trace_event("chat.received", message_chars=len(request.message), openai_key_present=openai_key_present())
    redis_runtime.touch_session(session_id, product_id, date_range)
    if redis_runtime.rate_limit_hit(session_id):
        trace_event("chat.rate_limited")
        clear_trace_context(trace_token)
        raise HTTPException(status_code=429, detail="Too many chat requests for this demo session.")
    try:
        with trace_span("chat.load_history"):
            prior_messages = load_chat_history(session_id, limit=20)
        with trace_span("chat.persist_user_message"):
            user_message_id = persist_user_chat_message(
                session_id=session_id,
                product_id=product_id,
                date_range=date_range,
                user_message=request.message,
                metadata={
                    "request_id": request_id,
                    "product_id": product_id,
                    "date_range": date_range,
                    "status_reason": "accepted_before_agent_run",
                },
            )
        trace_event("chat.user_message_persisted", user_message_id=user_message_id)
        if not redis_runtime.set_in_flight(
            session_id,
            request.message,
            metadata={
                "request_id": request_id,
                "user_message_id": user_message_id,
                "product_id": product_id,
                "date_range": date_range,
            },
        ):
            trace_event("chat.duplicate_inflight", user_message_id=user_message_id)
            mark_chat_message_status(
                user_message_id,
                status="failed",
                metadata={
                    "request_id": request_id,
                    "product_id": product_id,
                    "date_range": date_range,
                    "error": "duplicate_message_in_flight",
                },
            )
            raise HTTPException(status_code=409, detail="The same message is already being processed.")
        trace_event("chat.redis_inflight_set", user_message_id=user_message_id)
        try:
            with trace_span("agent.run", user_message_id=user_message_id):
                result = run_agent_chat(
                    db_path=settings.db_path,
                    message=request.message,
                    product_id=product_id,
                    date_range=date_range,
                    conversation_history=history_for_agent(prior_messages, limit=8),
                )
            citation_payloads = [item for item in result.citations]
            trace_event(
                "agent.result",
                user_message_id=user_message_id,
                fallback=result.fallback,
                model=result.model,
                answer_words=len(result.answer.split()),
                citation_count=len(citation_payloads),
                error=result.error,
            )
            with trace_span("chat.persist_assistant_message", user_message_id=user_message_id):
                persist_assistant_chat_message(
                    session_id=session_id,
                    answer=result.answer,
                    citations=citation_payloads,
                    metadata={
                        "request_id": request_id,
                        "user_message_id": user_message_id,
                        "model": result.model,
                        "fallback": result.fallback,
                        "error": result.error,
                        "product_id": product_id,
                        "date_range": date_range,
                    },
                )
            return ChatResponse(
                session_id=session_id,
                answer=result.answer,
                citations=[ChatCitation(**item) for item in citation_payloads],
                model=result.model,
                fallback=result.fallback,
            )
        except Exception as exc:
            error_message = f"{type(exc).__name__}: {exc}"
            trace_event("chat.error", user_message_id=user_message_id, error=error_message)
            mark_chat_message_status(
                user_message_id,
                status="failed",
                metadata={
                    "request_id": request_id,
                    "product_id": product_id,
                    "date_range": date_range,
                    "error": error_message,
                },
            )
            persist_assistant_chat_message(
                session_id=session_id,
                answer="I hit an unexpected backend error before I could finish this response.",
                citations=[],
                status="failed",
                metadata={
                    "request_id": request_id,
                    "user_message_id": user_message_id,
                    "product_id": product_id,
                    "date_range": date_range,
                    "error": error_message,
                },
            )
            raise
        finally:
            redis_runtime.clear_in_flight(session_id, request.message)
            trace_event("chat.redis_inflight_cleared", user_message_id=user_message_id)
    finally:
        trace_event("chat.finished")
        clear_trace_context(trace_token)


@app.get("/api/refund-ops/summary", response_model=RefundOpsSummaryResponse)
def refund_ops_summary(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> RefundOpsSummaryResponse:
    ensure_runtime_state()
    return RefundOpsSummaryResponse(
        data=get_refund_ops_summary_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
        )
    )


@app.get("/api/refund-ops/cases", response_model=RefundCaseListResponse)
def refund_ops_cases(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    mode: str = Query(default="all", max_length=20),
    limit: int = Query(default=10, ge=1, le=25),
) -> RefundCaseListResponse:
    ensure_runtime_state()
    return RefundCaseListResponse(
        cases=list_refund_cases_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            mode=mode,
            limit=limit,
        )
    )


@app.get("/api/refund-ops/cases/{case_id}", response_model=RefundCaseResponse)
def refund_ops_case(case_id: str) -> RefundCaseResponse:
    ensure_runtime_state()
    return RefundCaseResponse(data=get_refund_case_tool(settings.db_path, case_id=case_id))


@app.get("/api/refund-ops/cases/{case_id}/dispute-evidence", response_model=RefundCaseResponse)
def refund_ops_dispute_evidence(case_id: str) -> RefundCaseResponse:
    ensure_runtime_state()
    return RefundCaseResponse(data=build_dispute_evidence_pack_tool(settings.db_path, case_id=case_id))


@app.get("/api/refund-ops/cases/{case_id}/buyer-reply", response_model=RefundCaseResponse)
def refund_ops_buyer_reply(case_id: str) -> RefundCaseResponse:
    ensure_runtime_state()
    return RefundCaseResponse(data=draft_refund_reply_tool(settings.db_path, case_id=case_id))


@app.get("/api/refund-ops/prevention-actions", response_model=RefundCaseResponse)
def refund_ops_prevention_actions(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> RefundCaseResponse:
    ensure_runtime_state()
    return RefundCaseResponse(
        data={
            "actions": get_refund_prevention_actions_tool(
                settings.db_path,
                product_id=normalized_product_id(product_id),
                date_range=normalized_date_range(date_range),
            )
        }
    )


@app.get("/api/content-radar/summary", response_model=DataEnvelopeResponse)
def content_radar_summary(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=get_content_radar_summary_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
        )
    )


@app.get("/api/content-radar/trends", response_model=ListEnvelopeResponse)
def content_radar_trends(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    limit: int = Query(default=6, ge=1, le=12),
) -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(
        items=list_content_trends_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            limit=limit,
        )
    )


@app.get("/api/content-radar/plan", response_model=DataEnvelopeResponse)
def content_radar_plan(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    horizon_weeks: int = Query(default=4, ge=2, le=8),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=build_marketing_plan_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            horizon_weeks=horizon_weeks,
        )
    )


@app.get("/api/content-radar/drafts", response_model=DataEnvelopeResponse)
def content_radar_drafts(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    trend_id: Optional[str] = Query(default=None, max_length=120),
    channel: Optional[str] = Query(default=None, max_length=80),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=draft_campaign_assets_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            trend_id=trend_id,
            channel=channel,
        )
    )


@app.get("/api/retention-saver/summary", response_model=DataEnvelopeResponse)
def retention_saver_summary(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=get_retention_saver_summary_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
        )
    )


@app.get("/api/retention-saver/risks", response_model=ListEnvelopeResponse)
def retention_saver_risks(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    limit: int = Query(default=10, ge=1, le=25),
) -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(
        items=list_cancellation_risks_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            limit=limit,
        )
    )


@app.get("/api/retention-saver/pause-plan", response_model=DataEnvelopeResponse)
def retention_saver_pause_plan(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=build_pause_offer_plan_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
        )
    )


@app.get("/api/retention-saver/estimate", response_model=DataEnvelopeResponse)
def retention_saver_estimate(
    product_id: Optional[str] = Query(default="all", max_length=80),
    date_range: Optional[str] = Query(default="30", max_length=20),
    save_rate: Optional[str] = Query(default=None, max_length=20),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=estimate_pause_revenue_saved_tool(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            date_range=normalized_date_range(date_range),
            save_rate=save_rate,
        )
    )


@app.get("/api/admin-preview/summary", response_model=DataEnvelopeResponse)
def admin_preview_summary(
    product_id: Optional[str] = Query(default="all", max_length=80),
    limit: int = Query(default=6, ge=1, le=25),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=get_admin_action_preview_summary(
            settings.db_path,
            product_id=normalized_product_id(product_id),
            limit=limit,
        )
    )


@app.get("/api/admin-preview/api-cli-recommendation", response_model=DataEnvelopeResponse)
def admin_preview_api_cli_recommendation() -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(data=get_admin_api_cli_recommendation())


@app.get("/api/admin-preview/templates", response_model=ListEnvelopeResponse)
def admin_preview_templates() -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(items=list_admin_action_templates())


@app.get("/api/admin-preview/command", response_model=DataEnvelopeResponse)
def admin_preview_command(
    action_id: str = Query(default="purchase_lookup", max_length=80),
    purchase_id: Optional[str] = Query(default=None, max_length=120),
    case_id: Optional[str] = Query(default=None, max_length=120),
    product_id: Optional[str] = Query(default=None, max_length=80),
    reason: Optional[str] = Query(default=None, max_length=300),
    note: Optional[str] = Query(default=None, max_length=500),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=build_cli_command_preview(
            action_id,
            inputs={
                "purchase_id": purchase_id,
                "case_id": case_id,
                "product_id": normalized_product_id(product_id) if product_id else None,
                "reason": reason,
                "note": note,
            },
        )
    )


@app.get("/api/admin-preview/preview", response_model=DataEnvelopeResponse)
def admin_preview_action(
    action_id: str = Query(default="purchase_lookup", max_length=80),
    purchase_id: Optional[str] = Query(default=None, max_length=120),
    case_id: Optional[str] = Query(default=None, max_length=120),
    product_id: Optional[str] = Query(default=None, max_length=80),
    reason: Optional[str] = Query(default=None, max_length=300),
    note: Optional[str] = Query(default=None, max_length=500),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=preview_admin_action(
            settings.db_path,
            action_id=action_id,
            purchase_id=purchase_id,
            case_id=case_id,
            product_id=normalized_product_id(product_id) if product_id else None,
            reason=reason,
            note=note,
        )
    )


@app.get("/api/shortest-qa/summary", response_model=DataEnvelopeResponse)
def shortest_qa_summary() -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(data=get_shortest_qa_summary())


@app.get("/api/shortest-qa/suites", response_model=ListEnvelopeResponse)
def shortest_qa_suites() -> ListEnvelopeResponse:
    ensure_runtime_state()
    return ListEnvelopeResponse(items=list_shortest_qa_suites())


@app.get("/api/shortest-qa/tests", response_model=DataEnvelopeResponse)
def shortest_qa_tests(
    suite_id: str = Query(default="all", max_length=80),
    target_surface: str = Query(default="all", max_length=120),
    priority: str = Query(default="all", max_length=40),
    limit: Optional[int] = Query(default=None, ge=1, le=50),
) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(
        data=generate_shortest_qa_tests(
            suite_id=suite_id,
            target_surface=target_surface,
            priority=priority,
            limit=limit,
        )
    )


@app.get("/api/shortest-qa/tests/{test_id}", response_model=DataEnvelopeResponse)
def shortest_qa_test(test_id: str) -> DataEnvelopeResponse:
    ensure_runtime_state()
    return DataEnvelopeResponse(data=get_shortest_qa_test(test_id))


@app.post("/api/voice/client-secret")
def voice_client_secret() -> dict[str, Any]:
    return create_voice_client_secret(settings)


@app.get("/api/artifacts/{artifact_type}/{filename}")
def download_artifact(artifact_type: str, filename: str) -> FileResponse:
    roots = {
        "roadmaps": PROJECT_ROOT / "artifacts" / "roadmaps",
        "architecture": PROJECT_ROOT / "artifacts" / "architecture",
    }
    root = roots.get(artifact_type)
    if root is None or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="Artifact was not found.")
    path = (root / filename).resolve()
    root_resolved = root.resolve()
    if root_resolved not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact was not found.")
    return FileResponse(path, filename=filename)


demo_dir = PROJECT_ROOT / "demo"
if demo_dir.exists():
    app.mount("/", StaticFiles(directory=Path(demo_dir), html=True), name="demo")
