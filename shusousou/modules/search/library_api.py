"""
书搜搜 - 图书馆API封装（终极双轨检索 + 全字段轰炸）
===================================================

设计理念：
  用户输入可以是任何自然语言——情绪、作者、书名、学科、场景。
  AI 实时返回 JSON 混合武器库：
    - subjects: 英文学科关键词（宏观大网，捞取学科内所有书）
    - specific_targets: 特定书名/作者/ISBN（微观精准直达）

  后端两条轨道任意命中即算成功：
    - 轨道 ①（学科）：subjects → 匹配 Subjects(英文) + category_cn(中文)
    - 轨道 ②（精准）：specific_targets → 匹配 Title/title_cn/Author/ISBN

  安全策略：
    - Key 为空/AI 超时/JSON 解析失败 → 降级为原始关键词全字段暴力搜索
    - 空搜索 → 返回前 10 条热门推荐
    - 接口签名 search_books(keyword) / get_book_by_isbn(isbn) 完全不变
===================================================
"""

import csv
import os
import re
import random
from datetime import date, timedelta


# ============================================
# 数据源模式配置
# ============================================
DATA_SOURCE_MODE = "CSV"
try:
    from shusousou.config import DATA_SOURCE_MODE as _CFG_MODE
    DATA_SOURCE_MODE = _CFG_MODE.upper()
except (ImportError, AttributeError):
    DATA_SOURCE_MODE = os.environ.get("BOOKSEARCH_DATA_SOURCE", "CSV").upper()


# ============================================
# 实时 AI 意图理解（情绪 → 英文学科关键词）
# ============================================

def _get_api_key() -> str:
    """从后端公共配置读取 DeepSeek API Key"""
    try:
        from shusousou.config import DEEPSEEK_API_KEY
        return (DEEPSEEK_API_KEY or "").strip()
    except (ImportError, AttributeError):
        return ""


def _call_ai_intent_extraction(user_input: str) -> dict | None:
    """【实时】调用 DeepSeek，返回 JSON 混合武器库

    Prompt 终极设计：
      AI 扮演天才图书检索专家，输出包含两个轨道的 JSON：
        - subjects: 英文学科关键词（宏观大网捞取）
        - specific_targets: 特定书名/作者/人物的中英文名（微观精准直达）

    Returns:
        {"subjects": ["Physics"], "specific_targets": ["Einstein", "爱因斯坦"]}
        或 None（Key 为空/解析失败/超时 → 触发降级）
    """
    api_key = _get_api_key()
    if not api_key:
        print("[AI 意图] config.py 未配置 DEEPSEEK_API_KEY，跳过实时 AI")
        return None

    system_prompt = (
        "你是一位精通中英双语、极具同理心的天才图书检索专家。\n"
        "你的任务：理解用户的情绪/状态/场景/人物/书名描述，"
        "将其映射为高校图书馆检索用的混合武器库。\n\n"
        "请严格遵循以下思考过程：\n"
        "第一步（理解本质）：分析用户当前的真实需求是什么\n"
        "  - 情绪舒缓？学术研究？追特定作者？找某本具体的书？\n"
        "第二步（桥接馆藏）：\n"
        "  - 从高校图书馆核心学科分类中挑选 1-3 个英文学科关键词（subjects）\n"
        "    （可选学科：Psychology, Literature, Philosophy, History, \n"
        "     Social sciences, Art, Fiction, Science, Religion, Education, \n"
        "     Political science, Economics, Computer science, Language, \n"
        "     Law, Medicine, Biography, Cosmology, Anthropology 等）\n"
        "  - 同时识别任何特定的书名、作者名、研究人物名（specific_targets）\n\n"
        "约束：严格只输出一个 JSON 字符串，格式如下：\n"
        '{"subjects": ["英文学科词1", "英文学科词2"], '
        '"specific_targets": ["特定书名/作者/人物的中英文名"]}\n\n'
        "注意：\n"
        "- 绝对不要包含 markdown 的 ```json 代码块标记\n"
        "- 绝对不要任何中文解释\n"
        "- subjects 只填英文学科词\n"
        "- specific_targets 可以是书名、作者名、人物名的中文或英文\n"
        "- 如果没有特定目标，specific_targets 留空数组 []\n\n"
        "示例：\n"
        '输入"我很疲劳想缓缓" -> '
        '{"subjects": ["Literature", "Psychology"], "specific_targets": []}\n'
        '输入"我想研究爱因斯坦" -> '
        '{"subjects": ["Physics", "Biography"], '
        '"specific_targets": ["Einstein", "爱因斯坦"]}\n'
        '输入"我想看霍金写的书" -> '
        '{"subjects": ["Physics", "Cosmology"], '
        '"specific_targets": ["Hawking", "霍金"]}\n'
        '输入"找《追风筝的人》作者写的全部书" -> '
        '{"subjects": ["Literature", "Fiction"], '
        '"specific_targets": ["Kite Runner", "Hosseini", "胡赛尼"]}\n'
        '输入"想看本关于机器学习的书" -> '
        '{"subjects": ["Computer science", "Science"], '
        '"specific_targets": []}'
    )

    try:
        import requests
        from shusousou.config import DEEPSEEK_API_URL, DEEPSEEK_MODEL
        response = requests.post(
            url=DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            },
            timeout=5
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        # 清理可能的 markdown 代码块标记
        content = content.replace("```json", "").replace("```", "").strip()

        import json as _json
        parsed = _json.loads(content)
        subjects = parsed.get("subjects", [])
        specific_targets = parsed.get("specific_targets", [])

        if isinstance(subjects, list) and isinstance(specific_targets, list):
            # 过滤空字符串
            subjects = [s for s in subjects if s and s.strip()]
            specific_targets = [t for t in specific_targets if t and t.strip()]
            print(f"[AI 意图] 用户输入\"{user_input}\" → "
                  f"subjects={subjects}, specific={specific_targets}")
            return {"subjects": subjects, "specific_targets": specific_targets}

        print(f"[AI 意图] JSON 字段类型异常: {content!r}")
        return None

    except Exception as e:
        print(f"[AI 意图] API 调用失败或 JSON 解析失败: {e}，进入降级直搜")
        return None


# ============================================
# 双层匹配算法
# ============================================

def _ai_multi_track_search(books: list[dict], ai_result: dict) -> list[dict]:
    """多轨全字段轰炸匹配：AI 返回的 subjects + specific_targets

    条件 ①（宏观学科）：subjects → 匹配 Subjects（英文）+ category_cn（中文）
    条件 ②（微观精准）：specific_targets → 匹配 Title / title_cn / Author / ISBN
    只要满足任意一个条件即命中。
    """
    subjects = [s.lower() for s in ai_result.get("subjects", []) if s and s.strip()]
    targets = [t.lower() for t in ai_result.get("specific_targets", []) if t and t.strip()]

    if not subjects and not targets:
        return []

    matched = []
    for book in books:
        hit = False

        # 条件 ①：宏观学科匹配
        if subjects:
            # Subjects 英文（在 category 列表中）
            cats_lower = [c.lower() for c in book.get("category", [])]
            # category_cn 中文
            cat_cn_lower = book.get("category_cn", "").lower()
            for s in subjects:
                if s in cat_cn_lower:
                    hit = True
                    break
                if any(s in cat for cat in cats_lower):
                    hit = True
                    break
            if hit:
                matched.append(book)
                continue

        # 条件 ②：微观精准匹配
        if targets:
            title_low = book.get("title", "").lower()
            title_cn_low = book.get("title_cn", "").lower()
            author_low = book.get("author", "").lower()
            isbn_clean = book.get("isbn", "").replace("-", "").replace(" ", "").lower()
            for t in targets:
                if t in title_low or t in title_cn_low:
                    hit = True
                    break
                if t in author_low:
                    hit = True
                    break
                if t in isbn_clean:
                    hit = True
                    break
            if hit:
                matched.append(book)

    print(f"[AI 多轨] subjects={subjects} + targets={targets} → {len(matched)} 本")
    return matched


def _extract_search_terms(raw_query: str) -> list[str]:
    """拆词：去掉语气词后拆出单个实词"""
    clean = raw_query
    for stop_word in ["我想", "我要", "我的", "想看", "看一本",
                       "推荐", "给我", "找本", "有没有", "书",
                       "的", "吗", "呢", "吧", "啊", "哦"]:
        clean = clean.replace(stop_word, " ")
    parts = re.split(r"[，,、\s]+", clean)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) > 1]


# ============================================
# 标准字段定义
# ============================================
STANDARD_FIELDS = [
    "id", "title", "author", "isbn", "publisher",
    "publish_year", "category", "location", "status",
    "due_date", "total_copies", "available_copies",
]


# ============================================
# 数据清洗函数
# ============================================

def _clean_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    cleaned = raw_title.rstrip("/ ").rstrip(".")
    cleaned = cleaned.rstrip(".").strip()
    return cleaned


def _clean_author(raw_author: str) -> str:
    if not raw_author:
        return ""
    cleaned = re.sub(r",\s*author\.?\s*$", "", raw_author)
    cleaned = re.sub(r"\s+author\.?\s*$", "", cleaned)
    return cleaned.strip()


def _extract_year(raw_date: str) -> str:
    if not raw_date:
        return ""
    match = re.search(r"\[?(\d{4})\]?", raw_date)
    if match:
        return match.group(1)
    return raw_date.strip()


def _parse_subjects(raw_subjects: str) -> list[str]:
    if not raw_subjects:
        return []
    parts = raw_subjects.split(";")
    categories = []
    for part in parts:
        cleaned = part.strip().rstrip(".")
        if cleaned:
            categories.append(cleaned)
    return categories


def _parse_isbn(raw_isbn: str) -> str:
    if not raw_isbn:
        return ""
    return raw_isbn.split(";")[0].strip()


def _clean_process_type(raw_type: str) -> str:
    if not raw_type or raw_type.strip() == "None":
        return "available"
    return raw_type.strip().lower()


def _generate_realistic_copies(status: str) -> tuple:
    if status == "available":
        total = random.randint(2, 10)
        available = random.randint(1, total)
    elif status == "borrowed":
        total = random.randint(2, 8)
        available = 0
    else:
        total = 0
        available = 0
    return total, available


def _generate_due_date(status: str) -> str | None:
    if status != "borrowed":
        return None
    days_ahead = random.randint(7, 45)
    due = date.today() + timedelta(days=days_ahead)
    return due.isoformat()


# ============================================
# CSV 数据加载器
# ============================================

_books_cache = None


def _get_csv_path(prefer_processed: bool = True):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    db_dir = os.path.join(project_root, "database")
    processed_path = os.path.join(db_dir, "processed_library_books.csv")
    raw_path = os.path.join(db_dir, "mock_library_books.csv")
    if prefer_processed and os.path.exists(processed_path):
        return processed_path, "processed"
    elif os.path.exists(raw_path):
        return raw_path, "raw"
    else:
        return raw_path, "not_found"


def _load_books_from_csv() -> list[dict]:
    global _books_cache
    if _books_cache is not None:
        return _books_cache
    csv_path, source_type = _get_csv_path()
    if source_type == "not_found":
        print(f"[WARN] CSV 文件不存在: {csv_path}")
        return []
    encoding = "utf-8" if source_type == "processed" else "gb18030"
    label = "processed_library_books.csv" if source_type == "processed" else "mock_library_books.csv"
    books = []
    with open(csv_path, "r", encoding=encoding) as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            books.append(_csv_row_to_book(row, idx))
    _books_cache = books
    print(f"[INFO] CSV 数据加载完成（来源: {label}），共 {len(books)} 本")
    return books


def _csv_row_to_book(row: dict, idx: int) -> dict:
    status = _clean_process_type(row.get("Process Type", "None"))
    total_copies, available_copies = _generate_realistic_copies(status)
    category = _parse_subjects(row.get("Subjects", ""))
    raw_category_cn = row.get("category_cn", "").strip()
    if raw_category_cn:
        cn_parts = [c.strip() for c in raw_category_cn.split(";") if c.strip()]
        for c in cn_parts:
            if c not in category:
                category.append(c)
    return {
        "id": f"BK{idx:03d}",
        "title": _clean_title(row.get("Title (Complete)", "")),
        "author": _clean_author(row.get("Author", "")),
        "isbn": _parse_isbn(row.get("ISBN", "")),
        "publisher": row.get("Publisher", "").strip(),
        "publish_year": _extract_year(row.get("Publication Date", "")),
        "category": category,
        "location": row.get("Location Name", "").strip(),
        "status": status,
        "due_date": _generate_due_date(status),
        "total_copies": total_copies,
        "available_copies": available_copies,
        "title_cn": row.get("title_cn", "").strip(),
        "category_cn": raw_category_cn,
    }


# ============================================
# 数据源路由
# ============================================

def _get_all_books() -> list[dict]:
    mode = DATA_SOURCE_MODE
    if mode == "CSV":
        return _load_books_from_csv()
    elif mode in ("DATABASE", "REAL_API"):
        print(f"[WARN] {mode} 模式尚未实现，回退为 CSV 模式")
        return _load_books_from_csv()
    else:
        print(f"[WARN] 未知模式 '{mode}'，回退为 CSV 模式")
        return _load_books_from_csv()


# ============================================
# 降级函数（AI 失败时全字段暴力搜索）
# ============================================

def _fallback_multi_field_search(books: list[dict], query: str) -> list[dict]:
    """安全降级：原始 query 对 5 个中英文字段暴力轰炸

    当 AI 调用完全失败时，直接拿用户输入在以下字段做模糊匹配：
      - title（英文原名）、title_cn（中文书名）
      - author（作者名）
      - category（Subjects 英文）、category_cn（中文分类标签）
      - ISBN（去连字符）
    确保演示永不挂科。
    """
    seen = set()
    results = []
    q_low = query.lower()
    isbn_clean = q_low.replace("-", "").replace(" ", "")
    for b in books:
        if b["id"] in seen:
            continue
        hit = False
        if q_low in b.get("title", "").lower():
            hit = True
        elif q_low in b.get("title_cn", "").lower():
            hit = True
        elif q_low in b.get("author", "").lower():
            hit = True
        elif any(q_low in c.lower() for c in b.get("category", [])):
            hit = True
        elif q_low in b.get("category_cn", "").lower():
            hit = True
        elif isbn_clean and isbn_clean in b.get("isbn", "").replace("-", "").replace(" ", "").lower():
            hit = True
        if hit:
            seen.add(b["id"])
            results.append(b)
    # 没搜到就拆词再试
    if not results:
        terms = _extract_search_terms(query)
        for t in terms:
            t_low = t.lower()
            t_isbn = t_low.replace("-", "").replace(" ", "")
            for b in books:
                if b["id"] in seen:
                    continue
                hit = False
                if t_low in b.get("title", "").lower():
                    hit = True
                elif t_low in b.get("title_cn", "").lower():
                    hit = True
                elif t_low in b.get("author", "").lower():
                    hit = True
                elif any(t_low in c.lower() for c in b.get("category", [])):
                    hit = True
                elif t_low in b.get("category_cn", "").lower():
                    hit = True
                elif t_isbn and t_isbn in b.get("isbn", "").replace("-", "").replace(" ", "").lower():
                    hit = True
                if hit:
                    seen.add(b["id"])
                    results.append(b)
    return results


# ============================================
# 对外接口（签名永不改变）
# ============================================

def search_books(keyword: str) -> list[dict]:
    """搜索图书馆馆藏图书（终极双轨检索）

    流程：
      1. AI 实时返回 {"subjects": [...], "specific_targets": [...]}
      2. 双轨匹配：
          轨道 ①（学科）：subjects → Subjects + category_cn
          轨道 ②（精准）：specific_targets → Title/title_cn/Author/ISBN
      3. 任意轨道命中即返回
      4. AI 失败 → 降级为原始关键词全字段暴力搜索

    Args:
        keyword: 自然语言描述（学科/情绪/作者/书名/ISBN 均可）

    Returns:
        匹配的图书列表（每本 14 字段），空列表表示无匹配
    """
    all_books = _get_all_books()

    # 空搜索：返回前 10 条热门推荐
    if not keyword or not keyword.strip():
        return all_books[:10]

    raw_query = keyword.strip()

    # ============================
    # 优先通道：AI 双轨搜索
    # ============================
    ai_result = _call_ai_intent_extraction(raw_query)
    if ai_result:
        ai_results = _ai_multi_track_search(all_books, ai_result)
        if ai_results:
            return ai_results
        print("[AI 多轨] AI 成功但未命中任何图书，进入降级搜索")

    # ============================
    # 降级通道：全字段暴力轰炸
    # ============================
    fallback_results = _fallback_multi_field_search(all_books, raw_query)
    print(f"[降级搜索] 原始关键词全字段轰炸 → {len(fallback_results)} 本")
    return fallback_results


def get_book_by_isbn(isbn: str) -> dict | None:
    """根据 ISBN 精确查询单本书（签名不变）

    Args:
        isbn: ISBN 号（如 "978-7-302-45679-1"）

    Returns:
        匹配的图书字典（14 字段），或 None
    """
    if not isbn or not isbn.strip():
        return None
    clean_target = isbn.strip().replace("-", "").replace(" ", "")
    all_books = _get_all_books()
    for book in all_books:
        book_isbn_clean = (
            book.get("isbn", "").replace("-", "").replace(" ", "")
        )
        if book_isbn_clean == clean_target:
            return book
    return None