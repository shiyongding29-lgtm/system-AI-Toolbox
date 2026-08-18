"""
打工人工具箱 — 后端入口
FastAPI 应用创建、CORS、Router 注册、静态文件挂载。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.config import config
from backend.database import engine, Base


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """启动时创建数据库表 + 发现技能。"""
        Base.metadata.create_all(bind=engine)
        print("数据库表已创建。DB 就绪")
        from backend.services.skill_registry import skill_registry
        skill_registry.discover(force=True)
        yield

    app = FastAPI(
        title="system-AI-Toolbox API",
        version="0.1.0",
        description="system-AI-Toolbox — AI-powered productivity tools",
        lifespan=lifespan,
    )

    # CORS — allow_origins=["*"] 与 allow_credentials=True 是无效组合（浏览器会拒绝）
    cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()] or ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 确保上传目录存在
    os.makedirs(config.upload_dir, exist_ok=True)

    # 静态文件挂载
    app.mount("/uploads", StaticFiles(directory=config.upload_dir), name="uploads")

    # 注册 routers
    from backend.routers.history import router as history_router
    from backend.routers.translation_assistant import router as trans_router
    from backend.routers.email_doc import router as email_router
    from backend.routers.todo_extraction import router as todo_router
    from backend.routers.ppt_outline import router as ppt_router
    from backend.routers.weekly_report import router as weekly_router
    from backend.routers.document_summary import router as docsum_router
    from backend.routers.info_extraction import router as infoext_router
    from backend.routers.meeting_recorder import router as meeting_router
    from backend.routers.rag_qa import router as rag_router
    from backend.routers.deep_research import router as deep_research_router
    from backend.routers.task_planning import router as task_planning_router
    from backend.routers.document_comparison import router as doc_compare_router
    from backend.routers.data_analysis import router as data_analysis_router
    from backend.routers.multi_source_reader import router as multi_source_router
    from backend.routers.todos import router as todos_router
    from backend.routers.mindmap import router as mindmap_router
    from backend.routers.spreadsheet import router as spreadsheet_router
    from backend.routers.stream import router as stream_router
    from backend.routers.dashboard import router as dashboard_router
    from backend.routers.ai import router as ai_router
    from backend.routers.workflow import router as workflow_router
    from backend.routers.image_analyzer import router as image_router
    from backend.routers.chart_generator import router as chart_router
    from backend.routers.pdf_toolkit import router as pdf_router
    from backend.routers.sentiment_analyzer import router as sentiment_router
    from backend.routers.robot import router as robot_router
    from backend.routers.web_scraper import router as scraper_router
    from backend.routers.qr_generator import router as qr_router
    from backend.routers.file_converter import router as converter_router
    from backend.routers.agent import router as agent_router
    from backend.routers.core_tools import router as core_tools_router
    from backend.routers.skills import router as skills_router

    app.include_router(history_router)
    app.include_router(trans_router)
    app.include_router(email_router)
    app.include_router(todo_router)
    app.include_router(ppt_router)
    app.include_router(weekly_router)
    app.include_router(docsum_router)
    app.include_router(infoext_router)
    app.include_router(meeting_router)
    app.include_router(rag_router)
    app.include_router(deep_research_router)
    app.include_router(task_planning_router)
    app.include_router(doc_compare_router)
    app.include_router(data_analysis_router)
    app.include_router(multi_source_router)
    app.include_router(todos_router)
    app.include_router(mindmap_router)
    app.include_router(spreadsheet_router)
    app.include_router(stream_router)
    app.include_router(dashboard_router)
    app.include_router(ai_router)
    app.include_router(workflow_router)
    app.include_router(image_router)
    app.include_router(chart_router)
    app.include_router(pdf_router)
    app.include_router(sentiment_router)
    app.include_router(robot_router)
    app.include_router(scraper_router)
    app.include_router(qr_router)
    app.include_router(converter_router)
    app.include_router(agent_router)
    app.include_router(core_tools_router)
    app.include_router(skills_router)

    return app


app = create_app()


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
