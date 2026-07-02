# 📚 书搜搜 — 智能校园图书推荐平台

一个集成了AI图书推荐、书籍交换借阅和好书推荐论坛的校园图书服务平台。

## 项目结构
```
shusousou/
├── docs/              # 项目文档
├── logs/              # 开发日志
├── shusousou/         # 项目源码
│   ├── main.py        # 启动入口
│   ├── config.py      # 配置文件
│   ├── database/      # 数据库
│   ├── modules/       # 功能模块
│   │   ├── auth/      # 用户认证
│   │   ├── search/    # 书搜搜
│   │   ├── forum/     # 论坛
│   │   └── exchange/  # 交换借阅
│   ├── static/        # 静态文件
│   └── templates/     # 公共模板
└── README.md
```

## 快速开始

### 1. 安装Python
确保已安装 Python 3.10 或更高版本。

### 2. 安装依赖
```bash
cd D:\shusousou
pip install -r requirements.txt
```

### 3. 配置API Key
打开 `shusousou/config.py`，填入你的DeepSeek API Key。

### 4. 运行
```bash
python shusousou/main.py     #我前面那个用不了，后面这个可以：python -m shusousou.main
```

### 5. 访问
浏览器打开 http://localhost:8000

## 文档导航
| 想了解什么？ | 看哪个文档 |
|-------------|-----------|
| 项目整体介绍 | docs/00_项目总览.md |
| 功能需求细节 | docs/01_功能需求说明书.md |
| 技术实现方案 | docs/02_技术架构设计.md |
| 数据库结构 | docs/03_数据库设计.md |
| API接口 | docs/04_API接口规范.md |
| UI设计规范 | docs/05_UI设计规范.md |
| 开发规范 | docs/06_开发规范.md |
| 开发计划 | docs/07_开发步骤计划.md |
| 测试规范 | docs/08_测试规范.md |
