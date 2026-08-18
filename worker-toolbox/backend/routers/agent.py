"""AI Agent API — 对话式 Agent 的入口与记忆管理。"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.memory_service import memory_service
from backend.services import intent_router
from backend.services.agent_loop import agent_loop as agent_loop_service, get_turn

router = APIRouter(prefix="/api/agent", tags=["agent"])


# ── 对话 ──

class ChatRequest(BaseModel):
    text: str
    session_id: int | None = None
    session_key: str | None = None


@router.post("/chat")
def agent_chat(req: ChatRequest):
    """Agent 对话入口。快路径同步返回 fast；复杂任务返回 turn_id 轮询。"""
    text = (req.text or "").strip()
    if not text:
        return {"code": 400, "msg": "Missing text", "data": None}

    # 会话（按 session_key 复用，否则新建）
    sess = memory_service.create_session(req.session_key)
    session_id = sess.id
    memory_service.add_message(session_id, "user", text)

    # ── 快路径（0 LLM）：关键词 → 问候语 → 技能精确命中 → multi-tool把关 → 单意图本地模型+正则 ──
    fast = intent_router.keyword_route(text)
    if fast is None and not intent_router.is_chat_like(text):
        skill_hit = None
        try:
            from backend.services.skill_registry import skill_registry
            skill_hit = skill_registry.search(text)
        except Exception:
            pass
        if skill_hit is not None:
            fast = None  # 命中技能 → 走 agent 路径执行技能（0 LLM 精确匹配）
        elif not intent_router.is_multi_step(text):
            fast = intent_router.route_single(text)
    if fast:
        memory_service.add_message(
            session_id, "assistant", fast.get("reply", "")[:500],
            msg_type="fast_action", payload=fast,
        )
        return {"code": 0, "msg": "ok",
                "data": {"fast": fast, "session_id": session_id, "session_key": sess.session_key}}

    # ── Agent 路径：后台循环，前端轮询 status ──
    turn_id = agent_loop_service.start_turn(session_id, text)
    return {"code": 0, "msg": "ok",
            "data": {"turn_id": turn_id, "session_id": session_id, "session_key": sess.session_key}}


@router.get("/status/{turn_id}")
def agent_status(turn_id: str):
    """查询 Agent turn 进度（steps 时间线 + final 结果）。"""
    turn = get_turn(turn_id)
    if not turn:
        return {"code": 404, "msg": "turn 不存在", "data": None}
    return {"code": 0, "msg": "ok", "data": turn}


# ── 会话 ──

@router.get("/sessions")
def list_sessions():
    """会话列表。"""
    return {"code": 0, "msg": "ok", "data": memory_service.list_sessions()}


@router.get("/sessions/{session_id}/messages")
def session_messages(session_id: int):
    """单会话全部消息（含 payload 时间线）。"""
    return {"code": 0, "msg": "ok", "data": memory_service.session_messages(session_id)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int):
    memory_service.delete_session(session_id)
    return {"code": 0, "msg": "ok"}


# ── 实体记忆 ──

class EntityCreate(BaseModel):
    entity_type: str
    entity_key: str
    entity_value: str


@router.get("/memory")
def list_memory():
    """实体记忆列表。"""
    return {"code": 0, "msg": "ok", "data": memory_service.get_entities()}


@router.post("/memory")
def upsert_memory(req: EntityCreate):
    ent = memory_service.upsert_entity(req.entity_type, req.entity_key, req.entity_value, source="api")
    return {"code": 0, "msg": "ok", "data": {"id": ent.id}}


@router.delete("/memory/{entity_id}")
def delete_memory(entity_id: int):
    memory_service.delete_entity(entity_id)
    return {"code": 0, "msg": "ok"}


@router.post("/memory/clear")
def clear_memory():
    n = memory_service.clear_entities()
    return {"code": 0, "msg": "ok", "data": {"cleared": n}}


# ── 计划缓存管理 ──

@router.get("/plan-cache")
def list_plan_cache():
    from backend.services.plan_cache import plan_cache
    return {"code": 0, "msg": "ok", "data": plan_cache.list()}


@router.delete("/plan-cache/{cache_id}")
def delete_plan_cache_item(cache_id: int):
    from backend.services.plan_cache import plan_cache
    n = plan_cache.delete(cache_id)
    return {"code": 0, "msg": "ok", "data": {"deleted": n}}


@router.delete("/plan-cache")
def clear_plan_cache():
    from backend.services.plan_cache import plan_cache
    n = plan_cache.delete(None)
    return {"code": 0, "msg": "ok", "data": {"deleted": n}}


# ── 外部 API 设置 ──

@router.get("/settings")
def get_settings():
    """外部数据工具 API key 状态（脱敏）。"""
    from backend.services.toolkit.external_api import get_key_status
    return {"code": 0, "msg": "ok", "data": get_key_status()}


@router.put("/settings")
def put_settings(req: dict):
    """设置外部数据工具 API key。"""
    from backend.services.toolkit.external_api import set_keys
    return {"code": 0, "msg": "ok", "data": set_keys(req or {})}
