"""
shusousou - 配置文件
所有可配置的参数都在这里，便于统一管理
"""

import os

# ============================================
# DeepSeek AI 配置
# ============================================
# 请将下方的密钥替换为你的 DeepSeek API Key
# 获取地址：https://platform.deepseek.com/
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# ============================================
# 网站基本设置
# ============================================
SITE_NAME = {
    "zh": "书搜搜",
    "en": "BookSearch"
}
SITE_DESCRIPTION = {
    "zh": "AI驱动的图书推荐平台",
    "en": "AI-Powered Book Recommendation Platform"
}

# 默认语言
DEFAULT_LANGUAGE = "zh"  # zh = 中文, en = English

# ============================================
# 数据库配置
# ============================================
# 开发阶段使用SQLite
DATABASE_URL = "sqlite:///./shusousou/database/database.db"

# ============================================
# 邮件发送设置
# ============================================
# 用于发送验证邮件和通知邮件
# 以QQ邮箱为例，需要开启SMTP服务
MAIL_SERVER = "smtp.qq.com"
MAIL_PORT = 587
MAIL_USERNAME = ""  # ← 请替换为你的邮箱
MAIL_PASSWORD = ""  # ← 请替换为你的SMTP授权码
MAIL_FROM = ""      # ← 请替换为发件人邮箱

# ============================================
# 服务器运行配置
# ============================================
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# ============================================
# 图书库模拟 API 配置
# ============================================
# 开发阶段使用模拟接口
LIBRARY_API_MODE = "mock"  # "mock" = 模拟数据, "real" = 真实API
LIBRARY_API_URL = "http://localhost:8000/api/library"  # 模拟API地址