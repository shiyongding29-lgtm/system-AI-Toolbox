"""
外部数据 API 工具：天气（open-meteo 免 key）/ 汇率（open.er-api.com 免 key）/ 股价（需 key）。

key 配置：环境变量优先，其次 backend/data/agent_settings.json。
无 key 时优雅降级，返回带特殊错误码的结果（Agent 输出层识别并引导配置）。
"""

import json
import os
import threading

import httpx

from backend.config import config

SETTINGS_FILE = os.path.join(config.agent_data_dir, "agent_settings.json")
_lock = threading.Lock()

KEY_ENV = {
    "weather": "WEATHER_API_KEY",
    "exchange_rate": "EXCHANGE_API_KEY",
    "stock_quote": "STOCK_API_KEY",
}


def _load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_settings(settings: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def get_key(tool_id: str) -> str:
    """env 优先 → 本地设置文件。"""
    env_val = os.getenv(KEY_ENV.get(tool_id, ""), "")
    if env_val:
        return env_val
    return _load_settings().get(f"{tool_id}_api_key", "")


def get_key_status() -> dict:
    """各外部工具的 key 配置状态（脱敏）。"""
    status = {}
    for tool_id, env_name in KEY_ENV.items():
        key = get_key(tool_id)
        status[tool_id] = {
            "configured": bool(key),
            "source": "env" if os.getenv(env_name, "") else "file" if key else None,
            "masked": (key[:4] + "***" + key[-4:]) if key else "",
        }
    return status


def set_keys(keys: dict) -> dict:
    """保存 key 到设置文件，返回新状态。"""
    settings = _load_settings()
    for tool_id in KEY_ENV:
        if keys.get(f"{tool_id}_api_key"):
            settings[f"{tool_id}_api_key"] = keys[f"{tool_id}_api_key"].strip()
    _save_settings(settings)
    return get_key_status()


def _http_get(url: str, params: dict | None = None, timeout: float = 15) -> httpx.Response | None:
    try:
        return httpx.get(url, params=params, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; WorkerToolbox/1.0)"})
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# 天气（open-meteo，免 key）
# ═══════════════════════════════════════════════════════════════

def weather(city: str) -> dict:
    """查询城市当前天气。"""
    city = (city or "").strip().rstrip("市")
    if not city:
        return {"error": "weather_city_missing"}
    # ① geocoding：城市 → 坐标
    resp = _http_get("https://geocoding-api.open-meteo.com/v1/search",
                     {"name": city, "count": 1, "language": "zh", "format": "json"})
    if resp is None or resp.status_code != 200:
        return {"error": "weather_api_unreachable"}
    results = (resp.json() or {}).get("results") or []
    if not results:
        return {"error": f"weather_not_found: 无法解析城市「{city}」"}
    loc = results[0]
    # ② forecast：当前天气
    resp = _http_get("https://api.open-meteo.com/v1/forecast",
                     {"latitude": loc.get("latitude"), "longitude": loc.get("longitude"),
                      "current_weather": "true",
                      "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                      "timezone": "auto"})
    if resp is None or resp.status_code != 200:
        return {"error": "weather_api_unreachable"}
    data = resp.json() or {}
    cur = data.get("current") or {}
    codes = {0: "晴朗", 1: "基本晴朗", 2: "多云", 3: "阴", 45: "雾", 48: "雾凇",
             51: "小毛毛雨", 53: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
             71: "小雪", 73: "中雪", 75: "大雪", 80: "阵雨", 81: "强阵雨",
             82: "暴雨", 95: "雷暴", 96: "雷暴伴冰雹", 99: "强雷暴伴冰雹"}
    wcode = cur.get("weather_code", 0)
    return {
        "result": {
            "城市": f"{loc.get('name', city)}（{loc.get('country', '')}）",
            "温度": f"{cur.get('temperature_2m', '?')}°C",
            "天气": codes.get(wcode, f"代码{wcode}"),
            "湿度": f"{cur.get('relative_humidity_2m', '?')}%",
            "风速": f"{cur.get('wind_speed_10m', '?')} km/h",
        }
    }


# ═══════════════════════════════════════════════════════════════
# 汇率（open.er-api.com，免 key；备用 exxx 需 key）
# ═══════════════════════════════════════════════════════════════

_CN_CURRENCY = {"美元": "USD", "美金": "USD", "人民币": "CNY", "元": "CNY", "欧元": "EUR",
                "日元": "JPY", "英镑": "GBP", "港币": "HKD", "韩元": "KRW", "澳元": "AUD",
                "加元": "CAD", "卢布": "RUB", "新加坡元": "SGD", "新元": "SGD"}


def _normalize_currency(name: str) -> str:
    name = (name or "").strip().upper()
    return _CN_CURRENCY.get(name, name)


def exchange_rate(base: str, target: str) -> dict:
    """查询汇率：exchange_rate('USD', 'CNY') 表示 1 USD = ? CNY。"""
    base = _normalize_currency(base)
    target = _normalize_currency(target)
    if not base or not target:
        return {"error": "exchange_rate_missing"}
    resp = _http_get(f"https://open.er-api.com/v6/latest/{base}")
    if resp is None or resp.status_code != 200:
        return {"error": "exchange_api_unreachable"}
    data = resp.json() or {}
    rates = data.get("rates") or {}
    if target not in rates:
        return {"error": f"exchange_rate_not_found: 不认识的货币代码「{target}」"}
    return {"result": {"from": base, "to": target, "rate": rates[target],
                       "说明": f"1 {base} = {rates[target]} {target}"}}


# ═══════════════════════════════════════════════════════════════
# 股价（需 key；未配置 → 特殊码降级，Agent 引导配置）
# ═══════════════════════════════════════════════════════════════

def stock_quote(symbol: str) -> dict:
    """查询股价。未配置 key 返回 stock_key_missing（不触发重试）。"""
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return {"error": "stock_symbol_missing"}
    key = get_key("stock_quote")
    if not key:
        return {"error": "stock_key_missing"}
    # 兼容 alpha vantage 风格 API key（可换成任意兼容接口）
    resp = _http_get("https://www.alphavantage.co/query",
                     {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": key})
    if resp is None or resp.status_code != 200:
        return {"error": "stock_api_unreachable"}
    data = resp.json() or {}
    quote = data.get("Global Quote") or {}
    if not quote:
        return {"error": f"stock_not_found: 未找到代码「{symbol}」或 API key 无效"}
    return {"result": {
        "代码": quote.get("01. symbol", symbol),
        "价格": f"${quote.get('05. price', '?')}",
        "涨跌": f"{quote.get('09. change', '?')} ({quote.get('10. change percent', '?')})",
        "更新时间": quote.get("07. latest trading day", "?"),
    }}
