"""
项目延期风险检测服务 — XGBoost 分类器。

特征（类别型，0/1/2 编码）：
- plan_progress(计划进度): 0落后 / 1正常 / 2超前
- manpower_shortage(人手缺口): 0充足 / 1不足
- req_change(需求变更): 0很少变更 / 1经常改需求
- overtime_freq(加班频率): 0几乎不加班 / 1偶尔 / 2天天
- depend_task(外部依赖): 0无 / 1有
- urgent_boss(老板临时插需求): 0没有 / 1有
标签：high / medium / low（延期风险 高/中/低）
"""

import os
from typing import Optional

from backend.config import config

FEATURES = ['plan_progress', 'manpower_shortage', 'req_change',
            'overtime_freq', 'depend_task', 'urgent_boss']

FEATURE_LABELS = {
    'plan_progress': {'0': '落后', '1': '正常', '2': '超前'},
    'manpower_shortage': {'0': '人手充足', '1': '人手不足'},
    'req_change': {'0': '很少变更', '1': '经常改需求'},
    'overtime_freq': {'0': '几乎不加班', '1': '偶尔加班', '2': '天天加班'},
    'depend_task': {'0': '无外部依赖', '1': '有外部依赖'},
    'urgent_boss': {'0': '没有', '1': '有'},
}

RISK_CN = {'high': '高', 'medium': '中', 'low': '低'}
RISK_EMOJI = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}

_bundle = None


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'delay_risk_classifier', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('延期风险模型未训练，请先运行 train_delay_risk_classifier.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'metrics': b.get('metrics', {}),
        'feature_names': b.get('feature_names'),
        'feature_importances': b.get('feature_importances', {}),
        'feature_labels': FEATURE_LABELS,
    }


def predict(features: Optional[dict] = None) -> dict:
    """判断项目延期风险。features 含 6 个特征（0/1/2 编码）。"""
    b = _load()
    feats = features or {}
    missing = [k for k in FEATURES if k not in feats]
    if missing:
        return {"error": f"缺少特征: {', '.join(missing)}"}

    try:
        x = [[int(feats[k]) for k in FEATURES]]
    except (ValueError, TypeError):
        return {"error": "特征必须是数字（0/1/2 编码）"}

    pred_num = int(b['tree'].predict(x)[0])
    pred = b['reverse_map'][pred_num]
    proba = b['tree'].predict_proba(x)[0]
    probs = {b['reverse_map'][i]: round(float(proba[i]), 4) for i in range(len(proba))}
    conf = max(probs.values())

    return {
        'result': f"{RISK_EMOJI.get(pred, '⚪')} 延期风险：{RISK_CN.get(pred, pred)}（置信度 {conf:.0%}）",
        'risk': pred,
        'risk_cn': RISK_CN.get(pred, pred),
        'confidence': conf,
        'probabilities': probs,
        'disclaimer': '教学示例：基于合成规则数据的 XGBoost 模型，仅供学习。',
    }
