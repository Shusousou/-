"""
������ - �����ļ�
���п����õĲ��������������ͳһ����
"""

import os

# ============================================
# DeepSeek AI ����
# ============================================
# ���·�������� DeepSeek API Key
# ��ȡ��ʽ��https://platform.deepseek.com/
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# ============================================
# ��վ��������
# ============================================
SITE_NAME = {
    "zh": "������",
    "en": "BookSearch"
}
SITE_DESCRIPTION = {
    "zh": "AI����ͼ���Ƽ�ƽ̨",
    "en": "AI-Powered Book Recommendation Platform"
}

# Ĭ������
DEFAULT_LANGUAGE = "zh"  # zh = ����, en = English

# ============================================
# ���ݿ�����
# ============================================
# �����׶�ʹ��SQLite
DATABASE_URL = "sqlite:///./shusousou/database/database.db"

# ============================================
# �ʼ���������
# ============================================
# ���ڷ�����֤�ʼ���֪ͨ�ʼ�
# ��QQ����Ϊ������Ҫ����SMTP����
MAIL_SERVER = "smtp.qq.com"
MAIL_PORT = 587
<<<<<<< HEAD
MAIL_USERNAME = ""  # ← 请替换为你的邮箱
MAIL_PASSWORD = ""  # ← 请替换为你的SMTP授权码
MAIL_FROM = ""      # ← 请替换为发件人邮箱
=======
MAIL_USERNAME = "2024604689@qq.com"  # �� ���滻Ϊ�������
MAIL_PASSWORD = "eqlovlpdiqfubbeh"  # �� ���滻Ϊ���SMTP��Ȩ��

MAIL_FROM = "2024604689@qq.com"      # �� ���滻Ϊ����������
>>>>>>> 3b86434654b7019dca9d855a2c39142a05552783

# ============================================
# ����������
# ============================================
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# ============================================
# ͼ���ģ��API����
# ============================================
# �����׶�ʹ��ģ������
LIBRARY_API_MODE = "mock"  # "mock" = ģ������, "real" = ��ʵAPI
LIBRARY_API_URL = "http://localhost:8000/api/library"  # ģ��API��ַ

