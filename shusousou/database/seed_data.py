"""
书搜搜 - 初始化种子数据
"""

from .models import User, Post, engine, Base
from sqlalchemy.orm import Session
import hashlib


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def seed():
    """添加种子数据"""
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as session:
        if session.query(User).count() > 0:
            print("数据库中已有数据，跳过初始化")
            return
        
        print("开始添加种子数据...")
        
        users_data = [
            {"username": "小明", "email": "xiaoming@test.com", "password": "123456", "is_verified": True},
            {"username": "小红", "email": "xiaohong@test.com", "password": "123456", "is_verified": True},
            {"username": "测试用户", "email": "test@test.com", "password": "123456", "is_verified": True},
        ]
        
        users = []
        for u in users_data:
            user = User(
                username=u["username"],
                email=u["email"],
                password_hash=hash_password(u["password"]),
                is_verified=u["is_verified"]
            )
            session.add(user)
            session.flush()
            users.append(user)
        
        posts_data = [
            {"user_id": users[0].id, "book_name": "机器学习", "author": "周志华",
             "isbn": "978-7-302-45679-1", "category": "计算机",
             "content": "非常经典的机器学习入门书，讲解清晰，适合初学者。"},
            {"user_id": users[1].id, "book_name": "三体", "author": "刘慈欣",
             "isbn": "978-7-5366-9293-0", "category": "科幻",
             "content": "科幻巨作！强烈推荐，看完震撼了好久。"},
            {"user_id": users[0].id, "book_name": "活着", "author": "余华",
             "isbn": "978-7-5063-6782-8", "category": "文学",
             "content": "看完让人思考人生意义的一本书。"},
        ]
        
        for p in posts_data:
            session.add(Post(**p))
        
        session.commit()
        print(f"种子数据完成！用户 {len(users_data)} 个，帖子 {len(posts_data)} 个")


if __name__ == "__main__":
    seed()
