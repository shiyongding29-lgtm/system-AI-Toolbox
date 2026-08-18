"""
sklearn 垃圾邮件分类 — 随机森林 (Random Forest) + 手工特征工程

特征：文本长度/单词数/数字/感叹号/美元符号/大写比例 + 25 个垃圾关键词出现次数
标签：ham(正常) / spam(垃圾)

数据集：spam_data.csv（SMS 垃圾短信集合，5571 条）
用法：python3 train_spam_classifier.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'spam_data.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'spam_classifier'

# 复用服务层的特征函数（唯一真相源）
sys.path.insert(0, str(SCRIPT_DIR / 'worker-toolbox'))
from backend.services.spam_classifier_service import extract_features, FEATURE_NAMES, KEYWORDS

# ═══════════ 读取数据 + 特征工程 ═══════════
X, y = [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        X.append(extract_features(row['message']))
        y.append(row['label'])

X = np.array(X)
labels = sorted(set(y))          # ['ham', 'spam']
y_num = np.array([labels.index(v) for v in y])
n_spam = sum(1 for v in y if v == 'spam')
print(f'加载 {len(X)} 条 | 特征 {len(FEATURE_NAMES)} 个 | spam {n_spam} / ham {len(y) - n_spam}')

# ═══════════ 分层划分 ═══════════
X_tr, X_te, y_tr, y_te = train_test_split(
    X, y_num, test_size=0.2, random_state=42, stratify=y_num
)
print(f'训练集 {len(X_tr)} | 测试集 {len(X_te)}')

# ═══════════ 随机森林（不平衡数据用 balanced 权重）═══════════
rf = RandomForestClassifier(n_estimators=100, max_depth=30, class_weight='balanced',
                            random_state=42, n_jobs=-1)
rf.fit(X_tr, y_tr)
y_pred = rf.predict(X_te)

acc = accuracy_score(y_te, y_pred)
p, r, f1, _ = precision_recall_fscore_support(y_te, y_pred, average='binary', pos_label=1)
print(f'\n[随机森林] 准确率 {acc:.2%} | 精确率 {p:.2%} | 召回率 {r:.2%} | F1 {f1:.2%}')
cm = confusion_matrix(y_te, y_pred)
print(f'混淆矩阵 (行=真实, 列=预测):\n{cm}')
print(f'  → 正常被误判垃圾 {cm[0][1]} 条 | 垃圾漏判 {cm[1][0]} 条')

# 特征重要性（Top 10）
importances = rf.feature_importances_
top_idx = np.argsort(importances)[::-1][:10]
print('\nTop 10 特征重要性:')
for i in top_idx:
    print(f'  {FEATURE_NAMES[i]:20} {importances[i]:.4f}')

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'rf': rf,
    'feature_names': FEATURE_NAMES,
    'keywords': KEYWORDS,
    'labels': labels,
    'metrics': {
        'accuracy': round(float(acc), 4), 'precision': round(float(p), 4),
        'recall': round(float(r), 4), 'f1': round(float(f1), 4),
    },
    'top_keywords': [FEATURE_NAMES[i] for i in top_idx],
    'data_points': len(X),
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
