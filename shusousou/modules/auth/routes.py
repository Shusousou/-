"""
书搜搜 - 用户认证模块
负责：注册、登录、退出、邮箱验证
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import hashlib
import os

from ...database.models import User
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

router = APIRouter(prefix="/auth", tags=["auth"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
auth_templates = os.path.join(BASE_DIR, "modules", "auth", "templates")
global_templates = os.path.join(BASE_DIR, "templates")

loader = ChoiceLoader([
    FileSystemLoader(auth_templates),
    FileSystemLoader(global_templates)
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


from ...utils import get_db, get_current_user
from datetime import datetime


# ============================================
# 登录页面
# ============================================
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """显示登录页面"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    return templates.TemplateResponse(request, "login.html", {
        "language": lang,
        "current_user": current_user,
        "login_error": None,
        "login_success": None,
        "register_success": None
    })


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """处理登录"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    
    with get_db() as session:
        user = session.query(User).filter(User.email == email).first()
        
        if not user:
            msg = "该邮箱未注册" if lang == "zh" else "Email not registered"
            return templates.TemplateResponse(request, "login.html", {
                "language": lang, 
                "current_user": current_user,
                "login_error": msg, 
                "login_success": None,
                "register_success": None
            })
        
        if user.password_hash != hash_password(password):
            msg = "密码错误" if lang == "zh" else "Incorrect password"
            return templates.TemplateResponse(request, "login.html", {
                "language": lang, 
                "current_user": current_user,
                "login_error": msg, 
                "login_success": None,
                "register_success": None
            })
        
        if not user.is_verified:
            msg = "请先验证邮箱再登录" if lang == "zh" else "Please verify your email first"
            return templates.TemplateResponse(request, "login.html", {
                "language": lang, 
                "current_user": current_user,
                "login_error": msg, 
                "login_success": None,
                "register_success": None
            })
    
    # 登录成功
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="user_id", value=str(user.id))
    return response


# ============================================
# 注册页面
# ============================================
@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """显示注册页面"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    return templates.TemplateResponse(request, "register.html", {
        "language": lang,
        "current_user": current_user,
        "register_error": None,
        "register_success": None
    })


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """处理注册"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    
    if len(password) < 6:
        msg = "密码太短，至少6位" if lang == "zh" else "Password too short"
        return templates.TemplateResponse(request, "register.html", {
            "language": lang, 
            "current_user": current_user,
            "register_error": msg, 
            "register_success": None
        })
    
    with get_db() as session:
        existing = session.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        if existing:
            msg = "用户名或邮箱已被注册" if lang == "zh" else "Username or email already exists"
            return templates.TemplateResponse(request, "register.html", {
                "language": lang, 
                "current_user": current_user,
                "register_error": msg, 
                "register_success": None
            })
        
        verify_token = hashlib.md5(f"{email}{datetime.now()}".encode()).hexdigest()
        
        user = User(username=username, email=email,
                    password_hash=hash_password(password),
                    is_verified=True, verify_token=None)
        session.add(user)
        session.commit()
    
    # 发送验证邮件（开发模式：打印到控制台）
    verify_link = f"http://localhost:8000/auth/verify?token={verify_token}"
    from ...mailer import send_verification_email
    send_verification_email(email, username, verify_link)
    
    msg = f"注册成功！验证邮件已发送到 {email}，请检查收件箱（包括垃圾邮件）" if lang == "zh" else f"Registered! Verification sent to {email}. Check your inbox (including spam)."
    return templates.TemplateResponse(request, "register.html", {
        "language": lang, 
        "current_user": current_user,
        "register_error": None, 
        "register_success": msg
    })


# ============================================
# 忘记密码页面
# ============================================
@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request):
    """显示忘记密码页面"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    return templates.TemplateResponse(request, "forgot_password.html", {
        "language": lang,
        "current_user": current_user
    })


# ============================================
# 邮箱验证
# ============================================
@router.get("/verify")
async def verify_email(request: Request, token: str = ""):
    """验证邮箱"""
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    
    if not token:
        msg = "无效的验证链接" if lang == "zh" else "Invalid verification link"
        return templates.TemplateResponse(request, "login.html", {
            "language": lang, 
            "current_user": current_user,
            "login_error": msg, 
            "login_success": None,
            "register_success": None
        })
    
    with get_db() as session:
        user = session.query(User).filter(User.verify_token == token).first()
        if not user:
            msg = "验证链接已失效，请重新注册" if lang == "zh" else "Invalid or expired verification link"
            return templates.TemplateResponse(request, "login.html", {
                "language": lang, 
                "current_user": current_user,
                "login_error": msg, 
                "login_success": None,
                "register_success": None
            })
        
        user.is_verified = True
        user.verify_token = None
        session.commit()
    
    msg = "邮箱验证成功！请登录" if lang == "zh" else "Email verified! Please login"
    return templates.TemplateResponse(request, "login.html", {
        "language": lang, 
        "current_user": current_user,
        "login_error": None, 
        "login_success": None,
        "register_success": msg
    })


# ============================================
# 退出
# ============================================
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("user_id")
    return response
