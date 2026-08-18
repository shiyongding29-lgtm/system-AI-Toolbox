"""
反思模块 — 规则校验优先（0 LLM），异常时按类型重试/降级。

规则清单：
- tool_error         执行器返回 error 字段
- empty_output       期望输出为空
- todo_add_zero      提取到待办却一条都没写入
- chart_file_missing 图表生成后文件缺失
- json_malformed     JSON 类工具输出解析失败
- truncated_output   LLM 输出以 ... 结尾（截断信号）
- weather_not_found  天气城市解析失败
- calc_unsafe        计算器拒绝非法表达式
- invalid_result     非 dict 结果

LLM 反思触发条件：仅当失败节点是 LLM 型工具且规则属于格式类
（json_malformed / truncated_output / empty_output）。纯工具错误 LLM 修不了。
"""

import logging

from backend.routers.tools_registry import TOOLS_BY_ID
from backend.services.llm_service import llm_service
from backend.services.prompt_library import AGENT_REFLECT_SYSTEM

logger = logging.getLogger(__name__)

EXPECTED_OUTPUTS = {t["id"]: t["outputs"] for t in TOOLS_BY_ID.values()}

# JSON 输出类工具（校验输出能否解析）
JSON_TOOLS = {"table_generator", "todo_extraction", "image_analyzer"}

# LLM 可修复的规则（格式类错误）
LLM_REPAIRABLE = {"json_malformed", "truncated_output", "empty_output"}


def _parse_llm_json(raw: str):
    import json
    import re
    cleaned = raw.strip()
    cleaned = re.sub(r"^```\w*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    for pat in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        m = re.search(pat, cleaned)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                continue
    return None


def validate_node(tool_id: str, result) -> list[str]:
    """单节点规则校验，返回命中的规则名列表。"""
    findings = []
    if not isinstance(result, dict):
        return ["invalid_result"]
    if result.get("error"):
        findings.append("tool_error")
        return findings
    if tool_id == "todo_add" and result.get("added_count", 0) == 0:
        findings.append("todo_add_zero")
    if tool_id == "chart_generator" and not result.get("chart_url"):
        findings.append("chart_file_missing")
    if tool_id == "calculator" and result.get("rejected"):
        findings.append("calc_unsafe")
    for out in EXPECTED_OUTPUTS.get(tool_id, []):
        v = result.get(out)
        if isinstance(v, str) and not v.strip():
            findings.append("empty_output")
            break
    for v in result.values():
        if isinstance(v, str) and len(v) > 40 and v.rstrip().endswith("..."):
            findings.append("truncated_output")
            break
    if tool_id in JSON_TOOLS:
        for k, v in result.items():
            if isinstance(v, str) and v.strip() and k not in ("error",):
                if _parse_llm_json(v) is None:
                    findings.append("json_malformed")
                break
    return findings


class Reflector:
    """反思：validate（0 LLM）→ repair（LLM，仅格式类）→ degrade。"""

    def validate_workflow(self, node_results: dict) -> list[dict]:
        """校验工作流各节点，返回 [{node_id, tool, rule, detail}]。"""
        findings = []
        for node_id, result in node_results.items():
            if node_id.startswith("__tool_"):
                continue
            tool = node_results.get(f"__tool_{node_id}", "")
            for rule in validate_node(tool, result):
                findings.append({
                    "node_id": node_id, "tool": tool, "rule": rule,
                    "detail": str(result.get("error", ""))[:100],
                })
        return findings

    def repair(self, findings: list[dict], node_results: dict, user_text: str) -> dict:
        """对格式类错误做一次 LLM 修复（每节点最多 1 次）。

        返回修复后的 node_results；无法修复的保持原样。
        """
        repaired = dict(node_results)
        for f in findings:
            if f["rule"] not in LLM_REPAIRABLE:
                continue
            tool_id = f["tool"]
            if tool_id not in EXPECTED_OUTPUTS or not EXPECTED_OUTPUTS[tool_id]:
                continue
            output_key = EXPECTED_OUTPUTS[tool_id][0]
            bad_output = str(repaired.get(f["node_id"], {}))
            prompt = AGENT_REFLECT_SYSTEM.format(
                tool=tool_id, rule=f["rule"], inputs=user_text[:2000], output=bad_output[:2000],
            )
            try:
                fixed = llm_service.complete(
                    "You are a repair agent. Follow the repair instruction exactly.",
                    prompt, task_type="default",
                )
                repaired[f["node_id"]] = {output_key: fixed.strip()}
                logger.info("反思修复节点 %s(%s): %s", f["node_id"], tool_id, f["rule"])
            except Exception:
                logger.exception("反思修复失败: %s", f["node_id"])
        return repaired


# 全局单例
reflector = Reflector()
