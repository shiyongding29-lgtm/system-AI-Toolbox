"""
sklearn 任务优先级分类 — 决策树 (Decision Tree)

特征：deadline(截止)/impact(影响)/leader_followup(领导跟进)/workload(工作量)
标签：high / medium / low

数据集：task_priority_data.csv（基于优先级规则的合成数据，500 条）
用法：python3 train_priority_classifier.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'task_priority_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'priority_classifier'

FEATURES = ['deadline', 'impact', 'leader_followup', 'workload']

# ═══════════ 读取数据 ═══════════
X, y = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append([int(row[k]) for k in FEATURES])
        y.append(row['priority'])   # 直接用字符串标签（high/medium/low）

X = np.array(X)
labels = sorted(set(y))
print(f'加载 {len(X)} 条 | 标签 {labels}')

# ═══════════ 分层划分 ═══════════
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f'训练集 {len(X_tr)} | 测试集 {len(X_te)}')

# ═══════════ 决策树（限制深度保证可解释）═══════════
tree = DecisionTreeClassifier(max_depth=5, random_state=42)
tree.fit(X_tr, y_tr)
y_pred = tree.predict(X_te)
acc = accuracy_score(y_te, y_pred)
print(f'\n[决策树] 测试准确率 {acc:.2%}')
print(classification_report(y_te, y_pred))

# 导出 if-then 规则（决策树的核心价值）
rules = export_text(tree, feature_names=FEATURES)
print('\n学到的决策规则（前 20 行）:')
print('\n'.join(rules.split('\n')[:20]))

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'tree': tree,
    'feature_names': FEATURES,
    'labels': labels,
    'metrics': {'accuracy': round(float(acc), 4)},
    'tree_rules': rules,
    'data_points': len(X),
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
