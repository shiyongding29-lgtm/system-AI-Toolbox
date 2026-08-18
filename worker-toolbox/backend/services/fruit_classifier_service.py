"""
水果识别服务 — 加载 train_fruit_classifier.py 训练的 K-NN 模型。

特征：mass(质量/克)、width(宽度/厘米)、height(高度/厘米)、color_score(颜色分数 0~1)
标签：apple / mandarin / orange / lemon

教学示例：59 样本的经典玩具数据集，KNN 分类准确率 100%（水果特征分离度高）。
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
    path = os.path.join(config.models_dir, 'fruit_classifier', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('水果识别模型未训练，请先运行 train_fruit_classifier.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'data_points': b.get('data_points'),
        'labels': b.get('labels'),
        'feature_names': b.get('feature_names'),
        'k': b.get('k'),
        'metrics': b.get('metrics', {}),
    }


def predict(features: Optional[dict] = None) -> dict:
    """识别水果。features 须含 mass/width/height/color_score。"""
    b = _load()
    feats = features or {}
    missing = [k for k in b['feature_names'] if k not in feats]
    if missing:
        return {"error": f"缺少特征: {', '.join(missing)}（需提供 mass/width/height/color_score）"}

    try:
        x = np.array([[float(feats[k]) for k in b['feature_names']]])
    except (ValueError, TypeError):
        return {"error": "特征必须是数字"}

    x_scaled = b['scaler'].transform(x)
    pred_idx = int(b['knn'].predict(x_scaled)[0])          # 整数索引 → 映射回标签
    pred = b['labels'][pred_idx]
    proba = b['knn'].predict_proba(x_scaled)[0]

    # 各类别概率（邻居投票占比）
    probs = {label: round(float(proba[i]), 4) for i, label in enumerate(b['labels'])}

    # 最近的 k 个邻居距离（解释「为什么是这个水果」）
    dists, _ = b['knn'].kneighbors(x_scaled)
    avg_dist = round(float(dists[0].mean()), 4)

    fruit_emoji = {'apple': '🍎', 'mandarin': '🍊', 'orange': '🍊', 'lemon': '🍋'}
    return {
        'result': f"识别结果：{fruit_emoji.get(pred, '🍑')} {pred}（置信度 {max(probs.values()):.0%}）",
        'fruit': pred,
        'confidence': max(probs.values()),
        'probabilities': probs,
        'avg_neighbor_distance': avg_dist,
        'k': b.get('k'),
        'disclaimer': '教学示例：基于 59 个样本的 KNN 玩具模型，仅供学习，不代表真实水果识别精度。',
    }
