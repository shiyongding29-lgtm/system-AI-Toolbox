"""
ORM 数据模型。
"""

import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, Float, UniqueConstraint

from backend.database import Base


class HistoryRecord(Base):
    """统一的历史记录表 — 所有工具模块共用。"""
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tool_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    input_preview = Column(Text, nullable=True)
    output_preview = Column(Text, nullable=True)
    full_output = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)


class TodoItem(Base):
    """待办事项。"""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task = Column(String(500), nullable=False)
    owner = Column(String(100), nullable=True)
    deadline = Column(String(100), nullable=True)
    priority = Column(Integer, nullable=False, default=2)
    completed = Column(Boolean, default=False)
    source = Column(String(100), nullable=True)
    source_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    month_key = Column(String(7), nullable=False, index=True)  # YYYY-MM


class MeetingRecord(Base):
    """会议记录。"""
    __tablename__ = "meeting_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey("history.id"), nullable=True)
    transcript = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    mode = Column(String(20), nullable=False, default="live")
    audio_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())


class DocumentRecord(Base):
    """上传的文档。"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey("history.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(50), nullable=False)
    extracted_text = Column(Text, nullable=True)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())


class RagDocument(Base):
    """RAG 知识库文档分块。"""
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())


class WeeklyReport(Base):
    """周报记录。"""
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    history_id = Column(Integer, ForeignKey("history.id"), nullable=True)
    week_start = Column(String(20), nullable=False)
    week_end = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())


# ═══════════════════════════════════════════════════════════════
# Agent 记忆层
# ═══════════════════════════════════════════════════════════════

class AgentSession(Base):
    """Agent 对话会话。"""
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_key = Column(String(100), nullable=False, unique=True)
    title = Column(String(200), nullable=False, default="新对话")
    pending_plan_json = Column(Text, nullable=True)  # 追问流程暂存的 plan
    status = Column(String(20), nullable=False, default="active")  # active | archived
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class AgentMessage(Base):
    """Agent 会话消息。"""
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user | assistant | system
    content = Column(Text, nullable=False)
    msg_type = Column(String(30), nullable=False, default="chat")  # chat|fast_action|workflow|steps|error
    payload_json = Column(Text, nullable=True)  # steps 时间线/actions/plan 摘要
    llm_calls = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now(), index=True)


class AgentEntity(Base):
    """Agent 实体记忆（用户偏好，全局共享）。"""
    __tablename__ = "agent_entities"
    __table_args__ = (UniqueConstraint("entity_type", "entity_key"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)  # owner | language | style | fact
    entity_key = Column(String(200), nullable=False)
    entity_value = Column(String(500), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(20), nullable=False, default="rule")  # rule | llm | planner
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime, default=func.now())


class AgentPlanCache(Base):
    """Agent 计划复用缓存（SQLite 侧；向量存独立 FAISS 索引）。"""
    __tablename__ = "agent_plan_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_text = Column(Text, nullable=False)
    query_md5 = Column(String(32), nullable=False, unique=True)  # 精确匹配短路
    plan_json = Column(Text, nullable=False)
    title = Column(String(300), nullable=True)
    node_count = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="success")
    hit_count = Column(Integer, nullable=False, default=0)
    last_used_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
