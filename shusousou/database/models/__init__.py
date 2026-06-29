"""
书搜搜 - 数据库模型
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(BASE_DIR, "database", "database.db")
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()


def init_database():
    """创建所有数据表"""
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成！")


# 导入所有模型（确保它们在 Base.metadata 中注册）
from .user import User
from .forum import Post, Comment, Like, Star, CelebrityReview
from .exchange import ExchangeBook, ExchangeRequest, RequestMatch, ExchangeMessage

