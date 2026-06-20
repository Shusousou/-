# 书搜搜 — API接口规范

## 版本历史
| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2025-06-10 | 初版 |

---

## 1. 图书馆模拟API

### 1.1 请求格式
`
GET /api/library/search?q={关键词}&type={title|author|isbn|all}
`

### 1.2 响应格式
`json
{
  "success": true,
  "total": 2,
  "books": [
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
      "due_date": null,
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
      "due_date": "2025-06-15",
      "total_copies": 3,
      "available_copies": 0
    }
  ]
}
`

### 1.3 状态说明
| status | 含义 | 显示 |
|--------|------|------|
| available | 在馆可借 | ✅ 在馆 |
| borrowed | 已借出 | ⏳ 已借出，预计X月X日归还 |
| (无匹配) | 图书馆没有这本书 | 📝 未找到，可向图书馆推荐 |

---

## 2. 用户系统API

### 2.1 注册
`
POST /auth/register
`
请求体：
`json
{
  "username": "张三",
  "email": "zhangsan@example.com",
  "password": "mypassword123"
}
`
响应：
`json
{
  "success": true,
  "message": "注册成功！验证邮件已发送到您的邮箱，请查收（如未收到请检查垃圾邮件）"
}
`

### 2.2 邮箱验证
`
GET /auth/verify?token={验证令牌}
`
响应：
`json
{
  "success": true,
  "message": "邮箱验证成功！"
}
`

### 2.3 登录
`
POST /auth/login
`
请求体：
`json
{
  "email": "zhangsan@example.com",
  "password": "mypassword123"
}
`
响应：
`json
{
  "success": true,
  "user": {"id": 1, "username": "张三", "email": "zhangsan@example.com"}
}
`

### 2.4 退出
`
GET /auth/logout
`
响应：重定向到首页

---

## 3. 内部模块API（函数调用）

### 3.1 论坛模块暴露的函数
`python
# 根据ISBN获取相关评论
def get_comments_by_isbn(isbn: str) -> list[dict]:
    \"\"\"返回格式：[{"username": "张三", "content": "...", "likes": 12}]\"\"\"

# 根据关键词搜索帖子
def search_posts(keyword: str) -> list[dict]:
    \"\"\"返回匹配的帖子列表\"\"\"
`

### 3.2 交换模块暴露的函数
`python
# 根据ISBN获取可借阅的交换图书
def get_available_books_by_isbn(isbn: str) -> list[dict]:
    \"\"\"返回：[{"book_name": "...", "owner": "李四", ...}]\"\"\"

# 检查新书是否匹配某个Request
def check_request_match(keywords: list, new_book: dict) -> bool:
    \"\"\"关键词匹配检查\"\"\"
`

### 3.3 用户模块暴露的函数
`python
# 获取当前登录用户
def get_current_user(request) -> dict | None:
    \"\"\"返回用户信息或None\"\"\"

# 发送邮件
def send_email(to: str, subject: str, body: str) -> bool:
    \"\"\"发送邮件，返回是否成功\"\"\"
`

---

## 4. DeepSeek AI API

### 4.1 调用格式
`python
import requests

response = requests.post(
    url="https://api.deepseek.com/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个图书推荐助手..."},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.7
    }
)
`

### 4.2 API Key 配置
在 config.py 中：
`python
DEEPSEEK_API_KEY = "你的API Key"  # ← 在这里填入
`

---

## 5. 注意事项
- 所有API格式在后续对接真实系统时都可能修改
- 修改时只需更新本文档和对应的Python文件
- 所有模块代码中，API调用都封装在独立函数中，便于修改
