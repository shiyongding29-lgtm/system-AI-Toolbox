"""Skills API — 技能浏览 / 执行 / 创建 / 删除。"""
import asyncio
import os
import tempfile

from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from backend.routers.workflow_engine import run_workflow
from backend.services.skill_registry import skill_registry

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
def list_skills():
    """技能摘要列表。"""
    return {"code": 0, "msg": "ok", "data": skill_registry.list_skills()}


@router.get("/{skill_id}")
def get_skill(skill_id: str):
    """技能完整详情（含方法论 + 默认流程）。"""
    skill = skill_registry.get_skill(skill_id)
    if not skill:
        return {"code": 404, "msg": "技能不存在", "data": None}
    return {"code": 0, "msg": "ok", "data": skill.detail()}


class SkillCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "🧩"
    color: str = "#8b5cf6"
    prompt: str = ""
    tool_ids: list[str] = []
    aliases: list[str] = []
    input_hint: str = ""


@router.post("")
def create_skill(req: SkillCreate):
    """前端可视化创建技能（服务端自动串联流程）。"""
    skill, err = skill_registry.create_skill(req.model_dump())
    if err:
        return {"code": 400, "msg": err, "data": None}
    return {"code": 0, "msg": "ok", "data": skill.detail() if skill else None}


@router.delete("/{skill_id}")
def delete_skill(skill_id: str):
    ok, err = skill_registry.delete_skill(skill_id)
    if not ok:
        return {"code": 403, "msg": err or "删除失败", "data": None}
    return {"code": 0, "msg": "ok", "data": {"deleted": skill_id}}


class SkillRun(BaseModel):
    text: str = ""


@router.post("/{skill_id}/run")
def run_skill(skill_id: str, req: SkillRun):
    """直接执行技能默认流程（不经 agent 循环，0 编排 LLM）。"""
    skill = skill_registry.get_skill(skill_id)
    if not skill:
        return {"code": 404, "msg": "技能不存在", "data": None}
    text = (req.text or "").strip()
    if not text:
        return {"code": 400, "msg": "请输入内容", "data": None}
    workflow_id = run_workflow(skill.plan, {"text": text})
    return {"code": 0, "msg": "ok",
            "data": {"workflow_id": workflow_id, "skill": skill.summary()}}


@router.post("/{skill_id}/run-audio")
async def run_skill_audio(skill_id: str, file: UploadFile = File(...)):
    """上传录音 → 转写 → 执行技能默认流程（录音输入，匹配 meeting_recorder 类技能）。"""
    from backend.services.audio_service import transcribe_audio, segments_to_text
    skill = skill_registry.get_skill(skill_id)
    if not skill:
        return {"code": 404, "msg": "技能不存在", "data": None}

    suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        segments = await asyncio.to_thread(transcribe_audio, tmp_path)
        transcript = segments_to_text(segments)
    finally:
        os.unlink(tmp_path)

    if not transcript.strip():
        return {"code": 400, "msg": "转写结果为空", "data": None}

    workflow_id = run_workflow(skill.plan, {"text": transcript})
    return {"code": 0, "msg": "ok",
            "data": {"workflow_id": workflow_id, "skill": skill.summary(),
                     "transcript_preview": transcript[:300], "transcript_len": len(transcript)}}
