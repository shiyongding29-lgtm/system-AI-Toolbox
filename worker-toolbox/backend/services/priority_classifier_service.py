"""
任务优先级分类服务 — 决策树 (Decision Tree)。

特征（类别型，0/1/2 编码）：
- deadline(截止日期): 0宽松 / 1正常 / 2紧急
- impact(影响范围): 0低 / 1中 / 2高
- leader_followup(领导跟进): 0否 / 1是
- workload(工作量): 0小 / 1中 / 2大
标签：high / medium / low（高 / 中 / 低）

决策树的最大价值是可解释——model_info 返回学到的 if-then 规则树。
"""

import os
from typing import Optional

from backend.config import config

FEATURES = ['deadline', 'impact', 'leader_followup', 'workload']

FEATURE_LABELS = {
    'deadline': {'0': '宽松', '1': '正常', '2': '紧急'},
    'impact': {'0': '低', '1': '中', '2': '高'},
    'leader_followup': {'0': '否', '1': '是'},
    'workload': {'0': '小', '1': '中', '2': '大'},
}

PRIORITY_CN = {'high': '高', 'medium': '中', 'low': '低'}

_bundle = None


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'priority_classifier', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('优先级模型未训练，请先运行 train_priority_classifier.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'metrics': b.get('metrics', {}),
        'feature_names': b.get('feature_names'),
        'tree_rules': b.get('tree_rules', ''),
        'feature_labels': FEATURE_LABELS,
    }


def predict(features: Optional[dict] = None) -> dict:
    """判断任务优先级。features 含 deadline/impact/leader_followup/workload（0/1/2 编码）。"""
    b = _load()
    feats = features or {}
    missing = [k for k in FEATURES if k not in feats]
    if missing:
        return {"error": f"缺少特征: {', '.join(missing)}"}

    try:
        x = [[int(feats[k]) for k in FEATURES]]
    except (ValueError, TypeError):
        return {"error": "特征必须是数字（0/1/2 编码）"}

    pred = str(b['tree'].predict(x)[0])
    proba = b['tree'].predict_proba(x)[0]
    probs = {label: round(float(proba[i]), 4) for i, label in enumerate(b['labels'])}
    conf = max(probs.values())

    emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(pred, '⚪')
    return {
        'result': f"{emoji} 优先级：{PRIORITY_CN.get(pred, pred)}（置信度 {conf:.0%}）",
        'priority': pred,
        'priority_cn': PRIORITY_CN.get(pred, pred),
        'confidence': conf,
        'probabilities': probs,
        'disclaimer': '教学示例：基于合成规则数据的决策树模型，仅供学习。',
    }
