"""
向量嵌入服务 — 文本转向量，FAISS 搜索。
注意：首次使用需下载模型，约 1.3GB。

多个实例（RAG 知识库 / Agent 计划缓存）共用同一个 SentenceTransformer，
各持独立 FAISS 索引，物理隔离互不污染。
"""

import os
import json
import threading
from typing import Optional
import numpy as np

from backend.config import config

# 共享模型懒加载（模型 1.3GB，全局只加载一份）
# 注意：必须是可重入锁 — encode() 持锁时会调用 _get_shared_model()，
# 后者同样需要持锁（RLock 允许同一线程重复获取，普通 Lock 会自我死锁）
_model_lock = threading.RLock()
_shared_model = None


def _get_shared_model():
    global _shared_model
    with _model_lock:
        if _shared_model is None:
            from sentence_transformers import SentenceTransformer
            print(f"加载嵌入模型: {config.embedding_model} ...")
            _shared_model = SentenceTransformer(config.embedding_model)
            print("嵌入模型就绪。")
    return _shared_model


class EmbeddingService:
    """文本嵌入 + FAISS 向量搜索。"""

    def __init__(self, index_path: Optional[str] = None, chunks_path: Optional[str] = None):
        self._index = None
        self._chunks: list[dict] = []  # [{id, text, ...meta}]
        # 默认指向 RAG 知识库路径（向后兼容）；传入自定义路径即可独立索引
        self._index_path = index_path or os.path.join(config.knowledge_base_dir, "faiss.index")
        self._chunks_path = chunks_path or os.path.join(config.knowledge_base_dir, "chunks.json")

    def _ensure_index_loaded(self):
        if self._index is not None:
            return
        try:
            import faiss
            if os.path.exists(self._index_path):
                self._index = faiss.read_index(self._index_path)
                with open(self._chunks_path, "r") as f:
                    self._chunks = json.load(f)
            else:
                self._index = faiss.IndexFlatL2(1024)  # BGE-large embedding dim
                self._chunks = []
        except ImportError:
            raise ImportError("请安装 faiss-cpu: pip install faiss-cpu")

    def encode(self, texts: list[str], normalize_embeddings: bool = True) -> np.ndarray:
        """共享模型编码（加锁，RAG 与 PlanCache 并发安全）。"""
        with _model_lock:
            return _get_shared_model().encode(texts, normalize_embeddings=normalize_embeddings)

    def add_document(self, text: str, doc_name: str, chunk_size: int = 500):
        """将文档分块并添加到知识库。"""
        self._ensure_index_loaded()

        # 分块
        chunks = []
        for i in range(0, len(text), chunk_size - 50):
            chunk_text = text[i:i + chunk_size]
            if len(chunk_text) < 50:
                continue
            chunks.append(chunk_text)

        if not chunks:
            return 0

        # 向量化
        embeddings = self.encode(chunks)

        # 加入索引
        self._index.add(np.array(embeddings, dtype=np.float32))

        # 记录 chunks
        for j, chunk_text in enumerate(chunks):
            self._chunks.append({
                "id": len(self._chunks),
                "text": chunk_text,
                "doc_name": doc_name,
            })

        self._save()
        return len(chunks)

    def add_items(self, items: list[dict]) -> int:
        """批量添加 {id, text, ...meta} 条目（Agent 计划缓存等用）。"""
        self._ensure_index_loaded()
        if not items:
            return 0
        embeddings = self.encode([it["text"] for it in items])
        self._index.add(np.array(embeddings, dtype=np.float32))
        self._chunks.extend(items)
        self._save()
        return len(items)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """搜索最相关的文档片段。"""
        self._ensure_index_loaded()
        if self._index.ntotal == 0:
            return []

        query_vec = self.encode([query])
        distances, indices = self._index.search(np.array(query_vec, dtype=np.float32), top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            results.append({
                **self._chunks[idx],
                "distance": float(dist),
                "score": float(1 - dist),  # 保留旧字段（非余弦，RAG 显示用）
            })
        return results

    @property
    def ntotal(self) -> int:
        """索引条目数。"""
        self._ensure_index_loaded()
        return self._index.ntotal

    def remove(self, ids: list[int]) -> int:
        """删除指定 id 的 chunks 并重建索引（LRU 淘汰用）。"""
        self._ensure_index_loaded()
        if not ids or self._index.ntotal == 0:
            return 0
        idset = set(ids)
        kept = [c for c in self._chunks if c.get("id") not in idset]
        removed_count = len(self._chunks) - len(kept)
        if removed_count == 0:
            return 0
        self._chunks = kept
        import faiss
        self._index = faiss.IndexFlatL2(1024)
        if kept:
            embeddings = self.encode([c["text"] for c in kept])
            self._index.add(np.array(embeddings, dtype=np.float32))
        self._save()
        return removed_count

    def list_documents(self) -> list[dict]:
        """列出知识库中的文档。"""
        self._ensure_index_loaded()
        doc_names = list(set(c["doc_name"] for c in self._chunks))
        return [{"name": name, "chunks": sum(1 for c in self._chunks if c["doc_name"] == name)}
                for name in doc_names]

    def _save(self):
        import faiss
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss.write_index(self._index, self._index_path)
        with open(self._chunks_path, "w") as f:
            json.dump(self._chunks, f, ensure_ascii=False)

    @property
    def is_ready(self) -> bool:
        self._ensure_index_loaded()
        return self._index.ntotal > 0


# 全局单例（RAG 知识库）
embedding_service = EmbeddingService()
