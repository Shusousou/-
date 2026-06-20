# 书搜搜 - 团队合作说明书

## 一、部门分工

| 部门 | 核心功能 | 负责文件 |
|------|----------|----------|
| **部门1** 书搜搜 | 图书搜索、AI推荐、图书馆状态 | `modules/search/` |
| **部门2** 登录/注册/UI | 登录注册、双语切换、页面风格 | `modules/auth/`, `templates/`, `config.py` |
| **部门3** 论坛 | 发帖回帖、点赞、分类浏览 | `modules/forum/`, `database/models/forum.py` |
| **部门4** 交换借阅 | 发布图书、挂需求、AI匹配、站内消息、邮件 | `modules/exchange/`, `database/models/exchange.py`, `mailer/` |
| **部门5** 图书馆数据 | 图书馆API模拟、馆藏动态数据 | `modules/search/library_api.py` |

## 二、文件结构地图

```
shusousou/
│
├── main.py                      # 入口文件 — 部门2可改路由挂载
├── config.py                    # 全局配置 — 部门2维护
├── utils.py                     # 通用工具 — 部门2维护
│
├── database/
│   ├── models/                  # 数据库模型（分模块存放）
│   │   ├── __init__.py          # 统一导出 + 数据库引擎
│   │   ├── user.py              # 用户表 — 部门2
│   │   ├── forum.py             # 帖子/评论/点赞表 — 部门3
│   │   └── exchange.py          # 交换/需求/匹配/消息表 — 部门4
│   ├── seed_data.py             # 种子数据
│   └── init_db.py               # 数据库初始化
│
├── mailer/                      # 邮件模块
│   ├── __init__.py
│   └── sender.py                # 邮件发送逻辑 — 部门4
│
├── modules/
│   ├── auth/                    # [部门2] 登录注册
│   │   ├── routes.py
│   │   └── templates/
│   │       └── login_register.html
│   │
│   ├── search/                  # [部门1] 书搜搜核心
│   │   ├── routes.py
│   │   ├── ai_helper.py         # AI推荐
│   │   ├── library_api.py       # 图书馆API — 部门5
│   │   └── templates/
│   │       └── search.html
│   │
│   ├── forum/                   # [部门3] 论坛
│   │   ├── routes.py
│   │   └── templates/
│   │       ├── forum_index.html
│   │       ├── new_post.html
│   │       └── post_detail.html
│   │
│   └── exchange/                # [部门4] 交换借阅
│       ├── routes.py
│       └── templates/
│           ├── exchange_index.html
│           ├── exchange_detail.html
│           ├── new_exchange.html
│           ├── new_request.html
│           └── my_requests.html
│
└── templates/                   # [部门2] 全局模板
    ├── base.html
    └── index.html
```

## 三、各部门详细任务

### 部门1 — 书搜搜功能
**负责文件：** `modules/search/` 整个目录

**具体任务：**
1. 搜索功能优化 — 当前：AI推荐+图书馆状态；需要：[待补充]
2. AI推荐策略优化 — 结果太少时自动扩展关键词搜索
3. 搜索结果展示改进

**关键接口：**
- `GET/POST /search/` — 搜索页面
- `ai_helper.py` 中的 `get_recommendations()` — AI推荐
- `library_api.py` 中的 `search_books()` — 图书馆状态

### 部门2 — 登录注册 & 网页风格
**负责文件：** `modules/auth/`, `templates/`, `config.py`, `utils.py`, `main.py`

**具体任务：**
1. 登录注册功能打磨
2. 中英文双语切换完善
3. 网页UI美化 — 统一风格、配色、响应式
4. 验证邮件真正发送 — 配置 Outlook SMTP

**关键接口：**
- `GET/POST /auth/login` — 登录
- `GET/POST /auth/register` — 注册
- `GET /auth/logout` — 退出
- `GET /auth/verify` — 邮箱验证
- `templates/base.html` — 全局导航栏和布局

### 部门3 — 论坛功能
**负责文件：** `modules/forum/`, `database/models/forum.py`

**具体任务：**
1. 帖子管理 — 发帖、查看详情、分类浏览、搜索
2. 评论功能 — 评论帖子、邮件通知作者
3. 点赞功能 — 每人每帖一次
4. 分类浏览 — 计算机、科幻、文学、其他

**关键接口：**
- `GET /forum/` — 帖子列表
- `GET/POST /forum/new` — 发帖
- `GET /forum/{id}` — 帖子详情
- `POST /forum/{id}/comment` — 评论
- `POST /forum/{id}/like` — 点赞

### 部门4 — 交换借阅功能
**负责文件：** `modules/exchange/`, `database/models/exchange.py`, `mailer/`

**具体任务：**
1. 发布图书 — 填写信息 + AI辅助生成借阅要求
2. 图书列表 — 搜索、浏览可借图书
3. 挂需求 + AI匹配 — 自动匹配通知
4. 站内消息 — 评论区沟通
5. 邮件真正发送 — 配置后启用

**关键接口：**
- `GET /exchange/` — 图书列表
- `GET/POST /exchange/new` — 发布图书
- `GET /exchange/{id}` — 图书详情+评论区
- `GET/POST /exchange/request/new` — 挂需求
- `GET /exchange/my-requests` — 我的需求
- `POST /exchange/match-all` — 全部匹配
- `POST /exchange/ai-generate-rules` — AI生成借阅规则

### 部门5 — 图书馆动态数据
**负责文件：** `modules/search/library_api.py`

**具体任务：**
1. 图书馆API模拟 — 改成动态数据，模拟真实图书馆系统行为
2. 馆藏数据生成 — 根据书名/作者/ISBN 生成合理馆藏信息

**关键接口：**
- `library_api.py` 中的 `search_books()` — 输入书名，输出馆藏状态列表

## 四、如何合作

```bash
# 1. Fork + Clone
git clone <项目地址>
cd shusousou

# 2. 各自开发（只改自己部门的文件）

# 3. 提交 PR

# 4. 项目负责人审核合并
```

## 五、注意事项

**公共文件（改前需沟通）：**
| 文件 | 谁可改 | 原因 |
|------|--------|------|
| `main.py` | 部门2 | 路由挂载入口 |
| `config.py` | 部门2 | 全局配置 |
| `utils.py` | 部门2 | 通用工具 |
| `database/models/__init__.py` | 所有人 | 模型注册 |

**新增路由规则：**
- 路由装饰器的 `prefix` 要正确
- 使用 `require_login()` 检查登录
- 双语文案用 `lang` 变量控制

**运行方式：**
```bash
cd shusousou
py -m uvicorn shusousou.main:app --host 0.0.0.0 --port 8000
py -m shusousou.database.seed_data  # 重置数据库
```

**测试账号：**
| 账号 | 密码 |
|------|------|
| test@test.com | 123456 |
| xiaoming@test.com | 123456 |

## 六、当前功能状态

| 功能 | 状态 | 部门 |
|------|------|------|
| 登录/注册 | 完成 | 2 |
| 中英文切换 | 完成 | 2 |
| 邮箱验证（模拟） | 完成 | 2 |
| 书搜搜AI推荐 | 完成 | 1 |
| 图书馆状态查询 | 完成 | 5 |
| 论坛发帖/评论/点赞 | 完成 | 3 |
| 交换发布图书 | 完成 | 4 |
| 交换挂需求+AI匹配 | 完成 | 4 |
| 站内消息+邮件通知 | 完成 | 4 |
| AI辅助写借阅规则 | 完成 | 4 |
| 真实邮件发送 | 待配置 | 2 |
| 定时匹配扫描 | 完成 | 4 |
