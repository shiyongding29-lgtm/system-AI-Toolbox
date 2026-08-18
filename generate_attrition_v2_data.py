"""
生成 9 特征离职风险数据集（合成，模拟真实 HR 规律）。

特征：
  连续 8 个 —— tenure, salary, raise_pct, performance, overtime_hours,
              months_since_promotion, age, attendance_anomalies
  类别 1 个 —— department（技术部/销售部/市场部/财务部/人事部/运营部）
标签：attrition（0=留任, 1=离职）

刻意注入「非线性交互」离职规律（线性模型学不到，FCN 能学）：
  ① 高绩效 + 长期未晋升 → 强离职信号（人才憋屈悖论）
  ② 高绩效 + 低加薪幅度 → 不公平感离职
  ③ 高加班倦怠 / 考勤异常频繁 → 离职
以及主效应：工龄 U 型、年轻跳槽、部门差异、低薪。

用法：python3 generate_attrition_v2_data.py [N] [输出csv]
"""
import sys

import numpy as np
import pandas as pd

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
OUT = sys.argv[2] if len(sys.argv) > 2 else "attrition_data_v2.csv"

rng = np.random.default_rng(42)

# ── 类别特征：部门（6 个）──
DEPARTMENTS = ["技术部", "销售部", "市场部", "财务部", "人事部", "运营部"]
DEPT_EFFECT = {"技术部": 0.35, "销售部": 0.55, "市场部": 0.10,
               "财务部": -0.20, "人事部": -0.25, "运营部": 0.0}   # 离职倾向 logit 主效应
DEPT_SALARY = {"技术部": 1.3, "销售部": 1.1, "市场部": 1.0,
               "财务部": 1.0, "人事部": 0.9, "运营部": 0.9}        # 薪资系数

department = rng.choice(DEPARTMENTS, N)

# ── 连续特征 ──
age = np.round(rng.uniform(22, 55, N), 0)                                   # 年龄
tenure = np.round(np.clip(age - rng.uniform(20, 32, N), 0, 35), 1)          # 工龄（与年龄相关）
base_salary = 4000 + age * 150 + tenure * 200
salary = np.round([base_salary[i] * DEPT_SALARY[department[i]] * rng.uniform(0.8, 1.2)
                   for i in range(N)], 0)                                   # 薪资
performance = rng.choice([1, 2, 3, 4, 5], N, p=[0.03, 0.12, 0.35, 0.35, 0.15])  # 绩效 1~5
overtime_hours = np.round(np.clip(rng.normal(30, 20, N), 0, 100), 1)        # 加班时长
raise_pct = np.round(np.clip(rng.normal(4, 3, N), 0, 15), 1)                # 最近加薪幅度 %
# 距上次晋升月数：30% 从未晋升（用 120 表示），其余与工龄相关
months_since_promotion = np.where(
    rng.random(N) < 0.30, 120,
    np.round(np.clip(tenure * 12 * rng.uniform(0.2, 1.0, N), 0, 120), 0))
attendance_anomalies = rng.poisson(2, N)                                    # 考勤异常次数

# ── 构建离职 logit（不含全局截距，截距最后按目标离职率校准）──
logit = np.array([DEPT_EFFECT[d] for d in department])                      # 部门主效应
logit += np.where((tenure < 1.5) | (tenure > 12), 0.5, 0.0)                 # 工龄 U 型
logit += np.where(age < 28, 0.4, 0.0)                                       # 年轻跳槽
logit += np.where(overtime_hours > 60, 0.6, 0.0)                            # 加班倦怠
logit += np.where(attendance_anomalies >= 5, 0.8, 0.0)                      # 考勤异常频繁
logit += np.where(attendance_anomalies >= 3, 0.3, 0.0)
logit += np.where(salary < np.median(salary), 0.25, 0.0)                    # 相对低薪

# 关键非线性交互（FCN 的核心价值所在）
logit += np.where((performance >= 4) & (months_since_promotion > 36), 2.0, 0.0)  # 高绩效+长期未晋升
logit += np.where((performance >= 4) & (raise_pct < 2), 1.3, 0.0)                 # 高绩效+低加薪
logit += np.where((performance <= 2) & (attendance_anomalies >= 3), 0.4, 0.0)     # 低绩效+考勤差

logit += -0.02 * (tenure - 5) + 0.01 * (overtime_hours - 30)                # 轻微线性主效应
logit += rng.normal(0, 0.3, N)                                              # 噪声

# ── 截距校准：使平均离职概率 ≈ 22% ──
TARGET = 0.22
bias = np.log(TARGET / (1 - TARGET)) - np.mean(logit)
prob = 1 / (1 + np.exp(-(logit + bias)))
attrition = (rng.random(N) < prob).astype(int)

df = pd.DataFrame({
    "tenure": tenure, "salary": salary, "raise_pct": raise_pct,
    "performance": performance, "overtime_hours": overtime_hours,
    "months_since_promotion": months_since_promotion, "department": department,
    "age": age, "attendance_anomalies": attendance_anomalies, "attrition": attrition,
})
df.to_csv(OUT, index=False, encoding="utf-8")

rate = attrition.mean()
print(f"✅ 已生成 {N} 条数据 → {OUT}")
print(f"   离职率 {rate:.2%} | 离职 {int(attrition.sum())} / 留任 {int(N - attrition.sum())}")
print(f"   部门分布：{dict(zip(*np.unique(department, return_counts=True)))}")
print(f"   交互项命中：高绩效+长期未晋升 {int(((performance >= 4) & (months_since_promotion > 36)).sum())} 条")
