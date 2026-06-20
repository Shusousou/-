"""
书搜搜 - 图书馆API封装
============================================
⚠️ 重要说明：
   后续对接真实图书馆API时，**只修改本文件**即可，
   其他文件不需要改动。
   
   修改方法：
   1. 修改 search_books() 函数内部的API调用
   2. 确保返回格式与本文件一致即可
============================================
"""

import os
import json

# ============================================
# 模拟数据（开发阶段使用）
# ============================================
MOCK_BOOKS = [
    {
        "id": "BK001",
        "title": "机器学习",
        "author": "周志华",
        "isbn": "978-7-302-45679-1",
        "publisher": "清华大学出版社",
        "publish_year": "2016",
        "category": ["计算机", "人工智能"],
        "location": "3楼A区05架",
        "status": "available",
        "due_date": None,
        "total_copies": 5,
        "available_copies": 2
    },
    {
        "id": "BK002",
        "title": "统计学习方法",
        "author": "李航",
        "isbn": "978-7-302-47752-9",
        "publisher": "清华大学出版社",
        "publish_year": "2019",
        "category": ["计算机", "机器学习"],
        "location": "3楼A区06架",
        "status": "borrowed",
        "due_date": "2025-07-01",
        "total_copies": 3,
        "available_copies": 0
    },
    {
        "id": "BK003",
        "title": "深度学习",
        "author": "Ian Goodfellow",
        "isbn": "978-7-111-60888-8",
        "publisher": "机械工业出版社",
        "publish_year": "2017",
        "category": ["计算机", "深度学习"],
        "location": "3楼A区07架",
        "status": "available",
        "due_date": None,
        "total_copies": 2,
        "available_copies": 1
    },
    {
        "id": "BK004",
        "title": "三体",
        "author": "刘慈欣",
        "isbn": "978-7-5366-9293-0",
        "publisher": "重庆出版社",
        "publish_year": "2008",
        "category": ["科幻"],
        "location": "2楼B区12架",
        "status": "available",
        "due_date": None,
        "total_copies": 10,
        "available_copies": 3
    },
    {
        "id": "BK005",
        "title": "活着",
        "author": "余华",
        "isbn": "978-7-5063-6782-8",
        "publisher": "作家出版社",
        "publish_year": "2012",
        "category": ["文学"],
        "location": "2楼A区03架",
        "status": "borrowed",
        "due_date": "2025-06-25",
        "total_copies": 8,
        "available_copies": 0
    },
    {
        "id": "BK006",
        "title": "红楼梦",
        "author": "曹雪芹",
        "isbn": "978-7-020-00220-7",
        "publisher": "人民文学出版社",
        "publish_year": "1996",
        "category": ["文学", "古典"],
        "location": "2楼A区01架",
        "status": "available",
        "due_date": None,
        "total_copies": 6,
        "available_copies": 2
    },
    {
        "id": "BK007",
        "title": "Python编程：从入门到实践",
        "author": "Eric Matthes",
        "isbn": "978-7-115-54608-1",
        "publisher": "人民邮电出版社",
        "publish_year": "2020",
        "category": ["计算机", "编程"],
        "location": "3楼B区08架",
        "status": "available",
        "due_date": None,
        "total_copies": 4,
        "available_copies": 1
    },
    {
        "id": "BK008",
        "title": "算法导论",
        "author": "Thomas H. Cormen",
        "isbn": "978-7-111-55701-8",
        "publisher": "机械工业出版社",
        "publish_year": "2013",
        "category": ["计算机", "算法"],
        "location": "3楼A区10架",
        "status": "borrowed",
        "due_date": "2025-06-30",
        "total_copies": 3,
        "available_copies": 0
    },
]


# ============================================
# 核心搜索函数
# ============================================
def search_books(keyword: str) -> list[dict]:
    """搜索图书馆馆藏图书
    
    ⚠️ 后续对接真实API时，只修改此函数内部实现
    
    Args:
        keyword: 搜索关键词
        
    Returns:
        图书列表，每本包含：
        - title: 书名
        - author: 作者
        - isbn: ISBN
        - status: "available" / "borrowed" / "not_found"
        - location: 馆藏位置
        - due_date: 预计归还日期（已借出时）
    
    后续对接真实API示例：
    -----------------------------------------
    def search_books(keyword: str) -> list[dict]:
        # 调用真实图书馆API
        response = requests.get(
            url="https://图书馆API地址/search",
            params={"q": keyword, "type": "keyword"}
        )
        data = response.json()
        
        # 转换为统一格式
        results = []
        for book in data["books"]:
            results.append({
                "title": book["title"],
                "author": book["author"],
                "isbn": book["isbn"],
                "status": "available" if book["available"] else "borrowed",
                "location": book["location"],
                "due_date": book.get("due_date")
            })
        return results
    -----------------------------------------
    """
    results = []
    keyword_lower = keyword.lower()
    
    for book in MOCK_BOOKS:
        # 简单关键词匹配（后续可优化）
        if (keyword_lower in book["title"].lower() or
            keyword_lower in book["author"].lower() or
            keyword_lower in book["isbn"]):
            
            results.append({
                "title": book["title"],
                "author": book["author"],
                "isbn": book["isbn"],
                "status": book["status"],
                "location": book["location"],
                "due_date": book.get("due_date")
            })
    
    return results


def get_book_by_isbn(isbn: str) -> dict | None:
    """根据ISBN查询单本书
    
    Args:
        isbn: ISBN号
        
    Returns:
        图书信息或None
    """
    for book in MOCK_BOOKS:
        if book["isbn"] == isbn:
            return {
                "title": book["title"],
                "author": book["author"],
                "isbn": book["isbn"],
                "status": book["status"],
                "location": book["location"],
                "due_date": book.get("due_date")
            }
    return None
