"""
书搜搜 - 交换模型
负责：交换图书、需求、匹配、消息表结构（部门4维护）
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from . import Base


class ExchangeBook(Base):
    __tablename__ = "exchange_books"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_name = Column(String(200), nullable=False)
    author = Column(String(100))
    isbn = Column(String(20), index=True)
    requirements = Column(Text)
    expectations = Column(Text)
    contact_type = Column(String(20), default="")
    contact = Column(String(200), default="")
    status = Column(String(20), default="available")
    email_notify = Column(Boolean, default=
True)
    created_at = Column(DateTime, default=datetime.now)

    owner = relationship("User", back_populates="exchange_books")


class ExchangeRequest(Base):
    __tablename__ = "exchange_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(Text, nullable=False)
    keywords = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class RequestMatch(Base):
    __tablename__ = "request_matches"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("exchange_requests.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("exchange_books.id"), nullable=False)
    match_reason = Column(Text)
    is_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)


class ExchangeMessage(Base):
    __tablename__ = "exchange_messages"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("exchange_books.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])

