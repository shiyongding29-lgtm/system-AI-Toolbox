"""
FCN 全连接网络 — 员工离职风险预测（Sigmoid 输出离职概率）。

对比基线：
  - FCN（本方案）
  - SVM RBF（现有方案，作为强基线）
  - LogisticRegression（线性，展示非线性交互的价值）

输出：AUC-ROC / PR-AUC / 准确率 / 精确率 / 召回率 / F1，以及低/中/高风险分档。

用法：python3 train_attrition_fcn.py [csv路径]
"""
import sys
import copy
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score, average_precision_score, accuracy_score,
                             precision_score, recall_score, f1_score, confusion_matrix, roc_curve)

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / "attrition_data_v2.csv")
SAVE_DIR = SCRIPT_DIR / "models" / "attrition_fcn"

CONT_FEATURES = ["tenure", "salary", "raise_pct", "performance", "overtime_hours",
                 "months_since_promotion", "age", "attendance_anomalies"]
CAT_FEATURES = ["department"]
TARGET = "attrition"
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# ═══════════════════════════════════════════════════════════════
# ① 数据加载 + 预处理
# ═══════════════════════════════════════════════════════════════
df = pd.read_csv(CSV_PATH, encoding="utf-8")
X_cont = df[CONT_FEATURES].values.astype(np.float32)
X_cat = df[CAT_FEATURES].values
y = df[TARGET].values.astype(np.float32)

scaler = StandardScaler()
encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")

# 按索引分层划分（保证 cont 与 cat 同步）：train 60% / val 20% / test 20%
idx = np.arange(len(y))
idx_tr, idx_te = train_test_split(idx, test_size=0.2, stratify=y, random_state=42)
idx_tr, idx_va = train_test_split(idx_tr, test_size=0.25, stratify=y[idx_tr], random_state=42)

X_cont_tr = scaler.fit_transform(X_cont[idx_tr]).astype(np.float32)
X_cont_va = scaler.transform(X_cont[idx_va]).astype(np.float32)
X_cont_te = scaler.transform(X_cont[idx_te]).astype(np.float32)
X_cat_tr = encoder.fit_transform(X_cat[idx_tr]).astype(np.float32)
X_cat_va = encoder.transform(X_cat[idx_va]).astype(np.float32)
X_cat_te = encoder.transform(X_cat[idx_te]).astype(np.float32)
y_tr, y_va, y_te = y[idx_tr], y[idx_va], y[idx_te]

X_tr = np.hstack([X_cont_tr, X_cat_tr])
X_va = np.hstack([X_cont_va, X_cat_va])
X_te = np.hstack([X_cont_te, X_cat_te])
IN_DIM = X_tr.shape[1]

print(f"数据 {len(y)} 条 | train {len(idx_tr)} / val {len(idx_va)} / test {len(idx_te)} | 输入维度 {IN_DIM}")
print(f"离职率：train {y_tr.mean():.2%} | val {y_va.mean():.2%} | test {y_te.mean():.2%} | 设备 {DEVICE}")

# ═══════════════════════════════════════════════════════════════
# ② FCN 网络定义
# ═══════════════════════════════════════════════════════════════
class AttritionFCN(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64), nn.ReLU(), nn.BatchNorm1d(64), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.ReLU(), nn.BatchNorm1d(32), nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x)  # 输出 logits，交给 BCEWithLogitsLoss


def to_tensor(x):
    return torch.tensor(x, dtype=torch.float32).to(DEVICE)


def train_fcn(X_tr, y_tr, X_va, y_va, in_dim, epochs=300, patience=30):
    torch.manual_seed(42)
    model = AttritionFCN(in_dim).to(DEVICE)
    n_pos = int(y_tr.sum()); n_neg = len(y_tr) - n_pos
    pos_weight = torch.tensor([n_neg / n_pos], dtype=torch.float32).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)

    Xt, yt = to_tensor(X_tr), to_tensor(y_tr).view(-1, 1)
    Xv, yv = to_tensor(X_va), to_tensor(y_va)
    n = len(Xt)
    best_auc, best_state, bad = 0.0, None, 0

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n)
        for i in range(0, n, 128):
            bi = perm[i:i + 128]
            optimizer.zero_grad()
            loss = criterion(model(Xt[bi]), yt[bi])
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_prob = torch.sigmoid(model(Xv)).cpu().numpy().ravel()
        val_auc = roc_auc_score(y_va, val_prob)

        if val_auc > best_auc:
            best_auc, best_state, bad = val_auc, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= patience:
                print(f"  早停 @ epoch {epoch}（val AUC {best_auc:.4f}）")
                break
    model.load_state_dict(best_state)
    return model, best_auc


# ═══════════════════════════════════════════════════════════════
# ③ 训练三个模型
# ═══════════════════════════════════════════════════════════════
print("\n[FCN] 训练中...")
fcn, fcn_val_auc = train_fcn(X_tr, y_tr, X_va, y_va, IN_DIM)

print("[SVM RBF] 训练中...")
svm = SVC(kernel="rbf", C=1.0, gamma="scale", probability=True,
          class_weight="balanced", random_state=42)
svm.fit(X_tr, y_tr)

print("[LogisticRegression] 训练中...")
lr = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)
lr.fit(X_tr, y_tr)

# ═══════════════════════════════════════════════════════════════
# ④ 测试集评估
# ═══════════════════════════════════════════════════════════════
fcn.eval()
with torch.no_grad():
    fcn_prob = torch.sigmoid(fcn(to_tensor(X_te))).cpu().numpy().ravel()
svm_prob = svm.predict_proba(X_te)[:, 1]
lr_prob = lr.predict_proba(X_te)[:, 1]


def report(name, y_true, y_prob):
    auc = roc_auc_score(y_true, y_prob)
    pr_auc = average_precision_score(y_true, y_prob)
    fpr, tpr, thresh = roc_curve(y_true, y_prob)
    best_t = thresh[np.argmax(tpr - fpr)]  # 约登最优阈值（对 class_weight 概率偏移更公平）
    y_pred = (y_prob >= best_t).astype(int)
    low = int((y_prob < 0.3).sum())
    mid = int(((y_prob >= 0.3) & (y_prob < 0.7)).sum())
    high = int((y_prob >= 0.7).sum())
    return {
        "name": name,
        "auc": auc, "pr_auc": pr_auc,
        "acc": accuracy_score(y_true, y_pred),
        "prec": precision_score(y_true, y_pred, zero_division=0),
        "rec": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "low": low, "mid": mid, "high": high,
    }


rows = [report("FCN", y_te, fcn_prob),
        report("SVM-RBF", y_te, svm_prob),
        report("LogReg", y_te, lr_prob)]

print("\n════════════════════════════════ 测试集对比 ════════════════════════════════")
print(f"{'模型':<12}{'AUC':>8}{'PR-AUC':>9}{'准确率':>8}{'精确率':>8}{'召回率':>8}{'F1':>8}")
for r in rows:
    print(f"{r['name']:<12}{r['auc']:>8.4f}{r['pr_auc']:>9.4f}{r['acc']:>8.2%}"
          f"{r['prec']:>8.2%}{r['rec']:>8.2%}{r['f1']:>8.4f}")

print("\n风险分档（低 <0.3 / 中 0.3~0.7 / 高 >0.7）：")
for r in rows:
    print(f"  {r['name']:<12} 低 {r['low']:>4}  中 {r['mid']:>4}  高 {r['high']:>4}")

print("\n[FCN] 混淆矩阵（行=真实, 列=预测 @0.5）：")
print(confusion_matrix(y_te, (fcn_prob >= 0.5).astype(int)))

# ═══════════════════════════════════════════════════════════════
# ⑤ 保存模型
# ═══════════════════════════════════════════════════════════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
torch.save({
    "model_state": fcn.state_dict(),
    "in_dim": IN_DIM,
    "cont_features": CONT_FEATURES,
    "cat_features": CAT_FEATURES,
    "scaler": scaler,
    "encoder": encoder,
    "thresholds": {"low": 0.3, "high": 0.7},
    "metrics": rows[0],
}, SAVE_DIR / "model.pt")
print(f"\n✅ 模型已保存: {SAVE_DIR}/model.pt")
print(f"   FCN val AUC {fcn_val_auc:.4f} | test AUC {rows[0]['auc']:.4f}")
