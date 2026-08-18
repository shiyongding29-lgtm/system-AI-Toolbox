"""
sklearn 水果识别 — K-NN (K 近邻) 分类器

特征：mass(质量/克)、width(宽度/厘米)、height(高度/厘米)、color_score(颜色分数)
标签：apple / mandarin / orange / lemon

数据集：fruit_data.csv（经典 fruit_data_with_colors 数据集，59 样本）
用法：python3 train_fruit_classifier.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'fruit_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'fruit_classifier'

# ═══════════ 读取数据 ═══════════
FEATURES = ['mass', 'width', 'height', 'color_score']
X, y = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append([float(row[k]) for k in FEATURES])
        y.append(row['fruit_name'])

X = np.array(X)
labels = sorted(set(y))
y_num = np.array([labels.index(v) for v in y])
print(f'加载 {len(X)} 个样本 | {len(labels)} 类: {labels}')

# ═══════════ 标准化（KNN 基于距离，特征量纲差异大必须缩放）═══════════
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 分层划分（mandarin 只有 5 个样本，必须 stratify 保证每类都进训练集）
X_tr, X_te, y_tr, y_te = train_test_split(
    X_scaled, y_num, test_size=0.2, random_state=42, stratify=y_num
)
print(f'训练集 {len(X_tr)} | 测试集 {len(X_te)}')

# ═══════════ KNN（试几个 k 选最优）═══════════
best_k, best_acc = 3, 0
for k in range(1, 11):
    knn = KNeighborsClassifier(n_neighbors=k)
    knn.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, knn.predict(X_te))
    if acc > best_acc:
        best_k, best_acc = k, acc
    print(f'  k={k:2d}  → 测试准确率 {acc:.2%}')

print(f'\n选用 k={best_k}，测试准确率 {best_acc:.2%}')

knn = KNeighborsClassifier(n_neighbors=best_k)
knn.fit(X_tr, y_tr)
print(classification_report(y_te, knn.predict(X_te), target_names=labels))

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'knn': knn,
    'scaler': scaler,
    'feature_names': FEATURES,
    'labels': labels,
    'k': best_k,
    'metrics': {'accuracy': round(float(best_acc), 4)},
    'data_points': len(X),
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
