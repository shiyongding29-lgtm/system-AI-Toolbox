"""
Agent 计划复用缓存 — 相似任务直接复用历史 plan（0 LLM）。

- 向量侧：独立 FAISS 索引（与 RAG 索引物理隔离，共享嵌入模型）
- SQLite 侧：memory_service 的 agent_plan_cache 表
- 相似度：cos = 1 - L2²/2（归一化向量下与 L2 的换算）
- 只缓存 plan 本体（nodes/edges），不缓存执行结果
"""

import hashlib
import logging
import os
import threading

from backend.config import config
from backend.services.embedding_service import EmbeddingService
from backend.services.memory_service import memory_service

logger = logging.getLogger(__name__)

MAX_PLANS = 500
EVICT_BATCH = 50


class PlanCache:
    def __init__(self, threshold: float | None = None):
        self.threshold = threshold if threshold is not None else config.plan_cache_threshold
        self._vec = EmbeddingService(
            index_path=os.path.join(config.agent_data_dir, "plans.faiss"),
            chunks_path=os.path.join(config.agent_data_dir, "plan_chunks.json"),
        )
        self._lock = threading.RLock()  # 可重入：防御性，避免嵌套调用自我死锁

    def search_exact(self, query: str) -> dict | None:
        """仅 MD5 精确查找（0 LLM，无嵌入模型也可用）。供 skill 层之前的最高优先级匹配。"""
        q = (query or "").strip()
        if not q:
            return None
        q_md5 = hashlib.md5(q.encode()).hexdigest()
        with self._lock:
            row = memory_service.plan_cache_find(query_md5=q_md5)
            if row and row.get("plan"):
                memory_service.plan_cache_hit(row["id"])
                return {"plan": row["plan"], "score": 1.0,
                        "cache_id": row["id"], "source": "plan_cache_exact"}
        return None

    def search(self, query: str) -> dict | None:
        """返回 {"plan": dict, "score": float, "cache_id": int, "source": str} 或 None。"""
        q = (query or "").strip()
        if not q:
            return None
        q_md5 = hashlib.md5(q.encode()).hexdigest()

        with self._lock:
            # ① MD5 精确短路（免编码，免向量检索）
            row = memory_service.plan_cache_find(query_md5=q_md5)
            if row and row.get("plan"):
                memory_service.plan_cache_hit(row["id"])
                return {"plan": row["plan"], "score": 1.0,
                        "cache_id": row["id"], "source": "plan_cache_exact"}

            # ② 向量相似度匹配（需嵌入模型；不可用时优雅降级为未命中）
            try:
                hits = self._vec.search(q, top_k=1)
            except Exception:
                logger.exception("计划缓存向量检索失败（嵌入模型不可用？），降级为未命中")
                return None
            if not hits:
                return None
            h = hits[0]
            dist = h.get("distance", 0.0)
            cos = max(0.0, 1 - (dist ** 2) / 2)  # 归一化向量：cos = 1 - L2²/2
            if cos < self.threshold:
                return None
            cache_id = h.get("id")
            row = memory_service.plan_cache_find(cache_id=cache_id)
            if row and row.get("plan"):
                memory_service.plan_cache_hit(cache_id)
                return {"plan": row["plan"], "score": round(cos, 4),
                        "cache_id": cache_id, "source": "plan_cache"}

        return None

    def add(self, query: str, plan: dict) -> int | None:
        """执行成功后写入缓存（SQLite + FAISS 双写），返回 cache_id。"""
        q = (query or "").strip()
        if not q or not plan.get("nodes"):
            return None
        q_md5 = hashlib.md5(q.encode()).hexdigest()
        title = plan.get("title", "")

        with self._lock:
            row = memory_service.plan_cache_find(query_md5=q_md5)
            if row:
                # 已存在：只更新 SQLite（FAISS 向量不变）
                memory_service.plan_cache_add(q, q_md5, plan, title)
                return row["id"]
            new_row = memory_service.plan_cache_add(q, q_md5, plan, title)
            cache_id = new_row.id
            try:
                self._vec.add_items([{"id": cache_id, "text": q}])
            except Exception:
                logger.exception("计划缓存向量写入失败，仅保留 SQLite 记录")
                return cache_id

            # LRU 淘汰：超出容量按 last_used_at 淘汰最旧一批
            try:
                if self._vec.ntotal > MAX_PLANS:
                    oldest = memory_service.plan_cache_oldest(EVICT_BATCH)
                    ids = [o["id"] for o in oldest]
                    self._vec.remove(ids)
                    for o in oldest:
                        memory_service.plan_cache_delete(o["id"])
            except Exception:
                logger.exception("计划缓存 LRU 淘汰失败")
            return cache_id

    def list(self) -> list[dict]:
        return memory_service.plan_cache_list()

    def delete(self, cache_id: int | None = None) -> int:
        """删除单条或清空（SQLite + FAISS 同步），返回删除数。"""
        with self._lock:
            if cache_id is not None:
                n = memory_service.plan_cache_delete(cache_id)
                try:
                    self._vec.remove([cache_id])
                except Exception:
                    logger.exception("计划缓存向量删除失败")
                return n
            rows = memory_service.plan_cache_list()
            n = memory_service.plan_cache_delete(None)
            try:
                self._vec.remove([r["id"] for r in rows])
            except Exception:
                logger.exception("计划缓存向量清空失败")
            return n


# 全局单例
plan_cache = PlanCache()
