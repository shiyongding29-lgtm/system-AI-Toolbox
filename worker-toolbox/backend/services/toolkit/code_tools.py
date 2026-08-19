"""
零 LLM 代码工具：安全计算器 / 日期计算 / 单位换算 / 字数统计 / JSON 格式化。
全部纯 Python 实现，不调用任何大模型。
"""

import ast
import json
import operator
import re
from datetime import date, timedelta

# ═══════════════════════════════════════════════════════════════
# 计算器（AST 白名单安全 eval）
# ═══════════════════════════════════════════════════════════════

_ALLOWED_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                   ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
                   ast.Mod: operator.mod, ast.Pow: operator.pow}
_ALLOWED_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def _safe_eval_node(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_safe_eval_node(node.operand))
    raise ValueError(f"表达式包含不允许的操作: {type(node).__name__}")


def safe_calc(expression: str) -> dict:
    """安全计算四则/幂/括号表达式。非法表达式返回 rejected=True（绝不执行）。"""
    expr = (expression or "").strip().replace("×", "*").replace("÷", "/").replace("^", "**")
    if not expr or len(expr) > 200:
        return {"rejected": True, "error": "表达式为空或过长"}
    if re.search(r'[a-zA-Z_\\[\\]{};]', expr):
        return {"rejected": True, "error": "表达式包含不允许的字符"}
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval_node(tree)
        if isinstance(result, complex):
            return {"rejected": True, "error": "不支持复数"}
        # 美化输出：整数不带小数点
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return {"result": result}
    except ZeroDivisionError:
        return {"rejected": True, "error": "除数不能为 0"}
    except (ValueError, SyntaxError, OverflowError) as e:
        return {"rejected": True, "error": f"无法计算: {str(e)[:100]}"}


# ═══════════════════════════════════════════════════════════════
# 日期计算
# ═══════════════════════════════════════════════════════════════

_WEEKDAY_CN = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _next_weekday_cn(n: int) -> date:
    """下一个星期 n（0=周一...6=周日）。"""
    today = date.today()
    days_ahead = n - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def date_calc(query: str) -> dict:
    """解析中文相对日期：今天/明天/后天/大后天/下周五/下周X/N天后/N周后/N月后。"""
    q = (query or "").strip()
    if not q:
        return {"error": "缺少日期描述"}
    today = date.today()

    def fmt(d: date) -> str:
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"{d.isoformat()}（{weekdays[d.weekday()]}）"

    m = re.search(r'下个?周([一二三四五六日天])', q) or re.search(r'下星期([一二三四五六日天])', q)
    if m:
        d = _next_weekday_cn(_WEEKDAY_CN.get(m.group(1), 0))
        return {"result": fmt(d)}
    m = re.search(r'周([一二三四五六日天])(?:是)?(?:几号|几号)?', q)
    if m and re.search(r'(下|这)', q):
        base = 7 if "下" in q else 0
        d = today + timedelta(days=base + (_WEEKDAY_CN.get(m.group(1), 0) - today.weekday()))
        return {"result": fmt(d)}
    m = re.search(r'(\d+|[一二两三四五六七八九十]+)\s*个?(天|日|周|星期|月)后', q)
    if m:
        num = int(m.group(1)) if m.group(1).isdigit() else _CN_NUM.get(m.group(1), 1)
        unit = m.group(2)
        if unit in ("天", "日"):
            d = today + timedelta(days=num)
        elif unit in ("周", "星期"):
            d = today + timedelta(weeks=num)
        else:
            # 月后：加月份（日期截断到月末）
            total = today.month - 1 + num
            year, month = today.year + total // 12, total % 12 + 1
            import calendar
            day = min(today.day, calendar.monthrange(year, month)[1])
            d = date(year, month, day)
        return {"result": fmt(d)}
    for label, delta in (("大后天", 3), ("后天", 2), ("明天", 1), ("今天", 0), ("昨天", -1), ("前天", -2)):
        if label in q:
            return {"result": fmt(today + timedelta(days=delta))}
    return {"error": f"无法解析日期描述: {q[:50]}"}


# ═══════════════════════════════════════════════════════════════
# 单位换算
# ═══════════════════════════════════════════════════════════════

_LENGTH = {"米": 1, "千米": 1000, "公里": 1000, "厘米": 0.01, "毫米": 0.001,
           "分米": 0.1, "英里": 1609.344, "英尺": 0.3048, "英寸": 0.0254, "码": 0.9144}
_WEIGHT = {"千克": 1, "公斤": 1, "克": 0.001, "毫克": 1e-6, "吨": 1000,
           "斤": 0.5, "两": 0.05, "磅": 0.45359237, "盎司": 0.028349523}
_DATA = {"字节": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4,
         "B": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}

_UNITS = {**_LENGTH, **_WEIGHT, **_DATA,
          "摄氏度": "TEMP", "华氏度": "TEMP", "开尔文": "TEMP"}


def unit_convert(text: str) -> dict:
    """解析「X 单位A 转 单位B」/「X单位A等于多少单位B」。"""
    q = (text or "").strip()
    if not q:
        return {"error": "缺少换算描述"}
    m = re.search(r'(-?[\d.]+)\s*([^\s，。=等转换为0-9]{1,6})\s*(?:转|换|换算|等于|是|=|为|→|->)\s*([^\s，。]{1,6})', q)
    if not m:
        m = re.search(r'(-?[\d.]+)\s*([^\s，。=0-9]{1,6})\s*(?:等于|是多少)\s*多少\s*([^\s，。?？]{1,6})', q)
    if not m:
        return {"error": f"无法解析换算描述: {q[:60]}"}
    value = float(m.group(1))
    src = m.group(2).strip()
    dst = m.group(3).strip()
    dst = re.sub(r'^多少', '', dst).strip()  # 去掉「等于多少英里」里的「多少」前缀

    # 温度特判
    if "温" in src or "温" in dst or (src in ("摄氏度", "华氏度", "开尔文") or dst in ("摄氏度", "华氏度", "开尔文")):
        if src == "摄氏度" and dst == "华氏度":
            return {"result": round(value * 9 / 5 + 32, 2)}
        if src == "华氏度" and dst == "摄氏度":
            return {"result": round((value - 32) * 5 / 9, 2)}
        if src == "摄氏度" and dst == "开尔文":
            return {"result": round(value + 273.15, 2)}
        if src == "开尔文" and dst == "摄氏度":
            return {"result": round(value - 273.15, 2)}
        return {"error": f"不支持的温度换算: {src} → {dst}"}

    # 数据量大小写不敏感
    src_k, dst_k = src.upper(), dst.upper()
    table = {k.upper(): v for k, v in {**_LENGTH, **_WEIGHT, **_DATA}.items()}
    if src_k not in table or dst_k not in table:
        return {"error": f"不认识的单位: {src} 或 {dst}（支持长度/重量/温度/数据量）"}
    result = value * table[src_k] / table[dst_k]
    return {"result": round(result, 6)}


# ═══════════════════════════════════════════════════════════════
# 字数统计
# ═══════════════════════════════════════════════════════════════

def word_count(text: str) -> dict:
    """中英混合字数统计：中文字符数 + 英文单词数 + 总字符数。"""
    t = text or ""
    cn_chars = len(re.findall(r'[一-鿿぀-ヿ]', t))
    en_words = len(re.findall(r'[A-Za-z]+(?:[\'-][A-Za-z]+)*', t))
    total_chars = len(t.replace(" ", "").replace("\n", ""))
    return {
        "result": {
            "中文字符": cn_chars,
            "英文单词": en_words,
            "不含空格总字符": total_chars,
            "含空格总字符": len(t),
        }
    }


# ═══════════════════════════════════════════════════════════════
# JSON 格式化
# ═══════════════════════════════════════════════════════════════

def json_format(text: str) -> dict:
    """格式化或校验 JSON。"""
    t = (text or "").strip()
    if not t:
        return {"error": "缺少 JSON 文本"}
    try:
        parsed = json.loads(t)
        return {"result": json.dumps(parsed, ensure_ascii=False, indent=2)}
    except json.JSONDecodeError as e:
        # 尝试提取其中一段 JSON
        for pat in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
            m = re.search(pat, t)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                    return {"result": json.dumps(parsed, ensure_ascii=False, indent=2)}
                except json.JSONDecodeError:
                    continue
        return {"error": f"不是合法 JSON: {e.msg} (位置 {e.pos})"}
