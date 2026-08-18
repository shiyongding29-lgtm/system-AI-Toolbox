"""
股票预测服务 — 加载 train_stock_predictor.py 训练的 sklearn 模型。

⚠️ 教学示例：线性/逻辑回归无法可靠预测股市，结果仅供参考，不构成投资建议。
- 线性回归 → 预测次日收盘价（朴素基准：明天≈今天）
- 逻辑回归 → 预测次日涨跌方向 + 概率（实测准确率约 40%，不如抛硬币，如实呈现）
"""

import os
from typing import Optional

import numpy as np

from backend.config import config

_bundle = None


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'stock_predictor', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('股票预测模型未训练，请先运行 train_stock_predictor.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    """模型元信息（数据集/指标），供前端展示。"""
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'last_date': b.get('last_date'),
        'last_close': b.get('last_close'),
        'metrics': b.get('metrics', {}),
        'disclaimer': '机器学习教学示例：线性/逻辑回归无法可靠预测股市，不构成投资建议。',
    }


def predict(features: Optional[dict] = None) -> dict:
    """预测次日收盘价与涨跌方向。

    features 可含 open/high/low/close/volume，缺省用最新一天数据（预测「明天」）。
    """
    b = _load()
    feats = features or {}
    last = b['last_row']

    o = float(feats.get('open', last[0]))
    h = float(feats.get('high', last[1]))
    l = float(feats.get('low', last[2]))
    c = float(feats.get('close', last[3]))
    v = float(feats.get('volume', last[4]))
    prev_close = b.get('last_close', c)
    r = (c - prev_close) / prev_close if prev_close else 0.0

    x = np.array([[o, h, l, c, v, r]])
    next_close = float(b['linreg'].predict(x)[0])
    proba = b['logreg'].predict_proba(x)[0]  # [P(下跌), P(上涨)]
    up_p = float(proba[1])
    direction = '上涨' if up_p >= 0.5 else '下跌'

    summary = f"预测次日收盘价 ${next_close:.2f}，涨跌方向：{direction}（上涨概率 {up_p:.0%}）"
    return {
        'result': summary,
        'predicted_close': round(next_close, 2),
        'direction': direction,
        'up_probability': round(up_p, 4),
        'down_probability': round(float(proba[0]), 4),
        'last_close': prev_close,
        'metrics': b.get('metrics', {}),
        'disclaimer': '机器学习教学示例：线性/逻辑回归无法可靠预测股市，不构成投资建议。',
    }
