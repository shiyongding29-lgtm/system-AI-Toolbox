"""Scheduled Agent — 无人值守定时执行已保存的工作流（cron 调度）。"""
import os, json, re
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.routers.workflow_engine import run_workflow

router = APIRouter(prefix="/api/robot", tags=["robot"])

scheduler = BackgroundScheduler()
scheduler.start()

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'robots.json')
_robots = {}
_history = {}  # robot_id → [{time, status, result_preview}]


def _load():
    global _robots, _history
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                data = json.load(f)
                _robots = data.get('robots', {})
                _history = data.get('history', {})
        except: pass


def _save():
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump({'robots': _robots, 'history': _history}, f, ensure_ascii=False, indent=2)


def _resolve_vars(text: str) -> str:
    """替换模板变量。"""
    now = datetime.now()
    today = now.date()
    weekday = today.weekday()  # 0=Mon
    monday = today - timedelta(days=weekday)
    last_monday = monday - timedelta(days=7)
    last_sunday = monday - timedelta(days=1)
    vars_map = {
        '今天': today.isoformat(), '昨天': (today - timedelta(days=1)).isoformat(),
        '明天': (today + timedelta(days=1)).isoformat(),
        '上周一': last_monday.isoformat(), '上周日': last_sunday.isoformat(),
        '本周一': monday.isoformat(), '本周日': (monday + timedelta(days=6)).isoformat(),
        '本月一号': today.replace(day=1).isoformat(),
        '现在时间': now.strftime('%H:%M'), '当前年份': str(today.year),
    }
    for k, v in vars_map.items():
        text = text.replace(f'{{{k}}}', v)
    return text


class RobotConfig(BaseModel):
    name: str = ""
    plan: dict = {}
    schedule_type: str = "daily"  # daily, weekly, monthly
    time: str = "09:00"  # HH:MM
    weekday: int = 0  # 0=Mon, for weekly
    month_day: int = 1  # for monthly
    first_input: str = ""  # 模板输入，支持{今天}等变量
    enabled: bool = True


@router.post("/create")
async def create_robot(config: RobotConfig, robot_id: str = None):
    """创建/更新 Robot。如果 robot_id 已存在则更新。"""
    rid = robot_id or f"robot_{os.urandom(4).hex()}"
    _robots[rid] = config.model_dump()
    try: scheduler.remove_job(rid)
    except: pass
    if config.enabled:
        _schedule_robot(rid, config)
    _save()
    return {"code": 0, "msg": "ok", "data": {"id": rid}}


@router.get("/list")
async def list_robots():
    return {"code": 0, "msg": "ok", "data": [{"id": k, **v} for k, v in _robots.items()]}


@router.delete("/{robot_id}")
async def delete_robot(robot_id: str):
    _robots.pop(robot_id, None)
    try: scheduler.remove_job(robot_id)
    except: pass
    _save()
    return {"code": 0, "msg": "ok"}


@router.get("/{robot_id}/history")
async def robot_history(robot_id: str):
    """获取 Robot 执行历史。"""
    return {"code": 0, "msg": "ok", "data": _history.get(robot_id, [])}
async def toggle_robot(robot_id: str):
    if robot_id not in _robots:
        return {"code": 404, "msg": "Not found"}
    _robots[robot_id]['enabled'] = not _robots[robot_id].get('enabled', True)
    cfg = _robots[robot_id]
    try: scheduler.remove_job(robot_id)
    except: pass
    if cfg['enabled']:
        _schedule_robot(robot_id, RobotConfig(**cfg))
    _save()
    return {"code": 0, "msg": "ok", "data": _robots[robot_id]}


def _schedule_robot(rid: str, cfg: RobotConfig):
    """将 Robot 加入调度器。"""
    h, m = map(int, cfg.time.split(':'))

    if cfg.schedule_type == 'daily':
        trigger = CronTrigger(hour=h, minute=m)
    elif cfg.schedule_type == 'weekly':
        trigger = CronTrigger(day_of_week=cfg.weekday, hour=h, minute=m)
    elif cfg.schedule_type == 'monthly':
        trigger = CronTrigger(day=cfg.month_day, hour=h, minute=m)
    else:
        trigger = CronTrigger(hour=h, minute=m)

    def execute():
        plan = cfg['plan']
        user_input = {"text": _resolve_vars(cfg.get('first_input', ''))}
        wid = run_workflow(plan, user_input)
        import time; time.sleep(2)
        from backend.routers.workflow_engine import get_workflow_status
        status = get_workflow_status(wid)
        now = datetime.now().isoformat()
        if rid not in _history: _history[rid] = []
        _history[rid].insert(0, {
            'time': now,
            'status': status.get('status', '?') if status else '?',
            'workflow_id': wid,
            'node_count': len(plan.get('nodes', [])),
            'result_preview': str(user_input.get('text', ''))[:100],
        })
        if len(_history[rid]) > 20: _history[rid] = _history[rid][:20]
        _save()

    scheduler.add_job(execute, trigger, id=rid, replace_existing=True)


# 启动时加载并恢复所有 Robot
_load()
for rid, cfg in _robots.items():
    if cfg.get('enabled', True):
        try: _schedule_robot(rid, RobotConfig(**cfg))
        except: pass
