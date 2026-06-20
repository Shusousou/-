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
from .library_api import search_books, get_book_by_isbn
from .ai_helper import get_recommendations

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
    
    # Step 1: AI分析用户输入，生成推荐书单
    ai_result = get_recommendations(query)
    keywords = ai_result.get("keywords", [query])
    recommended_books = ai_result.get("books", [])
    
    # Step 2: 用关键词查图书馆馆藏
    results = []
    for rec_book in recommended_books:
        # 先尝试用ISBN精确查询
        library_book = None
        if rec_book.get("isbn"):
            library_book = get_book_by_isbn(rec_book["isbn"])
        
        # ISBN没查到，用书名模糊搜索
        if not library_book:
            lib_results = search_books(rec_book["title"])
            library_book = lib_results[0] if lib_results else None
        
        # 组装结果
        result = {
            "title": rec_book["title"],
            "author": rec_book.get("author", ""),
            "isbn": rec_book.get("isbn", ""),
            "reason": rec_book.get("reason", ""),
            "detail": rec_book.get("detail", ""),
            "library_status": library_book["status"] if library_book else "not_found",
            "library_location": library_book.get("location", "") if library_book else "",
            "library_due_date": library_book.get("due_date") if library_book else None,
        }
        
        # Step 3: 从论坛查相关评论
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session as DBSession
        from ...database.models import Post
        db_path = os.path.join(BASE_DIR, "database", "database.db")
        db_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
        
        forum_posts = []
        with DBSession(db_engine) as session:
            posts = session.query(Post).filter(
                (Post.book_name == rec_book["title"]) |
                (Post.isbn == rec_book.get("isbn", ""))
            ).all()
            for p in posts:
                forum_posts.append({
                    "username": p.user.username if p.user else "匿名",
                    "content": p.content[:100] + ("..." if len(p.content) > 100 else ""),
                    "likes": p.likes_count,
                    "post_id": p.id
                })
        
        result["forum_posts"] = forum_posts
        
        # Step 4: 从交换市场查可借图书
        from ...database.models import ExchangeBook
        exchange_books = []
        with DBSession(db_engine) as session:
            ebooks = session.query(ExchangeBook).filter(
                (ExchangeBook.book_name == rec_book["title"]) |
                (ExchangeBook.isbn == rec_book.get("isbn", ""))
            ).filter(ExchangeBook.status == "available").all()
            for eb in ebooks:
                exchange_books.append({
                    "owner": eb.owner.username if eb.owner else "匿名",
                    "book_id": eb.id,
                    "requirements": eb.requirements
                })
        
        result["exchange_books"] = exchange_books
        results.append(result)
    
    return templates.TemplateResponse(request, "search.html", {
        "language": lang,
        "current_user": current_user,
        "results": results,
        "query": query,
        "keywords": keywords
    })
