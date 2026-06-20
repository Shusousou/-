"""
书搜搜 - 公共工具函数
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession

def get_db():
    """获取数据库session"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(BASE_DIR, "database", "database.db")
    db_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return DBSession(db_engine)


def get_current_user(request):
    """获取当前登录用户"""
    from .database.models import User
    user_id = request.cookies.get("user_id")
    if user_id:
        with get_db() as session:
            return session.query(User).filter(User.id == int(user_id)).first()
    return None
