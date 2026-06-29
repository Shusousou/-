"""
书搜搜 · 图书馆动态流转模拟 — FastAPI 路由
==========================================
- GET  /simulation/          模拟沙盘页面
- GET  /simulation/api/state  获取当前状态 (JSON)
- POST /simulation/api/step   单步执行
- POST /simulation/api/toggle 启动/暂停
- POST /simulation/api/reset  重置
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

from jinja2 import Environment, FileSystemLoader, ChoiceLoader

from ...utils import get_current_user
from .engine import get_engine, reset_engine, _start_background, _stop_background

router = APIRouter(prefix="/simulation", tags=["simulation"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sim_templates = os.path.join(BASE_DIR, "modules", "simulation", "templates")
global_templates = os.path.join(BASE_DIR, "templates")
forum_templates = os.path.join(BASE_DIR, "modules", "forum", "templates")

loader = ChoiceLoader([
    FileSystemLoader(sim_templates),
    FileSystemLoader(forum_templates),
    FileSystemLoader(global_templates),
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)


# ============================================
# 模拟沙盘页面
# ============================================
@router.get("/", response_class=HTMLResponse)
async def simulation_page(request: Request):
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)

    engine = get_engine()
    snapshot = engine.get_snapshot()

    return templates.TemplateResponse(request, "simulation.html", {
        "language": lang,
        "current_user": current_user,
        "snapshot": snapshot,
    })


# ============================================
# API: 获取当前状态
# ============================================
@router.get("/api/state")
async def get_state():
    engine = get_engine()
    snapshot = engine.get_snapshot()
    return JSONResponse({"success": True, "state": snapshot})


# ============================================
# API: 单步执行
# ============================================
@router.post("/api/step")
async def step_simulation():
    engine = get_engine()
    snapshot = engine.step()
    return JSONResponse({"success": True, "state": snapshot})


# ============================================
# API: 启动/暂停切换
# ============================================
@router.post("/api/toggle")
async def toggle_simulation():
    engine = get_engine()
    engine.running = not engine.running
    if engine.running:
        _start_background()
    else:
        _stop_background()
    return JSONResponse({"success": True, "running": engine.running})


# ============================================
# API: 重置
# ============================================
@router.post("/api/reset")
async def reset_simulation():
    reset_engine()
    engine = get_engine()
    return JSONResponse({"success": True, "state": engine.get_snapshot()})


@router.post("/api/speed")
async def set_speed(request: Request):
    data = await request.json()
    speed = float(data.get("speed", 0.3))
    speed = max(0.05, min(2.0, speed))
    engine = get_engine()
    engine.speed = speed
    return JSONResponse({"success": True, "speed": engine.speed})
