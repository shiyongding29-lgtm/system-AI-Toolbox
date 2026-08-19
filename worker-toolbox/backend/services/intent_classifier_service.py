"""
本地意图分类器 — 用你训练的 DistilBERT 模型替代 LLM 调用
自动从训练时保存的 labels.txt 读取类别，添加新工具无需改代码
"""
import os
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

from backend.config import config

MODEL_PATH = os.path.join(config.models_dir, 'intent_classifier')

# 自动从 labels.txt 加载类别标签（训练脚本自动生成）
_labels_path = os.path.join(MODEL_PATH, 'labels.txt')
if os.path.exists(_labels_path):
    with open(_labels_path) as f:
        LABELS = [l.strip() for l in f if l.strip()]
else:
    LABELS = ['meeting', 'translation', 'ppt', 'summary', 'todo', 'research',
              'email', 'pomodoro', 'mindmap', 'data', 'spreadsheet', 'weekly_report', 'task_planning']

# 意图 → 前端 tool key 映射
TOOL_MAP = {
    'meeting': 'meeting', 'translation': 'translation', 'ppt': 'ppt',
    'summary': 'summary', 'todo': 'todo', 'research': 'research',
    'email': 'email', 'pomodoro': 'pomodoro', 'mindmap': 'mindmap',
    'data': 'data', 'spreadsheet': 'spreadsheet',
    'weekly_report': 'weekly-report', 'task_planning': 'task-planning',
    'image-analyzer': 'image-analyzer', 'chart-generator': 'chart-generator',
    'doc-compare': 'doc-compare', 'multi-source': 'multi-source', 'rag-qa': 'rag-qa',
    'info-extraction': 'info-extraction',
    'table_generator': 'table-generator',
    'pdf_toolkit': 'pdf-toolkit',
    'sentiment_analyzer': 'sentiment-analyzer',
    'file_converter': 'file-converter',
    'todo_add': 'todo-add',
    'web_scraper': 'web-scraper',
    'qr_generator': 'qr-generator',
    # ML 工具（结构化数值参数，走 Agent 大脑提参）
    'fruit_classifier': 'fruit-classifier',
    'spam_classifier': 'spam-classifier',
    'priority_classifier': 'priority-classifier',
    'delay_risk': 'delay-risk',
    'attrition_risk': 'attrition-risk',
    'anomaly_detector': 'anomaly-detector',
    'stock_predictor': 'stock',
}

_MODEL = None
_TOKENIZER = None
_DEVICE = None


def _load_model():
    global _MODEL, _TOKENIZER, _DEVICE
    if _MODEL is not None:
        return
    _DEVICE = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    _TOKENIZER = DistilBertTokenizer.from_pretrained(MODEL_PATH)
    _MODEL = DistilBertForSequenceClassification.from_pretrained(MODEL_PATH)
    _MODEL.to(_DEVICE)
    _MODEL.eval()
    print(f'✅ 意图分类模型已加载 ({len(LABELS)} 类, 设备: {_DEVICE})')


def predict(text: str) -> dict:
    _load_model()
    inputs = _TOKENIZER(text, return_tensors='pt', truncation=True, padding=True, max_length=64)
    inputs = {k: v.to(_DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = _MODEL(**inputs)
        scores = torch.softmax(outputs.logits, dim=-1)[0]
        pred_id = torch.argmax(scores).item()
    intent = LABELS[pred_id]
    return {
        'intent': intent,
        'confidence': round(scores[pred_id].item(), 4),
        'tool': TOOL_MAP.get(intent, intent),
        'all_scores': {LABELS[i]: round(scores[i].item(), 4) for i in range(len(LABELS))},
    }
