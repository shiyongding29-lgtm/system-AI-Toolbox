"""
Agent 循环 — 感知 → 规划 → 执行 → 反思 → 输出 → 记忆。

LLM 预算：编排层最多 config.agent_max_llm_calls 次调用（大脑/规划/反思/润色）。
工具执行器内部的 LLM 调用是业务开销，不计入预算但计入 llm_calls_total。

只有「大脑」是大模型，其余（路由/记忆/缓存/规则校验）都是代码。
"""

import json
import logging
import re
import threading
import time
from datetime import date, timedelta

from backend.config import config
from backend.services.llm_service import llm_service, LLMError
from backend.services.memory_service import memory_service
from backend.services.prompt_library import AGENT_BRAIN_SYSTEM, AGENT_FINAL_SYSTEM
from backend.services import intent_router
from backend.routers.workflow_engine import (
    plan_workflow, run_workflow, get_workflow_status, EXECUTORS,
)
from backend.routers.tools_registry import TOOLS_BY_ID

logger = logging.getLogger(__name__)

WORKFLOW_TIMEOUT_SECONDS = 600

# 工具 → 前端页面路由（无执行器的工具走跳转动作）
TOOL_ROUTES = {
    "pomodoro": ("pomodoro", ["work"]),
    "email": ("email-doc", ["to", "hint", "mode"]),
    "translation": ("translation-assistant", ["text", "mode"]),
    "research": ("deep-research", ["topic"]),
    "ppt": ("ppt-outline", ["slides", "style"]),
    "summary": ("document-summary", []),
    "mindmap": ("mindmap", []),
    "data": ("data-analysis", []),
    "spreadsheet": ("spreadsheet", []),
    "meeting": ("meeting-recorder", []),
    "weekly_report": ("weekly-report", []),
    "task_planning": ("task-planning", []),
    "image-analyzer": ("image-analyzer", []),
    "chart-generator": ("chart-generator", []),
    "doc-compare": ("document-comparison", []),
    "multi-source": ("multi-source-reader", []),
    "rag-qa": ("rag-qa", []),
    "info-extraction": ("info-extraction", []),
    "table-generator": ("table-generator", []),
    "pdf-toolkit": ("pdf-toolkit", []),
    "sentiment-analyzer": ("sentiment-analyzer", []),
    "file-converter": ("file-converter", []),
    "todo-add": ("todos", []),
    "web-scraper": ("web-scraper", []),
    "qr-generator": ("qr-generator", []),
}

TOOL_LABELS = {
    "pomodoro": "🍅 番茄钟", "email": "✉️ 写邮件", "translation": "🌐 翻译",
    "research": "🔍 深度调研", "ppt": "📽️ PPT", "summary": "📄 文档摘要",
    "mindmap": "🧠 思维导图", "data": "📈 数据分析", "spreadsheet": "📊 智能表格",
    "meeting": "🎙️ 会议记录", "weekly_report": "📋 周报", "task_planning": "🗓️ 任务规划",
    "image-analyzer": "🖼️ 图片分析", "chart-generator": "📊 图表生成",
    "doc-compare": "⚖️ 文档对比", "multi-source": "📖 多源阅读", "rag-qa": "📚 知识库问答",
    "info-extraction": "📋 信息提取", "table-generator": "📋 表格生成",
    "pdf-toolkit": "📑 PDF工具", "sentiment-analyzer": "💬 情感分析",
    "file-converter": "🔄 文件转换", "todo-add": "✅ 待办列表",
    "web-scraper": "🕷️ 网页抓取", "qr-generator": "📱 QR码",
}

# 记住类规则（0 LLM 实体抽取）
ENTITY_PATTERNS = [
    (re.compile(r'记住[：:]?\s*[「"“]?(?:我的)?(常用)?(负责人|老板|经理|上级|联系人)[」"”]?\s*(?:是|为)\s*[「"“]?([^\s，。！？,]{1,20})'),
     lambda m: ("owner", "常用负责人" if m.group(1) else m.group(2), m.group(3))),
    (re.compile(r'(?:以后|以后请|请)?用(中文|英文|繁體中文|简体中文)(?:回复|交流|对话|输出)'),
     lambda m: ("language", "常用语言", m.group(1))),
]


# ═══════════════════════════════════════════════════════════════
# LLM 预算
# ═══════════════════════════════════════════════════════════════

class LLMBudget:
    def __init__(self, max_calls: int | None = None):
        self.max_calls = max_calls if max_calls is not None else config.agent_max_llm_calls
        self.used = 0

    @property
    def can(self) -> bool:
        return self.used < self.max_calls

    def spend(self) -> None:
        self.used += 1


# ═══════════════════════════════════════════════════════════════
# Turn 状态（内存态，仿 _workflows）
# ═══════════════════════════════════════════════════════════════

_turns: dict[str, dict] = {}
_turns_lock = threading.Lock()


def _new_turn(session_id: int) -> str:
    turn_id = f"t_{int(time.time() * 1000)}"
    with _turns_lock:
        _turns[turn_id] = {
            "turn_id": turn_id, "session_id": session_id,
            "status": "running", "steps": [],
            "final": {"content": "", "actions": [], "degraded": False},
            "llm_calls": 0, "source": "fast", "error": None,
        }
    return turn_id


def _step(turn_id: str, phase: str, label: str, status: str = "done", detail: str = ""):
    with _turns_lock:
        t = _turns.get(turn_id)
        if t is not None:
            t["steps"].append({"phase": phase, "label": label, "status": status, "detail": detail})


def _set_turn(turn_id: str, **kwargs):
    with _turns_lock:
        t = _turns.get(turn_id)
        if t is not None:
            t.update(kwargs)


def get_turn(turn_id: str) -> dict | None:
    with _turns_lock:
        return _turns.get(turn_id)


# ═══════════════════════════════════════════════════════════════
# Agent 循环
# ═══════════════════════════════════════════════════════════════

class AgentLoop:

    # ── 入口：同步段（路由在 router 层做，这里只跑 agent 路径）──

    def start_turn(self, session_id: int, text: str) -> str:
        turn_id = _new_turn(session_id)
        t = threading.Thread(target=self._execute_turn, args=(turn_id, session_id, text), daemon=True)
        t.start()
        return turn_id

    # ── 主循环 ──

    def _execute_turn(self, turn_id: str, session_id: int, text: str):
        budget = LLMBudget()
        try:
            # ① 感知
            self._perceive(turn_id, session_id, text)

            # 追问合并：上轮 plan 有 questions，本轮文本是答案 → 直接执行
            pending = memory_service.get_pending_plan(session_id)
            if pending:
                self._act_workflow(turn_id, pending, {"text": text}, budget)
                self._memorize(turn_id, session_id, text, plan=pending, success=True)
                return

            # ② 规划
            plan = self._plan(turn_id, session_id, text, budget)

            # 大脑判定为纯聊天
            if plan is None:
                return  # _plan 已写入 final（chat / error 路径）

            if plan.get("questions"):
                # 需要追问：暂存 plan，等用户回答
                memory_service.set_pending_plan(session_id, plan)
                reply = plan.get("reply", "还有几个信息需要确认") + "\n\n" + \
                    "\n".join(f"❓ {q}" for q in plan["questions"])
                _set_turn(turn_id, status="need_input",
                          final={"content": reply, "actions": [], "degraded": False},
                          source=plan.get("source", "llm"))
                return

            # ③ 执行
            success = self._act(turn_id, plan, text, budget)

            # ④ 反思（规则校验 → 格式类错误 LLM 修复 → 降级）
            success, degraded = self._reflect(turn_id, plan, text, success, budget)

            # ⑤ 输出
            self._output(turn_id, plan, text, success, degraded, budget)

            # ⑥ 记忆
            self._memorize(turn_id, session_id, text, plan=plan, success=success)

            _set_turn(turn_id, status="done")
        except Exception as e:
            logger.exception("Agent turn 执行失败")
            _step(turn_id, "output", "输出", "error", str(e)[:200])
            _set_turn(turn_id, status="error",
                      final={"content": f"⚠️ 处理过程中出现错误：{str(e)[:200]}", "actions": [], "degraded": True},
                      error=str(e))

    # ── ① 感知 ──

    def _perceive(self, turn_id: str, session_id: int, text: str):
        history = memory_service.recent_messages(session_id, limit=10)
        ents = memory_service.get_entities()
        detail = f"上下文 {len(history)} 条历史消息"
        if ents:
            detail += f"，{len(ents)} 条实体偏好"
        _step(turn_id, "perceive", "感知上下文", "done", detail)

    # ── ② 规划 ──

    def _plan(self, turn_id: str, session_id: int, text: str, budget: LLMBudget) -> dict | None:
        """返回 plan dict；None 表示本轮已在内部完成输出（chat/错误）。"""
        # a. 计划缓存（0 LLM）
        try:
            from backend.services.plan_cache import plan_cache
            hit = plan_cache.search_exact(text)
            if hit:
                plan = dict(hit["plan"])
                plan["source"] = hit.get("source", "plan_cache")
                _set_turn(turn_id, source="plan_cache", llm_calls=0)
                _step(turn_id, "plan", "规划（命中历史方案，0 LLM）", "done",
                      f'复用「{plan.get("title", "")}」相似度 {hit.get("score", 0)}')
                return plan
        except Exception:
            logger.exception("计划缓存查询失败")

        # b. 技能匹配（0 LLM：名称/别名精确 → 描述向量相似）
        knowledge_prompt = None
        try:
            from backend.services.skill_registry import skill_registry
            sh = skill_registry.search(text)
            if sh:
                sk = sh["skill"]
                if sk.type == "workflow" and sk.plan.get("nodes"):
                    # 流程型：直接用默认流程执行
                    plan = dict(sk.plan)
                    plan["source"] = "skill"
                    plan["skill_id"] = sk.id
                    plan["prompt_md"] = sk.prompt
                    _set_turn(turn_id, source="skill", llm_calls=0)
                    _step(turn_id, "plan", f'规划（命中技能「{sk.name}」，0 LLM）', "done",
                          f'{sk.description[:60]} 相似度 {sh.get("score", 0)}')
                    return plan
                else:
                    # 知识型技能：只注入方法论，交给大脑决定流程（不 return）
                    knowledge_prompt = sk.prompt
                    _set_turn(turn_id, source="knowledge_skill", llm_calls=0)
                    _step(turn_id, "plan", f'规划（命中知识型技能「{sk.name}」）', "done",
                          "注入方法论，由大脑决定流程")
        except Exception:
            logger.exception("技能匹配失败")

        # c. 计划缓存向量相似
        try:
            from backend.services.plan_cache import plan_cache
            hit = plan_cache.search(text)
            if hit:
                plan = dict(hit["plan"])
                plan["source"] = hit.get("source", "plan_cache")
                _set_turn(turn_id, source="plan_cache", llm_calls=0)
                _step(turn_id, "plan", "规划（命中历史方案，0 LLM）", "done",
                      f'复用「{plan.get("title", "")}」相似度 {hit.get("score", 0)}')
                return plan
        except Exception:
            logger.exception("计划缓存查询失败")

        # d. 大脑 LLM（1 次）
        if not budget.can:
            self._final_chat(turn_id, "处理复杂度超预算，请换个简单的说法试试")
            return None

        context = memory_service.recent_messages(session_id, limit=6)
        ctx_text = "\n".join(f"{m['role']}: {m['content'][:200]}" for m in context) if context else "(无)"
        tools_summary = "\n".join(
            f'- {t["id"]}: {t["name"]} — {t["description"]}' for t in TOOLS_BY_ID.values()
        )
        from backend.services.skill_registry import skill_registry
        skills_summary = skill_registry.skills_summary_text()
        brain_prompt = AGENT_BRAIN_SYSTEM.format(tools_summary=tools_summary, skills_summary=skills_summary)
        brain_prompt = memory_service.inject_entities(brain_prompt)
        user_msg = f"对话上下文：\n{ctx_text}"
        if knowledge_prompt:
            user_msg += f"\n\n已知技能方法论（请遵循它组织回答）：\n{knowledge_prompt}"
        user_msg += f"\n\n用户最新输入：{text}"

        try:
            raw = llm_service.complete(brain_prompt, user_msg, task_type="default")
        except LLMError as e:
            _step(turn_id, "plan", "规划（大脑）", "error", e.message)
            self._final_chat(turn_id, f"⚠️ {e.message}")
            return None
        budget.spend()
        _set_turn(turn_id, llm_calls=budget.used)

        decision = self._parse_json(raw)
        if not decision:
            _step(turn_id, "plan", "规划（大脑）", "done", "大脑输出无法解析，按聊天处理")
            self._final_chat(turn_id, raw[:500] or "我不太确定，能再说一遍吗？")
            return None

        kind = decision.get("kind", "chat")
        reply = decision.get("reply", "")

        # 实体抽取（大脑 JSON + 0 LLM 规则）
        for ent in decision.get("entities", []) or []:
            if ent.get("type") and ent.get("key") and ent.get("value"):
                memory_service.upsert_entity(ent["type"], ent["key"], ent["value"], source="llm")
        for pat, mapper in ENTITY_PATTERNS:
            m = pat.search(text)
            if m:
                etype, ekey, evalue = mapper(m)
                memory_service.upsert_entity(etype, ekey, evalue, source="rule")

        if kind == "chat":
            _step(turn_id, "plan", "规划（大脑判定为聊天）", "done")
            _set_turn(turn_id, source="brain_llm")
            self._final_chat(turn_id, reply or raw[:500])
            return None

        if kind == "skill":
            skill_id = decision.get("skill_id", "")
            sk = skill_registry.get_skill(skill_id)
            if not sk:
                _step(turn_id, "plan", "规划（大脑）", "error", f"未知技能 {skill_id}")
                self._final_chat(turn_id, reply or "抱歉，我无法处理这个请求")
                return None
            if not sk.plan.get("nodes"):
                # 知识型技能被大脑点名：用方法论润色生成实际回答（而非敷衍答应）
                _set_turn(turn_id, source="knowledge_skill")
                try:
                    polished = llm_service.complete(
                        AGENT_FINAL_SYSTEM,
                        f"技能方法论：\n{sk.prompt}\n\n用户请求：{text}",
                        task_type="default",
                    )
                    budget.spend()
                    _set_turn(turn_id, llm_calls=budget.used)
                    self._final_chat(turn_id, polished)
                except Exception:
                    logger.exception("知识型技能润色失败")
                    self._final_chat(turn_id, reply or raw[:500])
                return None
            plan = dict(sk.plan)
            plan["source"] = "skill"
            plan["skill_id"] = skill_id
            plan["prompt_md"] = sk.prompt
            _set_turn(turn_id, source="skill")
            _step(turn_id, "plan", f'规划（大脑选中技能「{sk.name}」）', "done", sk.description[:60])
            return plan

        if kind == "single_tool":
            tool_id = decision.get("tool", "")
            params = decision.get("params", {}) or {}
            if tool_id not in TOOLS_BY_ID:
                _step(turn_id, "plan", "规划（大脑）", "error", f"未知工具 {tool_id}")
                self._final_chat(turn_id, reply or "抱歉，我无法处理这个请求")
                return None
            _step(turn_id, "plan", "规划（单工具直达）", "done",
                  f'{TOOLS_BY_ID[tool_id].get("name", tool_id)}')
            _set_turn(turn_id, source="brain_llm")
            # 单工具伪装成单节点 plan 统一走执行链
            return {
                "title": TOOLS_BY_ID[tool_id].get("name", tool_id),
                "nodes": [{"id": "n1", "tool": tool_id, "label": TOOLS_BY_ID[tool_id].get("name", tool_id)}],
                "edges": [], "input": "text",
                "single_tool": True, "tool_id": tool_id, "params": params,
                "reply": reply, "source": "brain_llm", "llm_calls": 1,
                "prompt_md": knowledge_prompt,
            }

        if kind == "workflow":
            _step(turn_id, "plan", "规划（LLM 编排工作流）", "running")
            plan = plan_workflow(text)
            budget.spend()
            _set_turn(turn_id, llm_calls=budget.used)
            if "error" in plan:
                _step(turn_id, "plan", "规划（LLM 编排工作流）", "error", plan["error"])
                self._final_chat(turn_id, f"⚠️ 工作流规划失败：{plan['error']}，可在智能工作流页手动搭建")
                return None
            plan["source"] = "llm"
            if knowledge_prompt:
                plan["prompt_md"] = knowledge_prompt
            _set_turn(turn_id, source="llm")
            _step(turn_id, "plan", "规划（LLM 编排工作流）", "done",
                  f'{plan.get("title", "")} — {len(plan.get("nodes", []))} 个节点')
            return plan

        self._final_chat(turn_id, reply or "我不太确定，能再说一遍吗？")
        return None

    # ── ③ 执行 ──

    def _act(self, turn_id: str, plan: dict, text: str, budget: LLMBudget) -> bool:
        if plan.get("single_tool"):
            return self._act_single_tool(turn_id, plan, text)
        return self._act_workflow(turn_id, plan, {"text": text}, budget)

    def _act_single_tool(self, turn_id: str, plan: dict, text: str) -> bool:
        tool_id = plan.get("tool_id")
        params = dict(plan.get("params", {}) or {})
        if not params.get("text"):
            params["text"] = text
        executor = EXECUTORS.get(tool_id)
        if not executor:
            # 无执行器 → 降级为跳转工具页动作
            route = TOOL_ROUTES.get(tool_id)
            if route:
                _step(turn_id, "act", "执行（引导打开工具页）", "done", TOOL_LABELS.get(tool_id, tool_id))
                _set_turn(turn_id, final={
                    "content": plan.get("reply", f"这个功能需要你手动操作，已为你准备入口"),
                    "actions": [{"type": "open_tool", "route": route[0],
                                 "params": {k: params.get(k) for k in route[1] if params.get(k) is not None},
                                 "label": TOOL_LABELS.get(tool_id, tool_id)}],
                    "degraded": True,
                })
                return True
            _step(turn_id, "act", "执行", "error", f"{tool_id} 无执行器")
            return False
        try:
            _step(turn_id, "act", f"执行 {TOOLS_BY_ID[tool_id].get('name', tool_id)}", "done")
            result = executor(params)
            plan["_single_result"] = result
            return True
        except Exception as e:
            logger.exception("单工具执行失败")
            _step(turn_id, "act", f"执行 {tool_id}", "error", str(e)[:200])
            plan["_single_result"] = {"error": str(e)[:200]}
            return False

    def _act_workflow(self, turn_id: str, plan: dict, user_input: dict, budget: LLMBudget) -> bool:
        _step(turn_id, "act", f"执行工作流「{plan.get('title', '')}」", "running",
              f"{len(plan.get('nodes', []))} 个节点")
        wid = run_workflow(plan, user_input)
        deadline = time.time() + WORKFLOW_TIMEOUT_SECONDS
        last_status = None
        while time.time() < deadline:
            st = get_workflow_status(wid)
            if st and st.get("status") in ("done", "error"):
                last_status = st
                break
            time.sleep(0.5)
        if last_status is None:
            _step(turn_id, "act", "执行工作流", "error", "执行超时")
            plan["_workflow_result"] = {"error": "执行超时"}
            return False
        plan["_workflow_result"] = last_status.get("results", {})
        node_lines = [f'{n.get("label", n.get("tool"))}: {n.get("status")}' for n in last_status.get("nodes", [])]
        _step(turn_id, "act", "执行工作流", "done", "；".join(node_lines))
        return last_status.get("status") == "done"

    # ── ④ 反思 ──

    def _reflect(self, turn_id: str, plan: dict, text: str, success: bool, budget: LLMBudget) -> tuple[bool, bool]:
        """规则校验（0 LLM）→ 格式类错误 LLM 修复一次 → 再失败降级。返回 (success, degraded)。"""
        if success:
            return True, False

        from backend.services.reflector import reflector, LLM_REPAIRABLE

        # 统一成节点结果结构
        if plan.get("single_tool"):
            node_results = {"n1": plan.get("_single_result") or {},
                            "__tool_n1": plan.get("tool_id", "")}
        else:
            node_results = plan.get("_workflow_result") or {}

        findings = reflector.validate_workflow(node_results)
        if not findings:
            _step(turn_id, "reflect", "反思（无异常）", "done")
            return False, False

        detail = "；".join(f"{f['tool']}:{f['rule']}" for f in findings)[:150]
        _step(turn_id, "reflect", f"反思（发现 {len(findings)} 处异常）", "done", detail)

        repairable = [f for f in findings if f["rule"] in LLM_REPAIRABLE]
        if repairable and budget.can:
            budget.spend()
            _set_turn(turn_id, llm_calls=budget.used)
            _step(turn_id, "reflect", "反思（LLM 修复格式错误）", "running")
            repaired = reflector.repair(repairable, node_results, text)
            remaining = reflector.validate_workflow(repaired)
            _step(turn_id, "reflect", "反思（修复后复检）", "done",
                  f"剩余异常 {len(remaining)} 处")
            if not remaining:
                # 修复成功：更新结果，视为成功
                if plan.get("single_tool"):
                    plan["_single_result"] = repaired.get("n1", {})
                else:
                    plan["_workflow_result"] = repaired
                return True, False

        _step(turn_id, "reflect", "反思（降级输出，保留成功部分）", "done")
        return False, True

    # ── ⑤ 输出 ──

    def _output(self, turn_id: str, plan: dict, text: str, success: bool, degraded: bool, budget: LLMBudget):
        result = plan.get("_single_result") or plan.get("_workflow_result") or {}

        # 单工具结果直接展示
        if plan.get("single_tool"):
            content = self._format_single_result(plan, result, success)
            _set_turn(turn_id, final={"content": content, "actions": [], "degraded": degraded or not success})
            return

        # 多节点：预算内可选 LLM 润色合并
        if success:
            _step(turn_id, "output", "输出（合并结果）", "running")
            if budget.can:
                try:
                    user_msg = f"任务：{text}\n\n各步骤输出：\n{self._format_results(result)}"
                    if plan.get("prompt_md"):
                        user_msg = f"技能方法论：\n{plan['prompt_md']}\n\n{user_msg}"
                    summary = llm_service.complete(
                        AGENT_FINAL_SYSTEM,
                        user_msg,
                        task_type="default",
                    )
                    budget.spend()
                    _set_turn(turn_id, llm_calls=budget.used)
                    _step(turn_id, "output", "输出（LLM 润色）", "done")
                    _set_turn(turn_id, final={"content": summary, "actions": [
                        {"type": "open_workflow", "label": "🔀 查看/编辑工作流",
                         "plan": {k: plan[k] for k in ("nodes", "edges", "title", "description") if k in plan}},
                    ], "degraded": False})
                    return
                except Exception:
                    logger.exception("LLM 润色失败，使用原始结果")
        content = self._format_results(result) or ("任务执行完成" if success else "任务执行失败")
        _set_turn(turn_id, final={"content": content, "actions": [
            {"type": "open_workflow", "label": "🔀 查看/编辑工作流",
             "plan": {k: plan[k] for k in ("nodes", "edges", "title", "description") if k in plan}},
        ], "degraded": degraded or not success})

    def _final_chat(self, turn_id: str, content: str):
        _set_turn(turn_id, status="done",
                  final={"content": content, "actions": [], "degraded": False})

    # ── ⑥ 记忆 ──

    def _memorize(self, turn_id: str, session_id: int, text: str, plan: dict | None = None,
                  success: bool = True):
        turn = get_turn(turn_id) or {}
        final = turn.get("final", {})
        memory_service.add_message(
            session_id, "assistant",
            final.get("content", "")[:2000],
            msg_type="workflow" if plan and not plan.get("single_tool") else "chat",
            payload={"steps": turn.get("steps", []), "actions": final.get("actions", []),
                     "degraded": final.get("degraded", False)},
            llm_calls=turn.get("llm_calls", 0),
        )
        # 成功 plan 写缓存（skill 的 plan 是模板本身，不写入）
        if success and plan and plan.get("nodes") and not plan.get("single_tool") \
                and plan.get("source") != "skill":
            try:
                from backend.services.plan_cache import plan_cache
                plan_cache.add(text, plan)
            except Exception:
                logger.exception("计划缓存写入失败")

    # ── 工具函数 ──

    @staticmethod
    def _parse_json(raw: str):
        cleaned = raw.strip()
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        m = re.search(r'\{[\s\S]*\}', cleaned)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        return None

    @staticmethod
    def _format_results(results: dict) -> str:
        if not results:
            return ""
        lines = []
        for k, v in results.items():
            if k.startswith("__tool_"):
                continue
            if isinstance(v, dict):
                for kk, vv in v.items():
                    if kk in ("error",):
                        lines.append(f"- **{kk}**: {str(vv)[:200]}")
                    elif kk not in ("text",) or len(str(vv)) > 80:
                        lines.append(f"- **{kk}**: {str(vv)[:300]}")
            else:
                lines.append(f"- **{k}**: {str(v)[:300]}")
        return "\n".join(lines)

    @staticmethod
    def _format_single_result(plan: dict, result: dict, success: bool) -> str:
        tool_id = plan.get("tool_id", "")
        label = TOOL_LABELS.get(tool_id, tool_id)
        if not success or result.get("error"):
            return f"⚠️ {label} 执行失败：{str(result.get('error', '未知错误'))[:200]}"
        if not result:
            return f"✅ {label} 执行完成"
        if "result" in result:
            return f"✅ {label} 结果：\n{str(result['result'])[:800]}"
        parts = []
        for k, v in result.items():
            if k in ("error",):
                continue
            if isinstance(v, str) and len(v) > 400:
                v = v[:400] + "…"
            elif isinstance(v, (list, dict)):
                v = json.dumps(v, ensure_ascii=False)[:400]
            parts.append(f"**{k}**: {v}")
        return f"✅ {label} 完成：\n" + "\n".join(parts) if parts else f"✅ {label} 执行完成"


# 全局单例
agent_loop = AgentLoop()
