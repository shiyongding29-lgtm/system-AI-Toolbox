"""
sklearn 股票预测器 — 线性回归(预测次日收盘价) + 逻辑回归(预测次日涨跌方向)

⚠️ 教学示例：线性/逻辑回归无法可靠预测股市，本工具仅演示 ML 工作流，不构成投资建议。

数据集：Apple 股票日线 (finance-charts-apple.csv，plotly 官方样例)
用法：python3 train_stock_predictor.py [csv路径]
"""
import sys
import csv
from pathlib import Path

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, classification_report
import joblib

SCRIPT_DIR = Path(__file__).resolve().parent
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else str(SCRIPT_DIR / 'stock_apple.csv')
SAVE_DIR = SCRIPT_DIR / 'models' / 'stock_predictor'

# ═══════════ 读取数据 ═══════════
dates, opens, highs, lows, closes, volumes = [], [], [], [], [], []
with open(CSV_PATH, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        dates.append(row['Date'])
        opens.append(float(row['AAPL.Open']))
        highs.append(float(row['AAPL.High']))
        lows.append(float(row['AAPL.Low']))
        closes.append(float(row['AAPL.Close']))
        volumes.append(float(row['AAPL.Volume']))

n = len(closes)
print(f'加载 {n} 天数据：{dates[0]} → {dates[-1]}')

FEATURES = ['open', 'high', 'low', 'close', 'volume', 'daily_return']
# 动量特征：当日涨跌幅 (close[t] - close[t-1]) / close[t-1]
returns = [0.0] + [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, n)]
X = np.column_stack([opens, highs, lows, closes, volumes, returns])

# ═══════════ 特征/目标构造（用当日特征预测次日）═══════════
X_reg = X[:-1]                              # 当日 OHLCV
y_close = np.array(closes[1:])              # 次日收盘价（线性回归目标）
y_dir = np.array([1 if closes[i + 1] > closes[i] else 0 for i in range(n - 1)])  # 次日涨跌（逻辑回归目标）

# 时序数据：不打乱，前 80% 训练、后 20% 测试（用过去预测未来）
split = int(len(X_reg) * 0.8)
Xr_tr, Xr_te = X_reg[:split], X_reg[split:]
yc_tr, yc_te = y_close[:split], y_close[split:]
yd_tr, yd_te = y_dir[:split], y_dir[split:]
print(f'训练集 {split} 天 | 测试集 {len(Xr_te)} 天（时序切分，未打乱）')

# ═══════════ 模型 1：线性回归 → 次日收盘价 ═══════════
linreg = LinearRegression()
linreg.fit(Xr_tr, yc_tr)
yc_pred = linreg.predict(Xr_te)
mae = mean_absolute_error(yc_te, yc_pred)
r2 = r2_score(yc_te, yc_pred)
print(f'\n[线性回归] 收盘价预测  MAE: ${mae:.2f}  R²: {r2:.4f}')

# ═══════════ 模型 2：逻辑回归 → 次日涨跌方向 ═══════════
# 平衡类别权重：避免退化成全预测单类，输出有意义的涨跌概率
logreg = LogisticRegression(max_iter=1000, class_weight='balanced')
logreg.fit(Xr_tr, yd_tr)
yd_pred = logreg.predict(Xr_te)
acc = accuracy_score(yd_te, yd_pred)
print(f'\n[逻辑回归] 涨跌方向预测  准确率: {acc:.2%}')
print(classification_report(yd_te, yd_pred, target_names=['下跌', '上涨'], zero_division=0))

# ═══════════ 保存 ═══════════
SAVE_DIR.mkdir(parents=True, exist_ok=True)
bundle = {
    'linreg': linreg,
    'logreg': logreg,
    'feature_names': FEATURES,
    'last_row': X[-1].tolist(),       # 最新一天 OHLCV（默认"预测明天"的输入）
    'last_date': dates[-1],
    'last_close': closes[-1],
    'metrics': {
        'mae': round(float(mae), 4), 'r2': round(float(r2), 4),
        'direction_accuracy': round(float(acc), 4),
    },
    'data_points': n,
}
joblib.dump(bundle, SAVE_DIR / 'model.joblib')
print(f'\n✅ 模型已保存: {SAVE_DIR}')
print(f'   最新交易日: {dates[-1]}  收盘价 ${closes[-1]:.2f}')
