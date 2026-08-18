"""AI 意图解析 API — 快路径(本地模型) + LLM 兜底。兼容接口，Agent 主入口在 /api/agent/chat。"""
from fastapi import APIRouter, Request
from backend.services.llm_service import llm_service, LLMError
from backend.services import intent_router

router = APIRouter(prefix="/api/ai", tags=["ai"])

INTENT_SYSTEM_PROMPT = """You are an intent classifier for a productivity toolbox app. Given the user's natural language input, analyze what tool they want and return a JSON object.

Available tools and their params:
- "todo": create a todo item. Params: {{ task: string, deadline: string (YYYY-MM-DD or empty string), owner: string or empty string }}
  Example: "set timer 30 min" → {{"tool":"pomodoro","params":{{"work":30}}, "reply":"30 minute pomodoro timer set 🍅"}}
- "pomodoro": start a pomodoro timer. Params: {{ work: number (minutes, default 25) }}
- "email": write an email or document. Params: {{ to: string or empty string, hint: string, mode: "email"|"notice"|"report"|"official" }}
- "translation": translate or rewrite text. Params: {{ text: string, mode: "translate_zh_en"|"translate_en_zh"|"polish"|"rewrite"|"expand"|"summarize" }}
- "research": deep web research. Params: {{ topic: string }}
- "ppt": generate PPT outline. Params: {{ slides: number or 0, style: string or empty string }}
- "summary": document summary. Params: {{}}
- "mindmap": mind map. Params: {{}}
- "data": data analysis. Params: {{}}
- "spreadsheet": spreadsheet. Params: {{}}
- "meeting": meeting recorder. Params: {{}}
- "weekly-report": weekly report. Params: {{ auto: true or false }}
- "task-planning": task planning. Params: {{}}
- "none": no tool matched. Params: {{}}

Today date: {today}. Tomorrow: {tomorrow}. Day after: {day_after}. Use these to resolve relative dates.

Return ONLY valid JSON, no markdown, no explanation:
{{"tool":"...","params":{{...}},"reply":"..."}}"""


import json
import logging
import re
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def _next_weekday(n: int):
    today = date.today()
    days_ahead = n - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).isoformat()


@router.post("/parse-intent")
def parse_intent(req: dict):
    text = req.get("text", "")
    if not text:
        return {"code": 400, "msg": "Missing text", "data": None}

    # ── 快路径：本地模型系列（multi-tool + 意图分类 + 正则，0 LLM）──
    fast = intent_router.fast_route(text)
    if fast:
        return {"code": 0, "msg": "ok", "data": fast}

    # ── 回退：用 LLM 解析 ──
    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()
    day_after = (today + timedelta(days=2)).isoformat()

    context = INTENT_SYSTEM_PROMPT.format(
        today=today.isoformat(), tomorrow=tomorrow, day_after=day_after
    )

    try:
        raw = llm_service.complete(context, text, task_type="default")
    except LLMError as e:
        return {"code": 503, "msg": e.message, "data": None}

    # Parse JSON from LLM response
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find JSON anywhere
        m = re.search(r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"params"\s*:\s*\{[^}]*\}\s*,\s*"reply"\s*:\s*"[^"]*"\s*\}', raw, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {"tool": "none", "params": {}, "reply": "不太确定你要做什么，能再说一遍吗？"}
        else:
            parsed = {"tool": "none", "params": {}, "reply": "不太确定你要做什么，能再说一遍吗？"}

    tool = parsed.get("tool", "none")
    params = parsed.get("params", {})
    reply = parsed.get("reply", "")

    return {"code": 0, "msg": "ok", "data": {"tool": tool, "params": params, "reply": reply}}
