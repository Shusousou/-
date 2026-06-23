"""
书搜搜 - 搜索模块
负责：搜索页面、AI推荐、结果展示
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from ...database.models import User, engine
from .library_api import search_books

router = APIRouter(prefix="/search", tags=["search"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
search_templates = os.path.join(BASE_DIR, "modules", "search", "templates")
global_templates = os.path.join(BASE_DIR, "templates")

loader = ChoiceLoader([
    FileSystemLoader(search_templates),
    FileSystemLoader(global_templates)
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)


from ...utils import get_current_user


# ============================================
# 搜索页面
# ============================================
@router.get("/", response_class=HTMLResponse)
async def search_page(request: Request):
    """搜索页面"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    
    return templates.TemplateResponse(request, "search.html", {
        "language": lang,
        "current_user": current_user,
        "results": None,
        "query": ""
    })


@router.post("/", response_class=HTMLResponse)
async def search(
    request: Request,
    query: str = Form(...)
):
    """处理搜索请求"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)

    if not query.strip():
        msg = "请输入你想看的书" if lang == "zh" else "Please enter what you want to read"
        return templates.TemplateResponse(request, "search.html", {
            "language": lang,
            "current_user": current_user,
            "results": [],
            "query": query,
            "error": msg
        })

    # 一站式搜索：library_api.py 已内置 AI 意图理解 + 双层检索
    # 只调一次 search_books()，绝不重复调 AI
    lib_books = search_books(query)

    # 组装前端展示结果
    results = []
    for lib_book in lib_books:
        r = {
            "title": lib_book["title"],
            "title_cn": lib_book.get("title_cn", ""),
            "author": lib_book["author"],
            "isbn": lib_book["isbn"],
            "reason": "",
            "detail": "",
            "library_status": lib_book["status"],
            "library_location": lib_book.get("location", ""),
            "library_due_date": lib_book.get("due_date"),
            "forum_posts": [],
            "exchange_books": [],
        }
        results.append(r)

    return templates.TemplateResponse(request, "search.html", {
        "language": lang,
        "current_user": current_user,
        "results": results,
        "query": query
    })
