"""
HR 员工离职风险预测服务 — SVM（支持向量机）。

特征（连续数值）：
- tenure(工龄/年)
- monthly_salary(月薪资/元)
- overtime_hours(月加班时长/小时)
- performance(绩效评分 1~5)
- promotions(晋升次数)
- commute_minutes(通勤时长/分钟)
标签：1=即将离职，0=留任

输出：离职概率 + 风险等级（高/中/低）。
"""

import os
from typing import Optional

from backend.config import config

FEATURES = ['tenure', 'monthly_salary', 'overtime_hours', 'performance', 'promotions', 'commute_minutes']

FEATURE_LABELS = {
    'tenure': '工龄(年)', 'monthly_salary': '月薪资(元)', 'overtime_hours': '月加班时长(小时)',
    'performance': '绩效评分(1~5)', 'promotions': '晋升次数', 'commute_minutes': '通勤时长(分钟)',
}

_bundle = None


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'attrition_classifier', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('离职风险模型未训练，请先运行 train_attrition_classifier.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'metrics': b.get('metrics', {}),
        'feature_names': b.get('feature_names'),
        'feature_labels': FEATURE_LABELS,
    }


def _risk_level(prob: float) -> str:
    if prob >= 0.7:
        return '高'
    if prob >= 0.4:
        return '中'
    return '低'


def predict(features: Optional[dict] = None) -> dict:
    """预测离职风险。features 含 6 个连续特征。"""
    b = _load()
    feats = features or {}
    missing = [k for k in FEATURES if k not in feats]
    if missing:
        return {"error": f"缺少特征: {', '.join(FEATURE_LABELS.get(k, k) for k in missing)}"}

    try:
        x = [[float(feats[k]) for k in FEATURES]]
    except (ValueError, TypeError):
        return {"error": "特征必须是数字"}

    x_scaled = b['scaler'].transform(x)
    proba = b['svm'].predict_proba(x_scaled)[0]  # [P(留任), P(离职)]
    leave_p = float(proba[1])
    level = _risk_level(leave_p)

    emoji = {'高': '🔴', '中': '🟡', '低': '🟢'}[level]
    return {
        'result': f"{emoji} 离职风险：{level}（离职概率 {leave_p:.0%}）",
        'attrition_probability': round(leave_p, 4),
        'stay_probability': round(float(proba[0]), 4),
        'risk_level': level,
        'disclaimer': '教学示例：基于合成数据的 SVM 模型，仅供学习，不构成人事决策依据。',
    }
