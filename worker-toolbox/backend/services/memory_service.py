"""
Agent 记忆服务 — 三层记忆的 SQLite 侧：
① 会话记忆（agent_sessions + agent_messages）
② 实体记忆（agent_entities，用户偏好）
③ 计划缓存 SQLite 侧（agent_plan_cache；向量侧在 plan_cache.py 的独立 FAISS）

纯存储 + 检索逻辑，无 LLM。
"""

import json
from typing import Optional

from backend.database import SessionLocal
from backend.models import AgentSession, AgentMessage, AgentEntity, AgentPlanCache


class MemoryService:
    """会话 + 实体记忆。计划缓存的 SQLite 侧也在此统一管理。"""

    # ── 会话 ──

    def create_session(self, session_key: str | None = None, title: str = "新对话") -> AgentSession:
        """创建或按 session_key 复用会话。"""
        db = SessionLocal()
        try:
            if session_key:
                sess = db.query(AgentSession).filter(AgentSession.session_key == session_key).first()
                if sess:
                    return sess
            import uuid
            key = session_key or f"sess_{uuid.uuid4().hex[:12]}"
            sess = AgentSession(session_key=key, title=title)
            db.add(sess)
            db.commit()
            db.refresh(sess)
            return sess
        finally:
            db.close()

    def get_session(self, session_id: int) -> Optional[AgentSession]:
        db = SessionLocal()
        try:
            return db.query(AgentSession).filter(AgentSession.id == session_id).first()
        finally:
            db.close()

    def add_message(self, session_id: int, role: str, content: str,
                    msg_type: str = "chat", payload: dict | None = None,
                    llm_calls: int = 0) -> AgentMessage:
        db = SessionLocal()
        try:
            msg = AgentMessage(
                session_id=session_id, role=role, content=content,
                msg_type=msg_type,
                payload_json=json.dumps(payload, ensure_ascii=False) if payload else None,
                llm_calls=llm_calls,
            )
            db.add(msg)
            # 首条 user 消息自动生成会话标题
            sess = db.query(AgentSession).filter(AgentSession.id == session_id).first()
            if sess and sess.title == "新对话" and role == "user" and len(content) > 0:
                sess.title = content[:30]
            db.commit()
            db.refresh(msg)
            return msg
        finally:
            db.close()

    def recent_messages(self, session_id: int, limit: int = 10) -> list[dict]:
        """最近 N 条消息，供大脑/planner 上下文注入（每条截断 500 字）。"""
        db = SessionLocal()
        try:
            msgs = (db.query(AgentMessage)
                    .filter(AgentMessage.session_id == session_id)
                    .order_by(AgentMessage.id.desc())
                    .limit(limit).all())
            return [{"role": m.role, "content": m.content[:500]} for m in reversed(msgs)]
        finally:
            db.close()

    def list_sessions(self) -> list[dict]:
        db = SessionLocal()
        try:
            from sqlalchemy import func
            rows = (db.query(AgentSession, func.count(AgentMessage.id).label("message_count"))
                    .outerjoin(AgentMessage, AgentMessage.session_id == AgentSession.id)
                    .group_by(AgentSession.id)
                    .order_by(AgentSession.updated_at.desc())
                    .all())
            return [{
                "id": s.id, "session_key": s.session_key, "title": s.title,
                "status": s.status, "message_count": cnt,
                "created_at": s.created_at.strftime("%m-%d %H:%M") if s.created_at else "",
                "updated_at": s.updated_at.strftime("%m-%d %H:%M") if s.updated_at else "",
            } for s, cnt in rows]
        finally:
            db.close()

    def session_messages(self, session_id: int) -> list[dict]:
        db = SessionLocal()
        try:
            msgs = (db.query(AgentMessage)
                    .filter(AgentMessage.session_id == session_id)
                    .order_by(AgentMessage.id.asc()).all())
            return [{
                "id": m.id, "role": m.role, "content": m.content,
                "msg_type": m.msg_type,
                "payload": json.loads(m.payload_json) if m.payload_json else None,
                "llm_calls": m.llm_calls,
                "created_at": m.created_at.strftime("%m-%d %H:%M") if m.created_at else "",
            } for m in msgs]
        finally:
            db.close()

    def delete_session(self, session_id: int) -> None:
        db = SessionLocal()
        try:
            db.query(AgentMessage).filter(AgentMessage.session_id == session_id).delete()
            db.query(AgentSession).filter(AgentSession.id == session_id).delete()
            db.commit()
        finally:
            db.close()

    def set_pending_plan(self, session_id: int, plan: dict | None) -> None:
        """追问机制：暂存未执行的 plan（执行后清空）。"""
        db = SessionLocal()
        try:
            sess = db.query(AgentSession).filter(AgentSession.id == session_id).first()
            if sess:
                sess.pending_plan_json = json.dumps(plan, ensure_ascii=False) if plan else None
                db.commit()
        finally:
            db.close()

    def get_pending_plan(self, session_id: int) -> Optional[dict]:
        db = SessionLocal()
        try:
            sess = db.query(AgentSession).filter(AgentSession.id == session_id).first()
            if sess and sess.pending_plan_json:
                try:
                    return json.loads(sess.pending_plan_json)
                except json.JSONDecodeError:
                    return None
            return None
        finally:
            db.close()

    # ── 实体记忆 ──

    def upsert_entity(self, etype: str, key: str, value: str, source: str = "rule") -> AgentEntity:
        db = SessionLocal()
        try:
            ent = (db.query(AgentEntity)
                   .filter(AgentEntity.entity_type == etype, AgentEntity.entity_key == key)
                   .first())
            if ent:
                ent.entity_value = value
                ent.source = source
            else:
                ent = AgentEntity(entity_type=etype, entity_key=key, entity_value=value, source=source)
                db.add(ent)
            db.commit()
            db.refresh(ent)
            return ent
        finally:
            db.close()

    def get_entities(self, etype: str | None = None) -> list[dict]:
        db = SessionLocal()
        try:
            q = db.query(AgentEntity)
            if etype:
                q = q.filter(AgentEntity.entity_type == etype)
            return [{
                "id": e.id, "entity_type": e.entity_type, "entity_key": e.entity_key,
                "entity_value": e.entity_value, "source": e.source,
                "confidence": e.confidence,
            } for e in q.order_by(AgentEntity.id.asc()).all()]
        finally:
            db.close()

    def delete_entity(self, entity_id: int) -> None:
        db = SessionLocal()
        try:
            db.query(AgentEntity).filter(AgentEntity.id == entity_id).delete()
            db.commit()
        finally:
            db.close()

    def clear_entities(self) -> int:
        db = SessionLocal()
        try:
            n = db.query(AgentEntity).count()
            db.query(AgentEntity).delete()
            db.commit()
            return n
        finally:
            db.close()

    def inject_entities(self, prompt: str) -> str:
        """0 LLM：把实体偏好拼成前缀注入 prompt。"""
        ents = self.get_entities()
        if not ents:
            return prompt
        lines = []
        type_labels = {"owner": "常用负责人", "language": "常用语言", "style": "偏好风格", "fact": "已知事实"}
        for e in ents:
            label = type_labels.get(e.entity_type, e.entity_type)
            lines.append(f"{label}：{e.entity_key}={e.entity_value}")
        prefix = "已知用户偏好：" + "；".join(lines)
        return f"{prefix}\n\n{prompt}"

    # ── 计划缓存（SQLite 侧）──

    def plan_cache_add(self, query: str, query_md5: str, plan: dict, title: str = "") -> AgentPlanCache:
        db = SessionLocal()
        try:
            row = (db.query(AgentPlanCache)
                   .filter(AgentPlanCache.query_md5 == query_md5).first())
            if row:  # 已存在则更新
                row.plan_json = json.dumps(plan, ensure_ascii=False)
                row.title = title
                row.node_count = len(plan.get("nodes", []))
                db.commit()
                return row
            row = AgentPlanCache(
                query_text=query, query_md5=query_md5,
                plan_json=json.dumps(plan, ensure_ascii=False),
                title=title, node_count=len(plan.get("nodes", [])),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row
        finally:
            db.close()

    def plan_cache_find(self, query_md5: str | None = None, cache_id: int | None = None) -> Optional[dict]:
        """按 md5 或 id 查找缓存行（plan_json 已解析）。"""
        db = SessionLocal()
        try:
            q = db.query(AgentPlanCache)
            if query_md5:
                q = q.filter(AgentPlanCache.query_md5 == query_md5)
            elif cache_id is not None:
                q = q.filter(AgentPlanCache.id == cache_id)
            row = q.first()
            if not row:
                return None
            return {"id": row.id, "query_text": row.query_text, "query_md5": row.query_md5,
                    "plan": json.loads(row.plan_json) if row.plan_json else None,
                    "title": row.title}
        finally:
            db.close()

    def plan_cache_hit(self, cache_id: int) -> None:
        """命中计数 + 刷新 last_used_at。"""
        db = SessionLocal()
        try:
            row = db.query(AgentPlanCache).filter(AgentPlanCache.id == cache_id).first()
            if row:
                row.hit_count = (row.hit_count or 0) + 1
                from datetime import datetime
                row.last_used_at = datetime.now()
                db.commit()
        finally:
            db.close()

    def plan_cache_list(self) -> list[dict]:
        db = SessionLocal()
        try:
            rows = db.query(AgentPlanCache).order_by(AgentPlanCache.last_used_at.desc()).all()
            return [{
                "id": r.id, "query_text": r.query_text[:80], "title": r.title,
                "node_count": r.node_count, "hit_count": r.hit_count,
                "status": r.status,
                "last_used_at": r.last_used_at.strftime("%m-%d %H:%M") if r.last_used_at else "",
            } for r in rows]
        finally:
            db.close()

    def plan_cache_delete(self, cache_id: int | None = None) -> int:
        """删除单条或清空，返回删除行。"""
        db = SessionLocal()
        try:
            q = db.query(AgentPlanCache)
            if cache_id is not None:
                q = q.filter(AgentPlanCache.id == cache_id)
            rows = q.all()
            for r in rows:
                db.delete(r)
            db.commit()
            return len(rows)
        finally:
            db.close()

    def plan_cache_oldest(self, limit: int = 50) -> list[dict]:
        """LRU 淘汰：按 last_used_at 最旧的 N 条（返回 id/query_md5）。"""
        db = SessionLocal()
        try:
            rows = (db.query(AgentPlanCache)
                    .order_by(AgentPlanCache.last_used_at.asc())
                    .limit(limit).all())
            return [{"id": r.id, "query_md5": r.query_md5} for r in rows]
        finally:
            db.close()


# 全局单例
memory_service = MemoryService()
