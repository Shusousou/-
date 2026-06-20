"""
书搜搜 - 数据库初始化脚本
运行此脚本创建所有数据表

用法：
    python -m shusousou.database.init_db
"""

from .models import init_database

if __name__ == "__main__":
    init_database()
    print("数据库已就绪！")
