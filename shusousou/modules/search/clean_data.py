"""
书搜搜 - 离线洗数脚本
============================================
用途：读取 mock_library_books.csv，调用 DeepSeek AI 为每本英文书
     生成中文书名（title_cn）和中文学科标签（category_cn），
     导出为新表格 processed_library_books.csv。

用法（在项目根目录 shusousou/ 的父目录运行）：
    cd 项目父目录
    python -m shusousou.modules.search.clean_data

或者直接运行：
    python shusousou/modules/search/clean_data.py

依赖：
    pip install requests
============================================
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime

# ============================================
# 配置区
# ============================================

# 从 config.py 中读取 API Key
try:
    from shusousou.config import DEEPSEEK_API_KEY
except ImportError:
    DEEPSEEK_API_KEY = ""

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# 批处理大小（每批 10 本，触发一次 API 调用）
BATCH_SIZE = 10
# 批间休眠秒数（防止 Rate Limit）
SLEEP_SECONDS = 1.5

# 文件路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSV_SOURCE = os.path.join(BASE_DIR, "database", "mock_library_books.csv")
CSV_TARGET = os.path.join(BASE_DIR, "database", "processed_library_books.csv")


# ============================================
# 核心函数
# ============================================

def _build_batch_prompt(books_batch: list[dict]) -> str:
    """为一批图书构建 AI 提示词

    Args:
        books_batch: 一批图书字典列表（10本）

    Returns:
        发送给 DeepSeek 的 system prompt
    """
    prompt = """你是一个专业的中文图书编目助手。请为以下每本英文图书完成两个任务：

任务 A：将英文书名翻译为通顺准确的中文书名。
任务 B：根据其学科（Subjects）提取 2-3 个最核心的中文学科分类标签，用中文分号隔开。

请按以下 JSON 格式返回结果（不要加任何额外文字说明）：
{
    "results": [
        {
            "original_title": "原始英文书名（精确匹配）",
            "title_cn": "中文书名翻译",
            "category_cn": "中文标签1; 中文标签2; 中文标签3"
        },
        ...
    ]
}

以下是需要处理的图书列表：
"""
    for i, book in enumerate(books_batch, 1):
        title = book.get("Title (Complete)", "").strip()
        subjects = book.get("Subjects", "").strip()
        prompt += f'\n{i}. 书名: {title}\n   学科: {subjects}\n'
    return prompt.strip()


def _call_deepseek(prompt: str) -> list[dict] | None:
    """调用 DeepSeek API

    Args:
        prompt: 完整的提示词

    Returns:
        解析后的结果列表，失败返回 None
    """
    try:
        import requests
        response = requests.post(
            url=DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个专业的图书编目助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 4096
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # 提取 JSON（处理可能存在的 markdown 代码块）
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0].strip()
        if content.startswith("```json"):
            content = content[7:]
            content = content.rsplit("```", 1)[0].strip()

        data = json.loads(content)
        return data.get("results", [])

    except Exception as e:
        print(f"  [API Error] {str(e)[:100]}")
        return None


def _fallback_translate(batch: list[dict]) -> list[dict]:
    """API 调用失败时的降级方案——基于规则提取中文信息

    Args:
        batch: 一批图书字典

    Returns:
        带中文字段的字典列表
    """
    results = []
    for book in batch:
        title = book.get("Title (Complete)", "").strip()
        subjects = book.get("Subjects", "").strip()

        # 降级 title_cn：将书名的副标题分割，取主标题
        title_cn = title.split(" /")[0].strip() if title else ""
        # 去掉末尾的英文句点和空格
        title_cn = title_cn.rstrip(".").strip()

        # 降级 category_cn：直接使用原始 Subjects，按分号切分后取前 3 个
        if subjects:
            parts = [s.strip().rstrip(".") for s in subjects.split(";")]
            category_cn = "; ".join(parts[:3])
        else:
            category_cn = ""

        results.append({
            "original_title": title,
            "title_cn": title_cn,
            "category_cn": category_cn,
        })
    return results


def _parse_ai_results(ai_results: list[dict], batch: list[dict]) -> list[dict]:
    """将 AI 返回结果与原始行数据合并

    Args:
        ai_results: AI 返回的中文字段列表
        batch: 原始行数据列表

    Returns:
        合并后的数据行
    """
    merged = []
    for book in batch:
        og_title = book.get("Title (Complete)", "").strip()
        # 在 AI 结果中查找对应条目
        match = None
        for ai_item in ai_results:
            if ai_item.get("original_title", "").strip() == og_title:
                match = ai_item
                break
        if match:
            book["title_cn"] = match.get("title_cn", "").strip()
            book["category_cn"] = match.get("category_cn", "").strip()
        else:
            # AI 漏掉了这本，用降级方案
            fallback = _fallback_translate([book])[0]
            book["title_cn"] = fallback["title_cn"]
            book["category_cn"] = fallback["category_cn"]
        merged.append(book)
    return merged


# ============================================
# 主流程
# ============================================

def run_clean():
    """主洗数流程"""
    print("=" * 60)
    print(f"书搜搜 - 离线洗数脚本")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Step 1: 检查 API Key
    if not DEEPSEEK_API_KEY:
        print("\n[!]  警告: DEEPSEEK_API_KEY 为空！")
        print("   脚本将使用规则降级方案，不会调用 AI。")
        print("   如需 AI 翻译，请先在 config.py 中填入 API Key。")
        print("   (从 https://platform.deepseek.com 获取)")
        use_ai = False
    else:
        print(f"\n[OK] DeepSeek API Key 已配置 (前8位: {DEEPSEEK_API_KEY[:8]}...)")
        use_ai = True

    # Step 2: 读取源 CSV
    print(f"\n[1/4] 读取源文件: {CSV_SOURCE}")
    if not os.path.exists(CSV_SOURCE):
        print(f"  [X] 文件不存在: {CSV_SOURCE}")
        sys.exit(1)

    with open(CSV_SOURCE, "r", encoding="gb18030") as f:
        reader = csv.DictReader(f)
        all_books = list(reader)

    total = len(all_books)
    print(f"  [OK] 共读取 {total} 条图书记录")
    print(f"     列名: {list(all_books[0].keys())}")

    # Step 3: 分批处理
    print(f"\n[2/4] 开始处理（每批 {BATCH_SIZE} 条）...")

    processed = []
    batch_count = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_idx in range(batch_count):
        start = batch_idx * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)
        batch = all_books[start:end]

        print(f"  处理第 {batch_idx + 1}/{batch_count} 批 (记录 {start + 1}-{end}/{total})...", end="")

        if use_ai:
            # 使用 AI
            prompt = _build_batch_prompt(batch)
            ai_results = _call_deepseek(prompt)
            if ai_results:
                batch_processed = _parse_ai_results(ai_results, batch)
                print(f" AI 处理完成 [OK]")
            else:
                print(f" AI 调用失败，使用降级方案...")
                for book in batch:
                    fb = _fallback_translate([book])[0]
                    book["title_cn"] = fb["title_cn"]
                    book["category_cn"] = fb["category_cn"]
                batch_processed = batch
                print(f" 降级处理完成 [!]")
        else:
            # 降级方案
            for book in batch:
                fb = _fallback_translate([book])[0]
                book["title_cn"] = fb["title_cn"]
                book["category_cn"] = fb["category_cn"]
            batch_processed = batch
            print(f" 降级处理完成 [!]")

        processed.extend(batch_processed)

        # 批间休眠（防止 Rate Limit）
        if use_ai and batch_idx < batch_count - 1:
            time.sleep(SLEEP_SECONDS)

    print(f"\n[3/4] 数据增强完成，共处理 {len(processed)} 条记录")

    # Step 4: 导出新表格
    print(f"\n[4/4] 导出到: {CSV_TARGET}")

    # 确认目标列名
    if processed:
        fieldnames = list(processed[0].keys())
        # 确保 title_cn 和 category_cn 在最后
        for col in ["title_cn", "category_cn"]:
            if col in fieldnames:
                fieldnames.remove(col)
        fieldnames.extend(["title_cn", "category_cn"])

        with open(CSV_TARGET, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(processed)

        print(f"  [OK] 导出成功！文件: {CSV_TARGET}")
        print(f"     编码: UTF-8")
        print(f"     列数: {len(fieldnames)}")
        print(f"     新增列: title_cn, category_cn")
    else:
        print("  [X] 无数据可导出")
        sys.exit(1)

    # 统计降级比例
    ai_count = sum(1 for b in processed if b.get("title_cn") and
                   b["title_cn"] != b.get("Title (Complete)", "").split(" /")[0].strip().rstrip(".").strip())
    print(f"\n[  ] 统计:")
    print(f"   总记录: {total}")
    print(f"   AI/规则处理: {ai_count} 条")
    print(f"   降级处理: {total - ai_count} 条")
    print(f"\n{'=' * 60}")
    print(f"[OK] 全部完成！耗时: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    run_clean()
