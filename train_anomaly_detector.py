"""
K-Means 异常员工识别 — 无监督学习

原理：聚类后，距离「最近簇中心」仍很远的样本 = 行为模式异常（和大多数人不一致），
标出来交给 HR 复核。例如「绩效很高但加班极低」这类组合。

特征：performance(绩效1~5) / overtime_hours(月加班) / tenure(工龄) / monthly_salary(月薪)
异常阈值：训练集「最近中心距离」的 95 分位数

数据集：anomaly_data.csv（3 个正常员工簇 + 注入的异常样本，525 条）
用法：python3 train_anomaly_detector.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'anomaly_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'anomaly_detector'

FEATURES = ['performance', 'overtime_hours', 'tenure', 'monthly_salary']

# ═══════════ 读取数据（is_anomaly 仅用于评估，不参与训练）═══════════
X, is_anomaly = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append([float(row[k]) for k in FEATURES])
        is_anomaly.append(int(row['is_anomaly']))
X = np.array(X)
true_anomaly = np.array(is_anomaly) == 1
print(f'加载 {len(X)} 条 | 注入异常 {true_anomaly.sum()} 条')

# ═══════════ 标准化（K-Means 基于距离，必须缩放）═══════════
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ═══════════ 肘部法则选 k ═══════════
print('\n肘部法则（惯性随 k 变化）:')
for k in range(1, 7):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    print(f'  k={k}  惯性={km.inertia_:.2f}')

# ═══════════ 聚类（k=3，对应 3 个正常员工簇）═══════════
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
kmeans.fit(X_scaled)
labels = kmeans.labels_
print(f'\n簇大小: {np.bincount(labels).tolist()}')

# ═══════════ 异常分数 = 到最近簇中心的距离 ═══════════
dists = np.min(kmeans.transform(X_scaled), axis=1)   # 每个样本到最近中心距离
threshold = float(np.percentile(dists, 95))          # 95 分位数为阈值
print(f'异常阈值（95分位距离）: {threshold:.4f}')

flagged = dists > threshold
caught = int((flagged & true_anomaly).sum())
false_pos = int((flagged & ~true_anomaly).sum())
missed = int((~flagged & true_anomaly).sum())
print(f'\n[评估] 标记 {flagged.sum()} 个异常')
print(f'  捕获注入异常 {caught}/{true_anomaly.sum()} | 漏报 {missed} | 误报 {false_pos}')

# ═══════════ PCA 降维（4 维 → 2 维，用于可视化）═══════════
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)
print(f'\nPCA 2 维解释方差: {pca.explained_variance_ratio_.tolist()}（合计 {pca.explained_variance_ratio_.sum():.2%}）')

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'kmeans': kmeans,
    'scaler': scaler,
    'pca': pca,
    'threshold': threshold,
    'feature_names': FEATURES,
    'n_clusters': 3,
    'x_pca': X_pca.tolist(),            # 训练样本 2D 坐标（散点图背景）
    'train_flags': flagged.tolist(),    # 训练样本异常标记
    'train_labels': labels.tolist(),    # 训练样本簇标签
    'explained_variance': pca.explained_variance_ratio_.tolist(),
    'metrics': {
        'data_points': len(X),
        'anomalies_flagged': int(flagged.sum()),
        'anomalies_caught': caught,
        'anomalies_injected': int(true_anomaly.sum()),
        'false_positives': false_pos,
    },
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
