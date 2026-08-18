"""核心代码工具 + 外部数据工具 API（供前端页面直调；Agent 走 EXECUTORS）。"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.toolkit.code_tools import safe_calc, date_calc, unit_convert, word_count, json_format
from backend.services.toolkit.external_api import weather, exchange_rate, stock_quote, get_key_status

router = APIRouter(prefix="/api/tools", tags=["core-tools"])


class TextRequest(BaseModel):
    text: str = ""
    city: str = ""
    base: str = ""
    target: str = ""
    symbol: str = ""


def _ok(data: dict) -> dict:
    if "error" in data:
        return {"code": 400, "msg": data["error"], "data": None}
    return {"code": 0, "msg": "ok", "data": data}


@router.post("/calculator")
def calc(req: TextRequest):
    return _ok(safe_calc(req.text))


@router.post("/date-calc")
def date_calc_api(req: TextRequest):
    return _ok(date_calc(req.text))


@router.post("/unit-convert")
def unit_convert_api(req: TextRequest):
    return _ok(unit_convert(req.text))


@router.post("/word-count")
def word_count_api(req: TextRequest):
    return _ok(word_count(req.text))


@router.post("/json-format")
def json_format_api(req: TextRequest):
    return _ok(json_format(req.text))


@router.post("/weather")
def weather_api(req: TextRequest):
    return _ok(weather(req.city or req.text))


@router.post("/exchange-rate")
def exchange_rate_api(req: TextRequest):
    return _ok(exchange_rate(req.base or req.text, req.target or ""))


@router.post("/stock")
def stock_api(req: TextRequest):
    return _ok(stock_quote(req.symbol or req.text))


class StockPredictRequest(BaseModel):
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None


@router.post("/stock-predict")
def stock_predict_api(req: StockPredictRequest):
    """sklearn 股票预测（线性回归收盘价 + 逻辑回归涨跌方向）。"""
    from backend.services.stock_predictor_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        return {"code": 0, "msg": "ok", "data": predict(feats)}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/stock-predict/info")
def stock_predict_info():
    """股票预测模型元信息（数据集/指标）。"""
    from backend.services.stock_predictor_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


class FruitClassifyRequest(BaseModel):
    mass: float | None = None
    width: float | None = None
    height: float | None = None
    color_score: float | None = None


@router.post("/fruit-classify")
def fruit_classify_api(req: FruitClassifyRequest):
    """KNN 水果识别。"""
    from backend.services.fruit_classifier_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = predict(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/fruit-classify/info")
def fruit_classify_info():
    """水果识别模型元信息。"""
    from backend.services.fruit_classifier_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.post("/spam-classify")
def spam_classify_api(req: TextRequest):
    """随机森林垃圾邮件分类。"""
    from backend.services.spam_classifier_service import predict
    try:
        result = predict(req.text)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/spam-classify/info")
def spam_classify_info():
    """垃圾邮件模型元信息。"""
    from backend.services.spam_classifier_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


class PriorityClassifyRequest(BaseModel):
    deadline: int | None = None
    impact: int | None = None
    leader_followup: int | None = None
    workload: int | None = None


@router.post("/priority-classify")
def priority_classify_api(req: PriorityClassifyRequest):
    """决策树任务优先级判断。"""
    from backend.services.priority_classifier_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = predict(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/priority-classify/info")
def priority_classify_info():
    """优先级模型元信息（含学到的决策规则）。"""
    from backend.services.priority_classifier_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


class DelayRiskRequest(BaseModel):
    plan_progress: int | None = None
    manpower_shortage: int | None = None
    req_change: int | None = None
    overtime_freq: int | None = None
    depend_task: int | None = None
    urgent_boss: int | None = None


@router.post("/delay-risk")
def delay_risk_api(req: DelayRiskRequest):
    """XGBoost 项目延期风险检测。"""
    from backend.services.delay_risk_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = predict(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/delay-risk/info")
def delay_risk_info():
    """延期风险模型元信息（含特征重要性）。"""
    from backend.services.delay_risk_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


class AttritionRequest(BaseModel):
    tenure: float | None = None
    salary: float | None = None
    raise_pct: float | None = None
    performance: float | None = None
    overtime_hours: float | None = None
    months_since_promotion: float | None = None
    department: str | None = None
    age: float | None = None
    attendance_anomalies: float | None = None


@router.post("/attrition-risk")
def attrition_risk_api(req: AttritionRequest):
    """FCN 员工离职风险预测。"""
    from backend.services.attrition_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = predict(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/attrition-risk/info")
def attrition_risk_info():
    """离职风险模型元信息。"""
    from backend.services.attrition_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


class AnomalyRequest(BaseModel):
    performance: float | None = None
    overtime_hours: float | None = None
    tenure: float | None = None
    monthly_salary: float | None = None


@router.post("/anomaly-detect")
def anomaly_detect_api(req: AnomalyRequest):
    """K-Means 异常员工识别。"""
    from backend.services.anomaly_service import predict
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = predict(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.post("/anomaly-detect/viz")
def anomaly_detect_viz(req: AnomalyRequest):
    """异常识别 + PCA 散点图可视化（当前员工位置高亮）。"""
    from backend.services.anomaly_service import visualize
    feats = {k: v for k, v in req.model_dump().items() if v is not None}
    try:
        result = visualize(feats)
        if "error" in result:
            return {"code": 400, "msg": result["error"], "data": None}
        return {"code": 0, "msg": "ok", "data": result}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/anomaly-detect/info")
def anomaly_detect_info():
    """异常识别模型元信息。"""
    from backend.services.anomaly_service import model_info
    try:
        return {"code": 0, "msg": "ok", "data": model_info()}
    except RuntimeError as e:
        return {"code": 503, "msg": str(e), "data": None}


@router.get("/keys-status")
def keys_status():
    return {"code": 0, "msg": "ok", "data": get_key_status()}
