"""
书搜搜 - 图书馆API封装（终极双轨检索 + 全字段轰炸）
===================================================

设计理念：
  用户输入可以是任何自然语言——情绪、作者、书名、学科、场景。
  AI 实时返回 JSON 混合武器库：
    - subjects: 中文学科关键词（宏观大网，捞取学科内所有书）
    - specific_targets: 特定书名/作者/ISBN（微观精准直达）

  后端两条轨道任意命中即算成功：
    - 轨道 ①（学科）：subjects → 匹配 category_cn(中文)
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
# 实时 AI 意图理解（情绪 → 中文学科关键词）
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

    Prompt 设计：
      AI 扮演图书检索专家，输出包含两个轨道的 JSON：
        - subjects: 中文学科关键词（宏观大网捞取）
        - specific_targets: 特定书名/作者/人物的中英文名（微观精准直达）
        - excluded_subjects: 用户想排除的学科

    Returns:
        {"subjects": ["心理学"], "specific_targets": [], "excluded_subjects": []}
        或 None（Key 为空/解析失败/超时 → 触发降级）
    """
    api_key = _get_api_key()
    if not api_key:
        print("[AI 意图] config.py 未配置 DEEPSEEK_API_KEY，跳过实时 AI")
        return None

    system_prompt = (
        "你是图书检索助手。你需要将用户的需求拆成三部分输出。\n\n"
        "请严格按以下JSON格式输出，不要带markdown标记：\n"
        '{"subjects": ["中文学科词"], "specific_targets": ["书名/作者名"], "excluded_subjects": ["排除的学科词"]}\n\n'
        "规则：\n"
        "1. subjects：用户提到的学科/类型，用中文学科词。最多2个。\n"
        "   可选学科词：人工智能、机器学习、深度学习、计算机、数据科学、编程、Python、算法、心理学、哲学、\n"
        "   历史、文学、小说、文化、语言、经济、法学、政治、医学、物理、化学、生物、数学、天文、\n"
        "   宗教、教育、艺术、军事、自然、绘本、传记、科幻、管理。\n"
        "   如果用户只表达了情绪（如心情不好、焦虑、无聊），没有指定学科，subjects 输出 []。\n"
        "2. specific_targets：用户明确提到的书名、作者名。中英文均可。没有则 []。\n"
        "3. excluded_subjects：用户说\"不想看/不要/排除\"的学科类型。没有则 []。\n\n"
        "示例：\n"
        '用户：我想看机器学习的书\n输出：{"subjects": ["机器学习"], "specific_targets": [], "excluded_subjects": []}\n'
        '用户：最近心情不好有点焦虑，想看本书缓缓\n输出：{"subjects": [], "specific_targets": [], "excluded_subjects": []}\n'
        '用户：想看村上春树的小说\n输出：{"subjects": ["文学", "小说"], "specific_targets": ["村上春树", "Murakami"], "excluded_subjects": []}\n'
        '用户：想看关于心理学的书，不要太枯燥的\n输出：{"subjects": ["心理学"], "specific_targets": [], "excluded_subjects": []}'
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
        excluded_subjects = parsed.get("excluded_subjects", [])

        if isinstance(subjects, list) and isinstance(specific_targets, list):
            # 过滤空字符串
            subjects = [s for s in subjects if s and s.strip()]
            specific_targets = [t for t in specific_targets if t and t.strip()]
            excluded_subjects = [e for e in excluded_subjects if e and e.strip()]
            print(f"[AI 意图] 用户输入\"{user_input}\" → "
                  f"subjects={subjects}, specific={specific_targets}, excluded={excluded_subjects}")
            return {"subjects": subjects, "specific_targets": specific_targets, "excluded_subjects": excluded_subjects}

        print(f"[AI 意图] JSON 字段类型异常: {content!r}")
        return None

    except Exception as e:
        print(f"[AI 意图] API 调用失败或 JSON 解析失败: {e}，进入降级直搜")
        return None


# ============================================
# 双层匹配算法
# ============================================

def _ai_multi_track_search(books: list[dict], ai_result: dict) -> list[dict]:
    """多轨全字段轰炸匹配：AI 返回的 subjects + specific_targets + excluded_subjects

    条件 ①（宏观学科）：subjects → 匹配 category_cn（中文）
    条件 ②（微观精准）：specific_targets → 匹配 Title / title_cn / Author / ISBN
    条件 ③（排除）：excluded_subjects → 匹配到的排除
    """
    subjects = [s.lower() for s in ai_result.get("subjects", []) if s and s.strip()]
    targets = [t.lower() for t in ai_result.get("specific_targets", []) if t and t.strip()]
    excluded = [e.lower() for e in ai_result.get("excluded_subjects", []) if e and e.strip()]

    if not subjects and not targets:
        return []

    matched = []
    for book in books:
        hit = False

        # 条件 ①：宏观学科匹配
        if subjects:
            cat_cn_lower = book.get("category_cn", "").lower()
            for s in subjects:
                if s in cat_cn_lower:
                    hit = True
                    break

        # 条件 ②：微观精准匹配
        if not hit and targets:
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

        # 条件 ③：排除匹配
        if hit and excluded:
            cat_cn_lower = book.get("category_cn", "").lower()
            for e in excluded:
                if e in cat_cn_lower:
                    hit = False
                    break

        if hit:
            matched.append(book)

    print(f"[AI 多轨] subjects={subjects} + targets={targets} + excluded={excluded} → {len(matched)} 本")
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
    """安全降级：原始 query 对 5 个中英文字段暴力轰炸"""
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
      1. AI 实时返回 {"subjects": [...], "specific_targets": [...], "excluded_subjects": [...]}
      2. 双轨匹配：
          轨道 ①（学科）：subjects → category_cn
          轨道 ②（精准）：specific_targets → Title/title_cn/Author/ISBN
          轨道 ③（排除）：excluded_subjects → 过滤
      3. AI 失败 → 降级为原始关键词全字段暴力搜索

    Args:
        keyword: 自然语言描述（学科/情绪/作者/书名/ISBN 均可）

    Returns:
        匹配的图书列表（空列表表示无匹配），最多返回 20 本
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
            # 情绪类搜索（无 subjects）时，取前 5 本学科相关
            if not ai_result.get("subjects"):
                return ai_results[:5]
            return ai_results

    # ============================
    # 降级通道：全字段暴力轰炸
    # ============================
    fallback_results = _fallback_multi_field_search(all_books, raw_query)
    print(f"[降级搜索] 原始关键词全字段轰炸 → {len(fallback_results)} 本")
    # 降级结果最多返回 20 本
    return fallback_results[:20]


def get_book_by_isbn(isbn: str) -> dict | None:
    """根据 ISBN 精确查询单本书"""
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