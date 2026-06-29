"""
书搜搜 - 论坛模型
负责：帖子、评论、点赞、收藏表结构 + 名人书评
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from . import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_name = Column(String(200), nullable=False)
    author = Column(String(100))
    isbn = Column(String(20), index=True)
    category = Column(String(50))
    content = Column(Text, nullable=False)
    review_type = Column(String(20), default="user")  # "user" | "celebrity"
    likes_count = Column(Integer, default=0)
    stars_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    post = relationship("Post", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class Star(Base):
    """帖子收藏/书签"""
    __tablename__ = "stars"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)


class CelebrityReview(Base):
    """名人书评（模拟数据源）"""
    __tablename__ = "celebrity_reviews"

    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String(20), index=True, nullable=False)
    reviewer_name = Column(String(100), nullable=False)
    reviewer_title = Column(String(200), default="")  # 头衔
    content = Column(Text, nullable=False)
    rating = Column(Integer, default=5)  # 1-5 星
    source = Column(String(200), default="")  # 来源
    created_at = Column(DateTime, default=datetime.now)

