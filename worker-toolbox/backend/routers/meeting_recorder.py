"""会议记录 API — 支持现场会议和线上会议两种模式 + 历史记录。"""
import json
import os
import re
import tempfile
import threading
import time
import datetime

from fastapi import APIRouter, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database import get_db, SessionLocal
from backend.models import MeetingRecord
from backend.services.llm_service import llm_service
from backend.services.audio_service import transcribe_audio, segments_to_text
from backend.services.prompt_library import MEETING_SUMMARY_SYSTEM
from backend.services.transcription_job import (
    create_job, get_job, start_transcription_thread,
)
from backend.routers.history import save_history
from backend.config import config

router = APIRouter(prefix="/api/meeting-recorder", tags=["meeting-recorder"])


class SummarizeRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    meeting_id: int | None = None


# ── 线上会议：全局录音状态 ──
_recorder = None
_recorder_lock = threading.Lock()
_recording_status = {"recording": False, "started_at": None, "output_dir": "", "prefix": "", "mode": ""}


# ── 保存会议记录到 MeetingRecord 表 ──

def _save_meeting_record(db: Session, mode: str, transcript: str, summary: str, duration: float, history_id: int, audio_path: str = None):
    record = MeetingRecord(
        history_id=history_id,
        transcript=transcript,
        summary=summary,
        duration_seconds=int(duration),
        mode=mode,
        audio_path=audio_path,
        created_at=datetime.datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.id


# ── 现场会议：浏览器上传录音 ──

@router.post("/upload")
async def meeting_upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """现场会议：上传浏览器录音文件，返回转写稿。"""
    suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        segments = transcribe_audio(tmp_path)
        transcript = segments_to_text(segments)
        duration = segments[-1]["end"] if segments else 0
        # 保存到 MeetingRecord
        record = MeetingRecord(
            transcript=transcript,
            summary="",
            duration_seconds=int(duration),
            mode="live",
            created_at=datetime.datetime.now(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return {
            "code": 0, "msg": "ok",
            "data": {
                "transcript": transcript,
                "segments_count": len(segments),
                "duration_seconds": round(duration, 1),
                "meeting_id": record.id,
            },
        }
    finally:
        os.unlink(tmp_path)


# ── 线上会议：后端双设备录音 ──

@router.post("/start-system")
async def start_system_recording():
    """线上会议：启动双设备录音（BlackHole 系统音频 + MacBook 麦克风）。"""
    global _recorder, _recording_status

    with _recorder_lock:
        if _recording_status["recording"]:
            return {"code": 400, "msg": "录音已在进行中", "data": None}

        from meeting_recorder.recorder import DualRecorder
        from meeting_recorder.utils import ensure_output_dir, generate_filename

        recording_dir = os.path.join(config.upload_dir, "meetings")
        ensure_output_dir(recording_dir)
        prefix = generate_filename()

        try:
            _recorder = DualRecorder()
            _recorder.start()
            _recording_status = {
                "recording": True,
                "started_at": time.time(),
                "output_dir": recording_dir,
                "prefix": prefix,
                "mode": "online",
            }
            return {
                "code": 0, "msg": "录音已开始",
                "data": {"prefix": prefix, "started_at": _recording_status["started_at"]},
            }
        except Exception as e:
            return {"code": 500, "msg": f"启动录音失败: {e}", "data": None}


@router.post("/stop-system")
async def stop_system_recording():
    """线上会议：停止录音，启动后台转写 Job，立即返回 job_id。"""
    global _recorder, _recording_status

    with _recorder_lock:
        if not _recording_status["recording"]:
            return {"code": 400, "msg": "没有正在进行的录音", "data": None}

        output_dir = _recording_status["output_dir"]
        prefix = _recording_status["prefix"]
        mode = _recording_status["mode"]

        try:
            system_wav, mic_wav = _recorder.stop(output_dir, prefix)
            duration = _recorder.duration
        except Exception as e:
            _recorder = None
            _recording_status = {"recording": False, "started_at": None, "output_dir": "", "prefix": "", "mode": ""}
            return {"code": 500, "msg": f"停止录音失败: {e}", "data": None}
        finally:
            _recorder = None

    if duration < 1.0:
        _recording_status = {"recording": False, "started_at": None, "output_dir": "", "prefix": "", "mode": ""}
        return {"code": 400, "msg": "录制时长不足 1 秒", "data": None}

    # 创建后台转写 Job，立即返回
    job = create_job()
    start_transcription_thread(
        job.job_id, system_wav, mic_wav, duration,
        prefix, output_dir, mode, SessionLocal,
    )

    _recording_status = {
        "recording": False, "started_at": None,
        "output_dir": "", "prefix": "", "mode": "",
        "job_id": job.job_id,
    }

    return {
        "code": 0, "msg": "ok",
        "data": {
            "job_id": job.job_id,
            "status": "transcribing",
            "duration_seconds": round(duration, 1),
        },
    }


@router.get("/transcription-status/{job_id}")
async def transcription_status(job_id: str):
    """查询后台转写 Job 的进度和结果。"""
    job = get_job(job_id)
    if not job:
        return {"code": 404, "msg": "Job 不存在", "data": None}

    return {
        "code": 0, "msg": "ok",
        "data": {
            "job_id": job.job_id,
            "status": job.status.value,
            "progress": job.progress,
            "status_message": job.status_message,
            "transcript": job.transcript,
            "summary": job.summary,
            "summary_error": job.summary_error,
            "duration_seconds": round(job.duration, 1),
            "meeting_id": job.meeting_id,
            "audio_url": job.audio_url,
            "history_id": job.history_id,
            "error": job.error,
        },
    }


@router.get("/status-system")
async def status_system_recording():
    """查询线上会议录音状态（录制中 / 转写中 / 空闲）。"""
    with _recorder_lock:
        if _recording_status["recording"]:
            dur = time.time() - _recording_status["started_at"]
            return {"code": 0, "msg": "ok", "data": {"recording": True, "duration_seconds": round(dur, 1)}}

        job_id = _recording_status.get("job_id")
        if job_id:
            return {"code": 0, "msg": "ok", "data": {"recording": False, "transcribing": True, "job_id": job_id}}

        return {"code": 0, "msg": "ok", "data": {"recording": False}}


@router.post("/summarize")
async def meeting_summarize(req: SummarizeRequest, db: Session = Depends(get_db)):
    """对转写稿生成会议纪要，并更新已有 MeetingRecord 的 summary 字段。"""
    summary = llm_service.complete(MEETING_SUMMARY_SYSTEM, req.transcript)
    history_id = save_history(
        db, "meeting-recorder",
        f"会议记录: {req.transcript[:50]}",
        req.transcript[:500], summary,
    )

    meeting_id = req.meeting_id
    if meeting_id:
        meeting = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
        if meeting:
            meeting.summary = summary
            meeting.history_id = history_id
            db.commit()

    # 同时自动提取待办事项
    from backend.services.prompt_library import TODO_EXTRACTION_SYSTEM
    import json, re
    todos_raw = llm_service.complete(TODO_EXTRACTION_SYSTEM, req.transcript)
    extracted = _parse_todo_items(todos_raw)

    return {
        "code": 0, "msg": "ok",
        "data": {
            "summary": summary,
            "extracted_todos": extracted,
        },
        "history_id": history_id,
    }


def _parse_todo_items(raw: str) -> list[dict]:
    """从 LLM 输出中解析待办 JSON 数组。"""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```\w*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    try:
        items = json.loads(cleaned)
        if isinstance(items, list):
            return items
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*\]", raw)
    if m:
        try:
            items = json.loads(m.group(0))
            if isinstance(items, list):
                return items
        except json.JSONDecodeError:
            pass
    return []




# ── 会议历史列表与详情 ──

@router.get("/list")
async def list_meetings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取会议记录历史列表。"""
    query = db.query(MeetingRecord).order_by(desc(MeetingRecord.created_at))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    data = []
    for m in items:
        data.append({
            "id": m.id,
            "mode": m.mode,
            "summary": m.summary[:300] if m.summary else "",
            "transcript_preview": m.transcript[:200] if m.transcript else "",
            "duration_seconds": m.duration_seconds,
            "audio_path": m.audio_path or "",
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
        })

    return {"code": 0, "msg": "ok", "data": {"items": data, "total": total}}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    """获取单条会议记录详情。"""
    m = db.query(MeetingRecord).filter(MeetingRecord.id == meeting_id).first()
    if not m:
        return {"code": 404, "msg": "记录不存在", "data": None}

    return {
        "code": 0, "msg": "ok",
        "data": {
            "id": m.id,
            "mode": m.mode,
            "transcript": m.transcript,
            "summary": m.summary,
            "duration_seconds": m.duration_seconds,
            "audio_path": m.audio_path or "",
            "created_at": m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else "",
        },
    }
