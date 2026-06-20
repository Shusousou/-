"""
书搜搜 - 论坛模块
负责：发帖、回帖、点赞、分类浏览
"""

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession
from datetime import datetime

from ...utils import get_current_user
from ...database.models import Post, Comment, Like, User
from ..search.library_api import search_books

router = APIRouter(prefix="/forum", tags=["forum"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
forum_templates = os.path.join(BASE_DIR, "modules", "forum", "templates")
global_templates = os.path.join(BASE_DIR, "templates")

loader = ChoiceLoader([
    FileSystemLoader(forum_templates),
    FileSystemLoader(global_templates)
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)

CATEGORIES = ["计算机", "科幻", "文学", "其他"]
CATEGORIES_EN = ["Computer", "Sci-Fi", "Literature", "Other"]


def get_db():
    db_path = os.path.join(BASE_DIR, "database", "database.db")
    db_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return DBSession(db_engine)


def require_login(request: Request):
    """检查登录，未登录跳转登录页"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return user


# ============================================
# 论坛首页 - 帖子列表
# ============================================
@router.get("/", response_class=HTMLResponse)
async def forum_index(request: Request):
    """帖子列表页"""
    # 登录检查
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    lang = request.cookies.get("language", "zh")
    category = request.query_params.get("category", "")
    search_q = request.query_params.get("q", "")
    
    with get_db() as session:
        # 查询帖子
        query = session.query(Post).order_by(Post.created_at.desc())
        
        if category:
            query = query.filter(Post.category == category)
        
        if search_q:
            query = query.filter(
                (Post.book_name.contains(search_q)) |
                (Post.content.contains(search_q)) |
                (Post.author.contains(search_q))
            )
        
        posts = query.all()
        
        # 获取每个帖子的评论数和点赞数
        post_list = []
        for p in posts:
            comment_count = session.query(Comment).filter(Comment.post_id == p.id).count()
            like_count = session.query(Like).filter(Like.post_id == p.id).count()
            
            # 查图书馆状态
            library_info = None
            lib_results = search_books(p.book_name)
            if lib_results:
                lib = lib_results[0]
                library_info = {
                    "status": lib["status"],
                    "location": lib.get("location", ""),
                    "due_date": lib.get("due_date")
                }
            
            post_list.append({
                "id": p.id,
                "book_name": p.book_name,
                "author": p.author or "",
                "content": p.content[:100] + ("..." if len(p.content) > 100 else ""),
                "category": p.category or "",
                "username": p.user.username if p.user else "匿名",
                "user_id": p.user_id,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
                "comment_count": comment_count,
                "like_count": like_count,
                "library": library_info
            })
    
    cats = CATEGORIES_EN if lang == "en" else CATEGORIES
    
    return templates.TemplateResponse(request, "forum_index.html", {
        "language": lang,
        "current_user": current_user,
        "posts": post_list,
        "categories": cats,
        "current_category": category,
        "search_q": search_q
    })


# ============================================
# 发帖页面
# ============================================
@router.get("/new", response_class=HTMLResponse)
async def new_post_page(request: Request):
    """发帖页面"""
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    lang = request.cookies.get("language", "zh")
    cats = CATEGORIES_EN if lang == "en" else CATEGORIES
    
    return templates.TemplateResponse(request, "new_post.html", {
        "language": lang,
        "current_user": current_user,
        "categories": cats
    })


@router.post("/new")
async def new_post(
    request: Request,
    book_name: str = Form(...),
    author: str = Form(""),
    category: str = Form(""),
    content: str = Form(...)
):
    """提交新帖"""
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    with get_db() as session:
        post = Post(
            user_id=current_user.id,
            book_name=book_name,
            author=author,
            category=category,
            content=content
        )
        session.add(post)
        session.commit()
        post_id = post.id
    
    return RedirectResponse(url=f"/forum/{post_id}", status_code=303)


# ============================================
# 帖子详情
# ============================================
@router.get("/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: int):
    """帖子详情页"""
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    lang = request.cookies.get("language", "zh")
    
    with get_db() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            msg = "帖子不存在" if lang == "zh" else "Post not found"
            return HTMLResponse(msg, status_code=404)
        
        # 帖子信息
        post_data = {
            "id": post.id,
            "book_name": post.book_name,
            "author": post.author or "",
            "content": post.content,
            "category": post.category or "",
            "username": post.user.username if post.user else "匿名",
            "user_id": post.user_id,
            "created_at": post.created_at.strftime("%Y-%m-%d %H:%M") if post.created_at else ""
        }
        
        # 馆藏状态
        library_info = None
        lib_results = search_books(post.book_name)
        if lib_results:
            lib = lib_results[0]
            library_info = {
                "status": lib["status"],
                "location": lib.get("location", ""),
                "due_date": lib.get("due_date")
            }
        
        # 评论
        comments = session.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()
        comment_list = []
        for c in comments:
            comment_list.append({
                "id": c.id,
                "content": c.content,
                "username": c.user.username if c.user else "匿名",
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
            })
        
        # 点赞数
        like_count = session.query(Like).filter(Like.post_id == post_id).count()
        
        # 当前用户是否已点赞
        liked = session.query(Like).filter(
            Like.post_id == post_id, Like.user_id == current_user.id
        ).first() is not None
    
    return templates.TemplateResponse(request, "post_detail.html", {
        "language": lang,
        "current_user": current_user,
        "post": post_data,
        "library": library_info,
        "comments": comment_list,
        "like_count": like_count,
        "liked": liked
    })


# ============================================
# 回复帖子
# ============================================
@router.post("/{post_id}/comment")
async def add_comment(
    request: Request,
    post_id: int,
    content: str = Form(...)
):
    """提交评论"""
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    with get_db() as session:
        comment = Comment(
            post_id=post_id,
            user_id=current_user.id,
            content=content
        )
        session.add(comment)
        session.commit()
        
        # 邮件通知帖子作者
        try:
            post = session.query(Post).filter(Post.id == post_id).first()
            author = session.query(User).filter(User.id == post.user_id).first()
            if author and author.email and author.id != current_user.id:
                from ...mailer import send_forum_comment_notification
                post_url = f"http://localhost:8000/forum/{post_id}"
                send_forum_comment_notification(
                    to_email=author.email,
                    receiver_name=author.username,
                    sender_name=current_user.username,
                    book_name=post.book_name,
                    comment_content=content,
                    post_url=post_url
                )
        except Exception as e:
            print(f"[Mail] 发送论坛评论通知失败: {e}")
    
    return RedirectResponse(url=f"/forum/{post_id}", status_code=303)


# ============================================
# 点赞/取消点赞
# ============================================
@router.post("/{post_id}/like")
async def toggle_like(request: Request, post_id: int):
    """切换点赞状态"""
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    
    with get_db() as session:
        existing = session.query(Like).filter(
            Like.post_id == post_id,
            Like.user_id == current_user.id
        ).first()
        
        if existing:
            session.delete(existing)
        else:
            like = Like(post_id=post_id, user_id=current_user.id)
            session.add(like)
        
        session.commit()
    
    return RedirectResponse(url=f"/forum/{post_id}", status_code=303)
