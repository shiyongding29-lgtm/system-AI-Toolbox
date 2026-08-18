"""
梯度提升树 项目延期风险分类 — sklearn GradientBoostingClassifier

（注：原计划用 XGBoost，但 xgboost 与 PyTorch 在 macOS 上存在 OpenMP
 原生库冲突，同进程加载会段错误。GradientBoostingClassifier 是同算法
 的 sklearn 原生实现，接口一致，无冲突。）

特征：计划进度/人手缺口/需求变更/加班频率/外部依赖/老板临时需求
标签：high / medium / low（延期风险）

数据集：delay_risk_data.csv（基于延期风险规则的合成数据，600 条）
用法：python3 train_delay_risk_classifier.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'delay_risk_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'delay_risk_classifier'

FEATURES = ['plan_progress', 'manpower_shortage', 'req_change',
            'overtime_freq', 'depend_task', 'urgent_boss']
LABEL_MAP = {'low': 0, 'medium': 1, 'high': 2}
REVERSE_MAP = {0: 'low', 1: 'medium', 2: 'high'}

# ═══════════ 读取数据 ═══════════
X, y = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append([int(row[k]) for k in FEATURES])
        y.append(LABEL_MAP[row['risk']])

X = np.array(X)
y = np.array(y)
print(f'加载 {len(X)} 条 | 特征 {len(FEATURES)} 个 | 类别 {list(REVERSE_MAP.values())}')

# ═══════════ 分层划分 ═══════════
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f'训练集 {len(X_tr)} | 测试集 {len(X_te)}')

# ═══════════ 梯度提升树（sklearn，同 XGBoost 算法族）═══════════
model = GradientBoostingClassifier(
    n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42,
)
model.fit(X_tr, y_tr)
y_pred = model.predict(X_te)
acc = accuracy_score(y_te, y_pred)
print(f'\n[梯度提升树] 测试准确率 {acc:.2%}')
print(classification_report(y_te, y_pred, target_names=['低', '中', '高']))

# 特征重要性（XGBoost 核心优势）
importances = model.feature_importances_
order = np.argsort(importances)[::-1]
print('\n特征重要性（哪些因素最影响延期风险）:')
for i in order:
    print(f'  {FEATURES[i]:20} {importances[i]:.4f}')

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'tree': model,
    'feature_names': FEATURES,
    'label_map': LABEL_MAP,
    'reverse_map': REVERSE_MAP,
    'metrics': {'accuracy': round(float(acc), 4)},
    'feature_importances': {FEATURES[i]: round(float(importances[i]), 4) for i in order},
    'data_points': len(X),
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
