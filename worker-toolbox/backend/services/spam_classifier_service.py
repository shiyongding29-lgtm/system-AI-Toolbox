"""
垃圾邮件分类服务 — 随机森林 + 手工特征工程。

特征（从原始文本提取）：
- 文本长度 / 单词数 / 数字个数 / 感叹号个数 / 美元符号个数 / 大写比例
- 垃圾关键词出现次数（free/win/prize/cash/urgent/... 共 25 个）

特征函数是训练与推理共用的唯一真相源（训练脚本也 import 这里，避免漂移）。
"""

import os
from typing import Optional

from backend.config import config

# 经典垃圾短信关键词（小写匹配）
KEYWORDS = [
    'free', 'win', 'winner', 'prize', 'cash', 'money', 'urgent', 'call',
    'now', 'click', 'offer', 'guaranteed', 'credit', 'congratulations',
    'claim', 'discount', 'buy', 'reply', 'stop', 'www', 'http', 'text',
    'mobile', 'won', 'award', 'bonus', 'exclusive', 'limited',
]

FEATURE_NAMES = ['length', 'word_count', 'digit_count', 'exclamation_count',
                 'dollar_count', 'capital_ratio'] + KEYWORDS

_bundle = None


def extract_features(text: str) -> list[float]:
    """从原始文本提取特征向量（训练/推理共用）。"""
    t = text or ''
    lower = t.lower()
    feats = [
        float(len(t)),                            # 文本长度
        float(len(t.split())),                    # 单词数
        float(sum(c.isdigit() for c in t)),       # 数字个数
        float(t.count('!')),                      # 感叹号个数
        float(t.count('$')),                      # 美元符号个数
    ]
    letters = sum(c.isalpha() for c in t)
    caps = sum(c.isupper() for c in t)
    feats.append(caps / letters if letters else 0.0)  # 大写比例
    for kw in KEYWORDS:
        feats.append(float(lower.count(kw)))      # 关键词出现次数
    return feats


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'spam_classifier', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('垃圾邮件模型未训练，请先运行 train_spam_classifier.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'metrics': b.get('metrics', {}),
        'feature_names': b.get('feature_names'),
        'top_keywords': b.get('top_keywords', []),
    }


def predict(text: str) -> dict:
    """判断文本是否垃圾邮件。返回 {result, label, spam_probability, keywords_hit}。"""
    b = _load()
    if not (text or '').strip():
        return {"error": "请输入要判断的文本"}
    x = [extract_features(text)]
    proba = b['rf'].predict_proba(x)[0]  # [P(ham), P(spam)]（按训练时类别顺序）
    # 类别顺序：labels 里 ham=0, spam=1（train 脚本保证）
    spam_p = float(proba[1]) if b['labels'][1] == 'spam' else float(proba[0])
    label = 'spam' if spam_p >= 0.5 else 'ham'

    # 命中的垃圾关键词（用于解释判断）
    lower = text.lower()
    hit = [kw for kw in b.get('keywords', []) if kw in lower][:8]

    emoji = '🚫' if label == 'spam' else '✅'
    result = f"{emoji} {'垃圾邮件' if label == 'spam' else '正常邮件'}（垃圾概率 {spam_p:.0%}）"
    return {
        'result': result,
        'label': label,
        'spam_probability': round(spam_p, 4),
        'keywords_hit': hit,
        'disclaimer': '教学示例：基于 SMS 垃圾短信数据集的随机森林模型，仅供学习。',
    }
