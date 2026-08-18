"""
Skill 注册表 — 文件夹式技能包：发现 / 加载 / 匹配 / 创建 / 删除。

技能 = 描述 + 方法论(prompt.md) + 默认流程(plan.json)，文件夹即真相源：
  backend/skills/<skill-id>/{skill.json, prompt.md, plan.json}

匹配通道（无嵌入模型也能用）：
  ① 名称/别名精确匹配（0 LLM）
  ② 描述向量相似（cos ≥ skill_match_threshold，需 sentence_transformers）
  ③ 异常优雅降级为 None（调用方走 brain LLM kind="skill"）
"""

import json
import logging
import os
import re
import shutil
import threading
from dataclasses import dataclass, field
from typing import Optional

from backend.config import config
from backend.routers.tools_registry import TOOLS_BY_ID
from backend.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# _resolve_inputs 的 text 回退链（workflow_engine.py）——边串联规则必须逐字对齐
TEXT_FALLBACK_CHAIN = ["transcript", "summary", "markdown", "hint", "topic", "question",
                       "tasks", "document", "translated_text", "outline", "report", "diff", "plan"]


@dataclass
class Skill:
    id: str
    name: str
    description: str
    icon: str
    color: str
    prompt: str
    plan: dict
    builtin: bool = False
    aliases: list = field(default_factory=list)
    input_hint: str = ""
    version: str = "1.0.0"
    path: str = ""
    triggers: list = field(default_factory=list)
    type: str = "workflow"  # workflow=流程型(有plan.json) / knowledge=知识型(仅方法论)

    @property
    def node_labels(self) -> list[str]:
        return [n.get("label", n.get("tool", "")) for n in self.plan.get("nodes", [])]

    def summary(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "icon": self.icon, "color": self.color, "builtin": self.builtin,
            "aliases": self.aliases, "input_hint": self.input_hint,
            "version": self.version, "node_labels": self.node_labels,
            "type": self.type,
        }

    def detail(self) -> dict:
        d = self.summary()
        d["prompt"] = self.prompt
        d["plan"] = self.plan
        return d


class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._lock = threading.Lock()
        self._dir_mtime: float = 0
        self._cache = EmbeddingService(
            index_path=os.path.join(config.agent_data_dir, "skills.faiss"),
            chunks_path=os.path.join(config.agent_data_dir, "skill_chunks.json"),
        )

    # ── 发现与加载 ──

    def discover(self, force: bool = False) -> dict[str, Skill]:
        """扫描 skills_dir 下所有 skill.json。坏包记日志跳过，不抛异常。"""
        with self._lock:
            if not force and self._skills and self._dir_current():
                return self._skills
            skills: dict[str, Skill] = {}
            if not os.path.isdir(config.skills_dir):
                os.makedirs(config.skills_dir, exist_ok=True)
            for entry in sorted(os.listdir(config.skills_dir)):
                skill_dir = os.path.join(config.skills_dir, entry)
                meta_path = os.path.join(skill_dir, "skill.json")
                if not os.path.isfile(meta_path):
                    continue
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    skill = self._load_skill(skill_dir, meta)
                    if skill:
                        skills[skill.id] = skill
                except Exception:
                    logger.exception("技能加载失败，跳过: %s", entry)
            self._skills = skills
            self._dir_mtime = self._dir_stat()
            logger.info("已发现 %d 个技能: %s", len(skills), ", ".join(skills.keys()))
            return skills

    def _dir_current(self) -> bool:
        return self._dir_stat() == self._dir_mtime

    @staticmethod
    def _dir_stat() -> float:
        try:
            return os.stat(config.skills_dir).st_mtime
        except OSError:
            return 0

    def _load_skill(self, skill_dir: str, meta: dict) -> Optional[Skill]:
        prompt = ""
        prompt_path = os.path.join(skill_dir, "prompt.md")
        if os.path.isfile(prompt_path):
            with open(prompt_path) as f:
                prompt = f.read()
        plan = {}
        plan_path = os.path.join(skill_dir, "plan.json")
        if os.path.isfile(plan_path):
            with open(plan_path) as f:
                plan = json.load(f)

        # 有 plan.json 且含节点 → 流程型；否则 → 知识型（仅方法论，大脑自定流程）
        if plan.get("nodes"):
            problems = validate_skill_plan(plan)
            if problems:
                logger.warning("技能 %s 的 plan 有问题，跳过: %s", meta.get("id"), "; ".join(problems))
                return None
            skill_type = "workflow"
        else:
            plan = {}
            skill_type = "knowledge"

        return Skill(
            id=meta["id"], name=meta.get("name", meta["id"]),
            description=meta.get("description", ""), icon=meta.get("icon", "🧩"),
            color=meta.get("color", "#8b5cf6"), prompt=prompt, plan=plan,
            builtin=meta.get("builtin", False), aliases=meta.get("aliases", []),
            input_hint=meta.get("input_hint", ""), version=meta.get("version", "1.0.0"),
            path=skill_dir, triggers=meta.get("triggers", []), type=skill_type,
        )

    def _ensure_fresh(self):
        if self._dir_current():
            return
        self.discover(force=True)
        try:
            self.rebuild_index()
        except Exception:
            logger.exception("技能向量索引重建失败")

    # ── 查询 ──

    def list_skills(self) -> list[dict]:
        self._ensure_fresh()
        return [s.summary() for s in self._skills.values()]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        self._ensure_fresh()
        return self._skills.get(skill_id)

    def skills_summary_text(self) -> str:
        self._ensure_fresh()
        lines = []
        for s in self._skills.values():
            alias_text = f"（别名：{'、'.join(s.aliases[:3])}）" if s.aliases else ""
            type_hint = "（知识型·无固定流程，命中后按方法论自行决定工具）" if s.type == "knowledge" else ""
            lines.append(f'- {s.id}: {s.name} — {s.description}{type_hint}{alias_text}')
        return "\n".join(lines) if lines else "(无)"

    # ── 匹配 ──

    def search(self, query: str) -> Optional[dict]:
        """返回 {"skill": Skill, "score": float, "source": "skill_exact"|"skill"} 或 None。"""
        q = (query or "").strip()
        if not q:
            return None
        self._ensure_fresh()

        # ① 名称/别名精确匹配（0 LLM，无嵌入模型可用）
        for s in self._skills.values():
            if q == s.id or q == s.name or q in s.aliases:
                return {"skill": s, "score": 1.0, "source": "skill_exact"}
            # 文本以「技能名+冒号/，」开头 → 视为点名该技能
            for name in [s.name, *s.aliases]:
                if q.startswith(name) and len(q) > len(name) and q[len(name)] in "：:，,。. ":
                    return {"skill": s, "score": 1.0, "source": "skill_exact"}
            # 触发词子串匹配（不限长度；触发词本身较具体，误伤风险低）
            q_lower = q.lower()
            for tg in s.triggers:
                if tg.lower() in q_lower:
                    return {"skill": s, "score": 1.0, "source": "skill_exact"}

        # ② 描述向量相似（需嵌入模型；不可用则优雅降级）
        try:
            hits = self._cache.search(q, top_k=1)
            if hits:
                dist = hits[0].get("distance", 0.0)
                cos = max(0.0, 1 - (dist ** 2) / 2)
                if cos >= config.skill_match_threshold:
                    skill_id = hits[0].get("id")
                    skill = self._skills.get(skill_id)
                    if skill:
                        return {"skill": skill, "score": round(cos, 4), "source": "skill"}
        except Exception:
            logger.debug("技能向量检索不可用，跳过（无嵌入模型？）")
        return None

    # ── 索引 ──

    def rebuild_index(self) -> None:
        """全量重建向量索引（chunks id = skill.id，技能数量级小）。"""
        items = [{"id": s.id, "text": f"{s.name} {s.description}"}
                 for s in self._skills.values()]
        # 清空旧索引（重建比增量简单可靠）
        self._cache = EmbeddingService(
            index_path=os.path.join(config.agent_data_dir, "skills.faiss"),
            chunks_path=os.path.join(config.agent_data_dir, "skill_chunks.json"),
        )
        if items:
            self._cache.add_items(items)

    # ── 创建 / 删除 ──

    def create_skill(self, payload: dict) -> tuple[Optional[Skill], Optional[str]]:
        """前端创建：{name, description, icon, color, prompt, tool_ids[有序], skill_type}。

        skill_type="knowledge" 时为知识型（无 plan.json，仅方法论，大脑自定流程）。
        """
        name = (payload.get("name") or "").strip()
        description = (payload.get("description") or "").strip()
        prompt = (payload.get("prompt") or "").strip()
        tool_ids = payload.get("tool_ids") or []
        skill_type = payload.get("skill_type") or "workflow"
        if not name:
            return None, "技能名称不能为空"
        if len(name) > 50:
            return None, "技能名称过长（≤50 字）"
        if not prompt:
            return None, "方法论（prompt）不能为空"
        if skill_type == "workflow" and not tool_ids:
            return None, "流程型技能至少选择一个工具"
        for tid in tool_ids:
            if tid not in TOOLS_BY_ID:
                return None, f"未知工具: {tid}"

        skill_id = slugify(name)
        base_id = skill_id
        i = 2
        while os.path.exists(os.path.join(config.skills_dir, skill_id)):
            skill_id = f"{base_id}-{i}"
            i += 1

        skill_dir = os.path.join(config.skills_dir, skill_id)
        os.makedirs(skill_dir, exist_ok=True)
        meta = {
            "id": skill_id, "name": name, "description": description,
            "icon": payload.get("icon", "🧩"), "color": payload.get("color", "#8b5cf6"),
            "version": "1.0.0", "builtin": False,
            "aliases": [a.strip() for a in (payload.get("aliases") or []) if a.strip()],
            "input_hint": payload.get("input_hint") or "粘贴输入文本",
            "tags": payload.get("tags") or [],
        }
        with open(os.path.join(skill_dir, "skill.json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        with open(os.path.join(skill_dir, "prompt.md"), "w") as f:
            f.write(prompt)
        warnings = []
        if skill_type == "workflow":
            plan, warnings = build_skill_plan(tool_ids)
            with open(os.path.join(skill_dir, "plan.json"), "w") as f:
                json.dump(plan, f, ensure_ascii=False, indent=2)

        self.discover(force=True)
        try:
            self.rebuild_index()
        except Exception:
            logger.exception("技能向量索引重建失败")
        return self._skills.get(skill_id), (warnings[0] if warnings else None)

    def delete_skill(self, skill_id: str) -> tuple[bool, Optional[str]]:
        skill = self.get_skill(skill_id)
        if not skill:
            return False, "技能不存在"
        if skill.builtin:
            return False, "内置技能不可删除"
        shutil.rmtree(skill.path, ignore_errors=True)
        self.discover(force=True)
        try:
            self.rebuild_index()
        except Exception:
            logger.exception("技能向量索引重建失败")
        return True, None


# ── 边自动串联（对齐 _resolve_inputs 的回退链）──

def build_skill_plan(tool_ids: list[str]) -> tuple[dict, list[str]]:
    """按工具顺序生成 nodes/edges。返回 (plan, warnings)。"""
    nodes = [{"id": f"n{i + 1}", "tool": tid, "label": TOOLS_BY_ID[tid]["name"]}
             for i, tid in enumerate(tool_ids)]
    edges = []
    warnings = []

    for i in range(len(nodes) - 1):
        a, b = nodes[i], nodes[i + 1]
        a_outs = TOOLS_BY_ID[a["tool"]]["outputs"]
        b_ins = TOOLS_BY_ID[b["tool"]]["inputs"]
        from_output = None

        # ① 专用键：A 输出 ∩ B 输入，且不是 text
        special = [o for o in a_outs if o in b_ins and o != "text"]
        if special:
            from_output = special[0]
        else:
            # ② text 链路：A 输出落在回退链且 B 要 text
            fallback = [o for o in a_outs if o in TEXT_FALLBACK_CHAIN]
            if fallback and ("text" in b_ins or not b_ins):
                from_output = fallback[0]
            # ③ B 要 text 或空输入 → 不写 fromOutput（引擎合并兜底）
            elif "text" in b_ins or not b_ins:
                from_output = None
            else:
                warnings.append(f"⚠️ 「{TOOLS_BY_ID[a['tool']]['name']}」的输出无法直接满足「{TOOLS_BY_ID[b['tool']]['name']}」的输入")

        edge = {"from": a["id"], "to": b["id"]}
        if from_output:
            edge["fromOutput"] = from_output
        edges.append(edge)

    first = TOOLS_BY_ID[nodes[0]["tool"]]
    if "file" in first.get("inputs", []):
        input_kind = "file"
    elif nodes[0]["tool"] == "meeting_recorder":
        input_kind = "paste_text_or_record_audio"
    else:
        input_kind = "paste_text"

    plan = {
        "title": "自定义技能",
        "description": " → ".join(TOOLS_BY_ID[tid]["name"] for tid in tool_ids),
        "input": input_kind,
        "nodes": nodes,
        "edges": edges,
    }
    return plan, warnings


def validate_skill_plan(plan: dict) -> list[str]:
    """执行前防线：tool 必须注册且有执行器。"""
    from backend.routers.workflow_engine import EXECUTORS
    problems = []
    nodes = plan.get("nodes") or []
    if not nodes:
        return ["plan 没有节点"]
    for n in nodes:
        tid = n.get("tool", "")
        if tid not in TOOLS_BY_ID:
            problems.append(f"未知工具 {tid}")
        elif tid not in EXECUTORS:
            problems.append(f"工具 {tid} 无执行器（尚不可在技能中使用）")
    return problems


def slugify(name: str) -> str:
    """中文名 → 拼音不可行，直接保留中文 + 安全字符过滤。"""
    s = re.sub(r'[^\w一-鿿-]', '-', name.strip().lower(), flags=re.UNICODE)
    s = re.sub(r'-+', '-', s).strip('-')
    return s or "skill"


# 全局单例
skill_registry = SkillRegistry()
