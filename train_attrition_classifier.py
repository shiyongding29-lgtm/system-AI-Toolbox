"""
SVM 员工离职风险预测 — 二分类

特征：工龄/月薪资/加班时长/绩效/晋升次数/通勤时长（连续数值）
标签：1=即将离职，0=留任

数据集：attrition_data.csv（基于真实离职规律的合成数据，1500 条）
用法：python3 train_attrition_classifier.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'attrition_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'attrition_classifier'

FEATURES = ['tenure', 'monthly_salary', 'overtime_hours', 'performance', 'promotions', 'commute_minutes']

# ═══════════ 读取数据 ═══════════
X, y = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append([float(row[k]) for k in FEATURES])
        y.append(int(row['attrition']))

X = np.array(X)
y = np.array(y)
n_leave = int(sum(y))
print(f'加载 {len(X)} 条 | 离职 {n_leave} / 留任 {len(y) - n_leave}')

# ═══════════ 标准化（SVM 基于距离，必须缩放）═══════════
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 分层划分
X_tr, X_te, y_tr, y_te = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)
print(f'训练集 {len(X_tr)} | 测试集 {len(X_te)}')

# ═══════════ SVM（RBF 核，balanced 处理不平衡，probability 输出概率）═══════════
svm = SVC(kernel='rbf', C=1.0, gamma='scale', probability=True,
          class_weight='balanced', random_state=42)
svm.fit(X_tr, y_tr)
y_pred = svm.predict(X_te)

acc = accuracy_score(y_te, y_pred)
p, r, f1, _ = precision_recall_fscore_support(y_te, y_pred, average='binary', pos_label=1)
print(f'\n[SVM] 准确率 {acc:.2%} | 精确率 {p:.2%} | 召回率 {r:.2%} | F1 {f1:.2%}')
cm = confusion_matrix(y_te, y_pred)
print(f'混淆矩阵 (行=真实, 列=预测):\n{cm}')
print(f'  → 误报离职 {cm[0][1]} 条 | 漏报离职 {cm[1][0]} 条')

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'svm': svm,
    'scaler': scaler,
    'feature_names': FEATURES,
    'metrics': {
        'accuracy': round(float(acc), 4), 'precision': round(float(p), 4),
        'recall': round(float(r), 4), 'f1': round(float(f1), 4),
    },
    'data_points': len(X),
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
