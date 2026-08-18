"""
异常员工识别服务 — K-Means 无监督离群检测。

输入员工 4 个行为特征，输出：
- anomaly_score：到最近簇中心的距离 / 阈值（>1.0 即为异常）
- is_anomalous：是否异常（交给 HR 复核）
- cluster：所属员工行为簇
"""

import os
from typing import Optional

import numpy as np

from backend.config import config

FEATURES = ['performance', 'overtime_hours', 'tenure', 'monthly_salary']

FEATURE_LABELS = {
    'performance': '绩效评分(1~5)', 'overtime_hours': '月加班时长(小时)',
    'tenure': '工龄(年)', 'monthly_salary': '月薪资(元)',
}

CLUSTER_HINT = {
    0: '（行为模式相近的员工群体）', 1: '（行为模式相近的员工群体）',
    2: '（行为模式相近的员工群体）',
}

_bundle = None


def _load():
    global _bundle
    if _bundle is not None:
        return _bundle
    path = os.path.join(config.models_dir, 'anomaly_detector', 'model.joblib')
    if not os.path.exists(path):
        raise RuntimeError('异常识别模型未训练，请先运行 train_anomaly_detector.py')
    import joblib
    _bundle = joblib.load(path)
    return _bundle


def model_info() -> dict:
    b = _load()
    return {
        'metrics': b.get('metrics', {}),
        'feature_names': b.get('feature_names'),
        'feature_labels': FEATURE_LABELS,
        'n_clusters': b.get('n_clusters'),
        'threshold': round(b.get('threshold', 0), 4),
    }


def predict(features: Optional[dict] = None) -> dict:
    """判断员工是否行为异常。features 含 4 个连续特征。"""
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
    dists = b['kmeans'].transform(x_scaled)[0]     # 到各簇中心距离
    min_dist = float(dists.min())
    cluster = int(b['kmeans'].predict(x_scaled)[0])
    score = min_dist / b['threshold']              # 1.0 = 阈值边界
    is_anomalous = min_dist > b['threshold']

    if is_anomalous:
        result = f"⚠️ 疑似异常员工（异常分数 {score:.2f}，超过阈值）— 建议 HR 复核"
    else:
        result = f"✅ 行为正常（异常分数 {score:.2f}，属第 {cluster + 1} 类员工）"

    return {
        'result': result,
        'is_anomalous': bool(is_anomalous),
        'anomaly_score': round(score, 4),
        'distance': round(min_dist, 4),
        'threshold': round(b['threshold'], 4),
        'cluster': cluster,
        'disclaimer': '教学示例：K-Means 无监督离群检测，仅基于合成数据，不构成人事决策依据。',
    }


def visualize(features: Optional[dict] = None) -> dict:
    """生成散点图：训练样本（PCA 2D）+ 当前员工位置高亮。返回 {image_url, prediction}。"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    b = _load()
    feats = features or {}
    pred = predict(feats)
    if "error" in pred:
        return pred

    try:
        x = [[float(feats[k]) for k in FEATURES]]
    except (ValueError, TypeError):
        return {"error": "特征必须是数字"}

    x_scaled = b['scaler'].transform(x)
    x_pca = b['pca'].transform(x_scaled)[0]

    xp = np.array(b['x_pca'])
    flags = np.array(b['train_flags'], dtype=bool)
    labels = np.array(b['train_labels'])
    colors = ['#3b82f6', '#22c55e', '#8b5cf6']

    fig, ax = plt.subplots(figsize=(7, 5), dpi=110)
    # 正常样本按簇着色
    for c in range(b['n_clusters']):
        mask = (~flags) & (labels == c)
        ax.scatter(xp[mask, 0], xp[mask, 1], c=colors[c], s=14, alpha=0.45, label=f'Cluster {c + 1}')
    # 训练集异常样本
    ax.scatter(xp[flags, 0], xp[flags, 1], c='#ef4444', s=30, marker='x', alpha=0.7, label='Anomalies (training)')
    # 当前员工
    ax.scatter(x_pca[0], x_pca[1], c='#f59e0b', s=220, marker='*', edgecolors='black', linewidths=1.4, label='Current employee', zorder=5)

    ax.set_xlabel('Principal Component 1')
    ax.set_ylabel('Principal Component 2')
    ax.set_title('Employee Behavior Clusters (PCA 2D Projection)', fontsize=12)
    ax.legend(fontsize=8, loc='best')
    ax.grid(alpha=0.2)

    os.makedirs(config.upload_dir, exist_ok=True)
    fname = f"anomaly_{os.urandom(4).hex()}.png"
    path = os.path.join(config.upload_dir, fname)
    plt.savefig(path, bbox_inches='tight', facecolor='white')
    plt.close()

    return {
        'image_url': f"/uploads/{fname}",
        'explained_variance': b.get('explained_variance', []),
        'prediction': pred,
    }
