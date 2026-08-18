"""
意图路由 — AI Assistant 快路径（本地模型 + 正则，零 LLM）。

被 /api/ai/parse-intent 和 AgentLoop 双复用。
- keyword_route: 新工具关键词直达（阶段5填充）
- route_multi_workflow: multi-tool 模型 ≥0.7 → LLM 生成工作流预览（现有行为）
- route_single: 单意图模型 ≥0.6 + 正则提取参数 → 跳转工具
"""

import re
import logging
from datetime import date, timedelta

from backend.services.multitool_classifier_service import predict_multi
from backend.services.intent_classifier_service import predict as local_predict

logger = logging.getLogger(__name__)


def keyword_route(text: str) -> dict | None:
    """新工具关键词直达（0 LLM）。返回 parse-intent 同构 dict 或 None。"""
    t = (text or "").strip()
    if not t:
        return None

    # 计算器：明确的计算意图 + 含运算符的数字表达式
    if re.search(r'^(帮我|请)?(算|计算)(一下|算|:)?', t) and re.search(r'\d', t) and re.search(r'[+\-*/×÷^]', t):
        expr = re.sub(r'^(帮我|请)?(算|计算)(一下|算|:)?\s*', '', t).rstrip('？?。！!')
        if expr:
            return {"tool": "calculator", "params": {"text": expr}, "reply": f"🧮 帮你计算 {expr}", "source": "keyword"}

    # 日期计算（排除待办提醒类）
    if re.search(r'(今天|明天|后天|大后天|昨天|前天|下周|几号|星期几|周几|天后|月后)', t) \
            and not re.search(r'(提醒|待办|todo|会议|deadline|截止|交|提交)', t, re.I):
        if re.search(r'(星期几|周几|几号|什么日子|哪天|星期|日期)', t) or \
                re.search(r'^(今天|明天|后天|大后天|昨天|前天|下周)', t):
            return {"tool": "date_calc", "params": {"text": t}, "reply": "📅 帮你算日期", "source": "keyword"}

    # 天气
    if re.search(r'(天气|气温|温度|下雨)', t):
        m = re.search(r'([一-鿿]{2,12}?)(?:的)?(?:天气|气温|温度|下雨)', t)
        city = m.group(1) if m else t[:12]
        city = re.sub(r'(今天|明天|现在|目前|今明)$', '', city) or "北京"
        return {"tool": "weather", "params": {"text": city}, "reply": f"🌤️ 帮你查{city}天气", "source": "keyword"}

    # 汇率
    if re.search(r'(汇率|兑换|换算成|兑)', t) and re.search(r'([A-Za-z]{3}|美元|人民币|欧元|日元|英镑|港币|韩元|澳元|加元|卢布)', t):
        return {"tool": "exchange_rate", "params": {"text": t}, "reply": "💱 帮你查汇率", "source": "keyword"}

    # 异常员工识别
    if re.search(r'(异常|离群|反常).{0,4}(员工|行为|样本)|识别.{0,2}异常|异常检测', t):
        return {"tool": "anomaly_detector", "params": {"text": t}, "reply": "🔍 帮你识别异常员工", "source": "keyword"}

    # 离职风险预测
    if re.search(r'(离职|跳槽|流失).{0,4}(风险|预测|概率)|员工.{0,4}(会不会|是否).{0,2}离职', t):
        return {"tool": "attrition_risk", "params": {"text": t}, "reply": "👋 帮你预测员工离职风险", "source": "keyword"}

    # 延期风险检测
    if re.search(r'(延期|拖延).{0,4}(风险|检测|预测|评估)|(项目|任務).{0,4}(会|会不会|是否).{0,2}延期', t):
        return {"tool": "delay_risk", "params": {"text": t}, "reply": "⏰ 帮你评估项目延期风险", "source": "keyword"}

    # 任务优先级判断
    if re.search(r'(任务|事项).{0,4}(优先级|优先)|(优先级|优先).{0,4}(判断|排序|评估)', t):
        return {"tool": "priority_classifier", "params": {"text": t}, "reply": "🎯 帮你判断任务优先级", "source": "keyword"}

    # 垃圾邮件检测
    if re.search(r'(判断|检测|识别|是不是).{0,4}(垃圾邮件|垃圾短信|骚扰)', t) or re.search(r'(垃圾邮件|垃圾短信).{0,4}(判断|检测|识别)', t):
        return {"tool": "spam_classifier", "params": {"text": t}, "reply": "🚫 帮你检测垃圾邮件", "source": "keyword"}

    # 水果识别
    if re.search(r'(识别|这是什么|分类).{0,4}(水果)', t) or re.search(r'(水果).{0,4}(识别|分类)', t):
        return {"tool": "fruit_classifier", "params": {"text": t}, "reply": "🍎 帮你识别水果", "source": "keyword"}

    # 股票预测（放在股价查询之前，避免「预测股价」被 stock_quote 拦截）
    if re.search(r'(预测|预估).{0,4}(股价|股票|涨跌|明天|次日)', t) or re.search(r'(明天|次日).{0,3}(涨|跌)', t):
        return {"tool": "stock_predictor", "params": {"text": t}, "reply": "📉 帮你预测股票走势", "source": "keyword"}

    # 股价
    if re.search(r'(股价|股票|行情|市值|美股|港股)', t):
        m = re.search(r'([一-鿿]{1,10}?)(?:的)?(?:股价|股票|行情)', t)
        symbol = m.group(1) if m else t[:10]
        return {"tool": "stock_quote", "params": {"text": symbol}, "reply": f"📈 帮你查{symbol}股价", "source": "keyword"}

    # 字数统计
    if re.search(r'(字数|多少个字|多少字|word\s*count|统计字数)', t, re.I):
        return {"tool": "word_counter", "params": {"text": t}, "reply": "🔢 帮你统计字数", "source": "keyword"}

    # JSON 格式化
    if re.search(r'(json|JSON)', t) and re.search(r'(格式化|美化|校验|format|validate|缩进)', t):
        return {"tool": "json_formatter", "params": {"text": t}, "reply": "🧾 帮你格式化 JSON", "source": "keyword"}

    # 单位换算
    if re.search(r'\d+(\.\d+)?\s*(米|千米|公里|厘米|毫米|分米|英尺|英寸|英里|千克|公斤|克|毫克|吨|斤|两|磅|MB|GB|KB|TB|摄氏度|华氏度|字节)', t):
        return {"tool": "unit_converter", "params": {"text": t}, "reply": "⚖️ 帮你换算单位", "source": "keyword"}

    return None


# 纯聊天/问候语判断（0 LLM）— 单意图模型容易把问候误判为 todo 等工具
_CHAT_PATTERNS = [
    re.compile(r'^(你好|您好|嗨|哈喽|hello|hi|hey|在吗|在不在|早上好|晚上好|下午好|谢谢|感谢|再见|拜拜)[\s!！。.~～]*$', re.I),
    re.compile(r'^(介绍一下你自己|你是谁|你能做什么|你有什么功能|你会什么|你是谁呀|你是谁啊)[\s?？。.!！]*$'),
]


def is_chat_like(text: str) -> bool:
    """纯问候/寒暄/自我介绍类文本，不应走工具快路径。"""
    t = (text or "").strip()
    if len(t) > 30:
        return False
    return any(p.match(t) for p in _CHAT_PATTERNS)


# 上游 output 已覆盖的功能 → 不需要再调这些 tool
REDUNDANT_MAP = {
    'meeting_recorder.summary': ['document_summary'],
    'document_summary.summary': ['document_summary'],
    'meeting_recorder.transcript': [],
}


def _deduplicate_workflow(plan: dict) -> dict:
    """去掉被上游 output 覆盖的重复 tool。"""
    nodes = plan.get('nodes', [])
    edges = plan.get('edges', [])

    # 收集上游覆盖的 output
    covered = set()
    for e in edges:
        up = e.get('from', '')
        out = e.get('fromOutput', '')
        key = f'{up}.{out}'
        for dup_tool in REDUNDANT_MAP.get(key, []):
            covered.add(dup_tool)

    # 移除被覆盖的节点和边
    if covered:
        removed_ids = set()
        for n in nodes:
            if n.get('tool') in covered:
                removed_ids.add(n['id'])
        plan['nodes'] = [n for n in nodes if n['id'] not in removed_ids]
        plan['edges'] = [e for e in edges if e['to'] not in removed_ids and e['from'] not in removed_ids]

    return plan


def is_multi_step(text: str) -> bool:
    """multi-tool 模型判定是否多步骤（0 LLM），供路由决策。"""
    try:
        mt_result = predict_multi(text)
        return bool(mt_result['is_multi'] and mt_result['confidence'] >= 0.7)
    except Exception:
        logger.exception("multi-tool 检测失败")
        return False


def route_multi_workflow(text: str) -> dict | None:
    """multi-tool 模型判定为多步骤 → 生成工作流预览（缓存优先，0/1 次 LLM）。失败返回 None。"""
    try:
        if is_multi_step(text):
            try:
                from backend.routers.workflow_engine import plan_workflow_cached
                plan = plan_workflow_cached(text)
                if 'error' not in plan:
                    plan = _deduplicate_workflow(plan)
                    reply = f'已生成工作流: {plan.get("title", "")}'
                    questions = plan.get('questions', [])
                    if questions:
                        reply += '\n\n' + '\n'.join(f'❓ {q}' for q in questions)
                    return {
                        "type": "workflow",
                        "plan": plan,
                        "reply": reply,
                        "questions": questions,
                        "source": plan.get("source", "local_model"),
                    }
            except Exception:
                logger.exception("多步骤工作流生成失败，回退到单工具分类")
    except Exception:
        logger.exception("multi-tool 检测失败")
    return None


def route_single(text: str) -> dict | None:
    """单意图分类（本地模型）+ 正则提取参数。低信心返回 None。"""
    today = date.today()
    try:
        local_result = local_predict(text)
    except Exception:
        logger.exception("本地意图分类失败")
        return None

    if local_result['confidence'] < 0.6:
        return None

    intent = local_result['intent']
    tool = local_result['tool']

    # 聊天类（训练数据含 chat 类）不跳工具，交给 Agent 大脑
    if intent == 'chat':
        return None

    # ── 正则提取参数（不依赖 LLM，瞬间完成）──
    params = {}
    cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
              '两': 2, '半': 0.5, '十五': 15, '二十': 20, '二十五': 25, '三十': 30, '三十五': 35,
              '四十': 40, '四十五': 45, '五十': 50, '五十五': 55, '六十': 60}
    pomo_m = re.search(r'(\d+|[一二三四五六七八九十两][十]?[一二三四五六七八九]?)\s*(分钟|分|min)', text, re.I)
    if pomo_m:
        try:
            params['work'] = int(pomo_m.group(1))
        except ValueError:
            params['work'] = cn_num.get(pomo_m.group(1), 25)

    ppt_m = re.search(r'(\d+|[一二三四五六七八九十两][十]?)\s*(页|张|slides?|pages?)', text, re.I)
    if ppt_m:
        try:
            params['slides'] = int(ppt_m.group(1))
        except ValueError:
            params['slides'] = cn_num.get(ppt_m.group(1), 12)
    ppt_s = re.search(r'(\S{1,6})(?:风|风格|style)', text)
    if ppt_s:
        params['style'] = ppt_s.group(1) + '风'

    deadline = ''
    if re.search(r'后天', text):
        d = today + timedelta(days=2)
        deadline = d.isoformat()
    elif re.search(r'明天', text):
        d = today + timedelta(days=1)
        deadline = d.isoformat()
    elif re.search(r'今天', text):
        deadline = today.isoformat()
    if deadline:
        params['deadline'] = deadline
        task = re.sub(r'提醒我|记得|别忘了|帮我记|帮我记录|明天|后天|今天', '', text).strip().lstrip('：:，,。.').strip() or text
        params['task'] = task

    reply_map = {
        'meeting': '帮你打开会议记录', 'translation': '帮你打开翻译', 'ppt': '帮你生成PPT',
        'summary': '帮你总结文档', 'todo': '帮你添加待办', 'research': '帮你调研',
        'email': '帮你写邮件', 'pomodoro': f'帮你设置{params.get("work", 25)}分钟番茄钟',
        'mindmap': '帮你生成思维导图', 'data': '帮你分析数据',
        'spreadsheet': '帮你打开智能表格', 'weekly_report': '帮你生成周报',
        'task_planning': '帮你规划任务', 'image-analyzer': '帮你分析图片',
        'chart-generator': '帮你生成图表', 'doc-compare': '帮你对比文档',
        'multi-source': '帮你多源阅读', 'rag-qa': '帮你查询知识库', 'info-extraction': '帮你提取信息',
        'table_generator': '帮你生成表格', 'pdf_toolkit': '帮你处理PDF',
        'sentiment_analyzer': '帮你分析情感',
        'file_converter': '帮你转换文件格式', 'todo_add': '帮你添加待办',
        'web_scraper': '帮你抓取网页', 'qr_generator': '帮你生成QR码',
        'calculator': '帮你计算', 'date_calc': '帮你算日期',
        'unit_converter': '帮你换算单位', 'word_counter': '帮你统计字数',
        'json_formatter': '帮你格式化JSON', 'weather': '帮你查天气',
        'exchange_rate': '帮你查汇率', 'stock_quote': '帮你查股价',
    }

    return {
        "tool": tool, "params": params,
        "reply": reply_map.get(intent, f'→ {intent}'),
        "source": "local_model",
    }


def fast_route(text: str) -> dict | None:
    """完整快路径：多步骤 → 单意图。未命中返回 None（调用方走 LLM 兜底）。"""
    return route_multi_workflow(text) or route_single(text)
