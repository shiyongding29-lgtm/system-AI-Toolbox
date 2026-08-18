"""
HR 员工离职风险预测服务 — FCN 全连接网络（Sigmoid 输出离职概率）。

特征 9 个（连续 8 + 类别 1）：
- tenure(工龄/年)  salary(月薪资/元)  raise_pct(最近加薪幅度%)
- performance(绩效 1~5)  overtime_hours(月加班时长)
- months_since_promotion(距上次晋升月数，从未晋升填 120)
- age(年龄)  attendance_anomalies(考勤异常次数)
- department(部门，6 选 1 类别)

输出：离职概率 0~1 + 风险等级（低 <0.3 / 中 0.3~0.7 / 高 >0.7）。
"""

import os

import numpy as np
import torch
import torch.nn as nn

from backend.config import config

CONT_FEATURES = ["tenure", "salary", "raise_pct", "performance", "overtime_hours",
                 "months_since_promotion", "age", "attendance_anomalies"]

FEATURE_LABELS = {
    "tenure": "工龄(年)", "salary": "月薪资(元)", "raise_pct": "最近加薪幅度(%)",
    "performance": "绩效评分(1~5)", "overtime_hours": "月加班时长(小时)",
    "months_since_promotion": "距上次晋升(月)", "age": "年龄",
    "attendance_anomalies": "考勤异常次数", "department": "部门",
}

DEPARTMENTS = ["技术部", "销售部", "市场部", "财务部", "人事部", "运营部"]


# 网络结构与 train_attrition_fcn.py 保持一致（加载 state_dict 需要同结构）
class AttritionFCN(nn.Module):
    def __init__(self, in_dim):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 64), nn.ReLU(), nn.BatchNorm1d(64), nn.Dropout(0.3),
            nn.Linear(64, 32), nn.ReLU(), nn.BatchNorm1d(32), nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(self, x):
        return self.net(x)  # 输出 logits


_bundle = None
_model = None


def _load():
    global _bundle, _model
    if _bundle is not None:
        return
    path = os.path.join(config.models_dir, "attrition_fcn", "model.pt")
    if not os.path.exists(path):
        raise RuntimeError("离职风险模型未训练，请先运行 train_attrition_fcn.py")
    _bundle = torch.load(path, map_location="cpu", weights_only=False)
    _model = AttritionFCN(_bundle["in_dim"])
    _model.load_state_dict(_bundle["model_state"])
    _model.eval()


def model_info() -> dict:
    _load()
    m = _bundle.get("metrics", {})
    return {
        "data_points": 3000,
        "metrics": {
            "accuracy": m.get("acc", 0), "precision": m.get("prec", 0),
            "recall": m.get("rec", 0), "f1": m.get("f1", 0), "auc": m.get("auc", 0),
        },
        "feature_labels": FEATURE_LABELS,
        "departments": DEPARTMENTS,
        "thresholds": _bundle.get("thresholds", {"low": 0.3, "high": 0.7}),
    }


def _risk_level(prob: float) -> str:
    if prob >= 0.7:
        return "高"
    if prob >= 0.3:
        return "中"
    return "低"


def predict(features: dict | None = None) -> dict:
    """预测离职风险。features 含 8 个连续特征 + department。"""
    _load()
    feats = features or {}
    missing = [k for k in CONT_FEATURES if k not in feats]
    if missing:
        return {"error": f"缺少特征: {', '.join(FEATURE_LABELS.get(k, k) for k in missing)}"}
    dept = (feats.get("department") or "").strip()
    if dept not in DEPARTMENTS:
        return {"error": f"未知部门「{dept}」，可选：{'、'.join(DEPARTMENTS)}"}

    try:
        cont = np.array([[float(feats[k]) for k in CONT_FEATURES]], dtype=np.float32)
    except (ValueError, TypeError):
        return {"error": "特征必须是数字"}

    cont = _bundle["scaler"].transform(cont).astype(np.float32)
    cat = _bundle["encoder"].transform([[dept]]).astype(np.float32)
    x = np.hstack([cont, cat])

    with torch.no_grad():
        prob = float(torch.sigmoid(_model(torch.tensor(x))).item())
    level = _risk_level(prob)
    emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}[level]

    return {
        "result": f"{emoji} 离职风险：{level}（离职概率 {prob:.0%}）",
        "attrition_probability": round(prob, 4),
        "stay_probability": round(1 - prob, 4),
        "risk_level": level,
        "disclaimer": "基于 FCN 全连接网络的离职风险预测，结果仅供 HR 参考，不构成人事决策依据。",
    }
