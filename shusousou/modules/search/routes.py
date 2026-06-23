"""
书搜搜 - 搜索模块
负责：搜索页面、AI推荐、结果展示、多轮追问
"""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import re

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from ...database.models import User, engine
from .library_api import search_books, _call_ai_intent_extraction

router = APIRouter(prefix="/search", tags=["search"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
search_templates = os.path.join(BASE_DIR, "modules", "search", "templates")
global_templates = os.path.join(BASE_DIR, "templates")

loader = ChoiceLoader([
    FileSystemLoader(search_templates),
    FileSystemLoader(global_templates)
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)


from ...utils import get_current_user

# ============================================
# 搜索上下文管理
# ============================================
_search_contexts: dict = {}


def get_search_context(user_id: str) -> dict:
    if user_id not in _search_contexts:
        _search_contexts[user_id] = {
            "history": [],
            "subjects": [],
            "last_query": "",
            "last_results": [],
        }
    return _search_contexts[user_id]


def reset_context(user_id: str):
    _search_contexts[user_id] = {
        "history": [],
        "subjects": [],
        "last_query": "",
        "last_results": [],
    }


# ============================================
# AI 推荐阅读顺序（带推荐原因）
# ============================================
def ai_recommend_reading_order(books: list[dict]) -> list[tuple[int, str]]:
    if not books:
        return []

    book_list = "\n".join([
        f"{i+1}. 《{b.get('title_cn') or b['title']}》 - {b['author']}"
        for i, b in enumerate(books)
    ])

    prompt = (
        "你是一位阅读导师。请为以下图书推荐一个合理的阅读顺序，"
        "考虑从入门到深入、从基础到进阶的逻辑。\n\n"
        f"图书列表：\n{book_list}\n\n"
        "请输出一个 JSON 数组，每个元素包含 index（图书序号）和 reason（推荐原因，一句话中文说明为什么这个顺序）。\n"
        '格式：[{"index": 3, "reason": "作为入门读物先建立基础概念"}, {"index": 1, "reason": "在入门后深入学习"}, ...]\n'
        "按推荐阅读顺序从先到后排列，只输出 JSON，不要任何其他内容。"
    )

    try:
        import requests
        from shusousou.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
        if not DEEPSEEK_API_KEY:
            return [(i, "") for i in range(len(books))]
        response = requests.post(
            url=DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000
            },
            timeout=10
        )
        content = response.json()["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        import json as _json
        order_data = _json.loads(content)
        if isinstance(order_data, list):
            result = []
            for item in order_data:
                idx = item.get("index", 0)
                reason = item.get("reason", "")
                if 1 <= idx <= len(books):
                    result.append((idx - 1, reason))
            if result:
                return result
    except Exception as e:
        print(f"[阅读顺序] AI 调用失败: {e}")

    return [(i, "") for i in range(len(books))]


# ============================================
# 搜索页面
# ============================================
@router.get("/", response_class=HTMLResponse)
async def search_page(request: Request):
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    user_key = str(getattr(current_user, "id", "anonymous"))
    reset_context(user_key)

    return templates.TemplateResponse(request, "search.html", {
        "language": lang, "current_user": current_user,
        "results": None, "query": "", "history": [],
        "suggestions": [], "show_count": 0, "has_more": False,
        "fallback_books": [],
        "reading_order_results": None,
    })


@router.post("/", response_class=HTMLResponse)
async def search(
    request: Request,
    query: str = Form(...),
    mode: str = Form("auto")
):
    lang = request.cookies.get("language", "zh")
    current_user = get_current_user(request)
    user_key = str(getattr(current_user, "id", "anonymous"))

    if not query.strip():
        msg = "请输入你想看的书" if lang == "zh" else "Please enter what you want to read"
        return templates.TemplateResponse(request, "search.html", {
            "language": lang, "current_user": current_user,
            "results": [], "query": query, "error": msg,
            "history": [], "suggestions": [],
            "show_count": 0, "has_more": False,
            "fallback_books": [], "reading_order_results": None,
        })

    ctx = get_search_context(user_key)

    if mode == "new":
        reset_context(user_key)
        ctx = get_search_context(user_key)
        lib_books = search_books(query)
        ctx["last_query"] = query
        ctx["last_results"] = lib_books
        ctx["history"] = [{"role": "user", "content": query}]

    elif mode == "reading_order":
        if ctx["last_results"]:
            order_with_reasons = ai_recommend_reading_order(ctx["last_results"])
            ordered_results = []
            for idx, reason in order_with_reasons:
                if idx < len(ctx["last_results"]):
                    book = dict(ctx["last_results"][idx])
                    book["reading_reason"] = reason
                    ordered_results.append(book)
            lib_books = ordered_results
            ctx["history"].append({"role": "user", "content": "📋 帮我推荐一下阅读顺序"})
        else:
            empty_msg = "请先搜索一些书籍，再点击推荐阅读顺序"
            ctx["history"].append({"role": "assistant", "content": empty_msg, "results": []})
            return templates.TemplateResponse(request, "search.html", {
                "language": lang, "current_user": current_user,
                "results": [], "query": query, "error": empty_msg,
                "history": ctx["history"], "suggestions": [],
                "show_count": 0, "has_more": False,
                "fallback_books": [], "reading_order_results": None,
            })

    elif mode == "followup":
        prev_books = ctx.get("last_results", [])
        if prev_books:
            # === 提取排除关键词（不要/不想/不想看/不看/排除） ===
            exclude_keywords = []
            exclude_patterns = ["不想看", "不想", "不要", "不看", "排除"]
            processed_query = query
            for pat in exclude_patterns:
                if pat in processed_query:
                    parts = processed_query.split(pat, 1)
                    after = parts[1].strip()
                    # 提取排除词（第一个2字以上的中文词）
                    ex_match = re.search(r'([\u4e00-\u9fff]{2,})', after)
                    if ex_match:
                        exclude_keywords.append(ex_match.group(1))
                    processed_query = parts[0]

            # === 提取正关键词（去掉停用词） ===
            narrow_query = processed_query
            for stop_word in ["再", "帮我", "看看", "相关的", "的", "还", "要", "想", "看", "书", "推荐", "给我", "跟"]:
                narrow_query = narrow_query.replace(stop_word, " ")
            keywords = [w.strip() for w in narrow_query.split() if len(w.strip()) > 1]

            # === 在上一轮结果中筛选 ===
            filtered = []
            if keywords or exclude_keywords:
                for b in prev_books:
                    cat_cn = b.get("category_cn", "").lower()
                    title_cn = b.get("title_cn", "").lower()
                    title = b.get("title", "").lower()
                    author = b.get("author", "").lower()

                    # 正匹配：有正关键词时，至少匹配一个
                    matched = True
                    if keywords:
                        matched = False
                        for kw in keywords:
                            kw_low = kw.lower()
                            if kw_low in cat_cn or kw_low in title_cn or kw_low in title or kw_low in author:
                                matched = True
                                break

                    # 排除：匹配排除词则剔除
                    if matched and exclude_keywords:
                        for ex in exclude_keywords:
                            ex_low = ex.lower()
                            if ex_low in cat_cn or ex_low in title_cn or ex_low in title or ex_low in author:
                                matched = False
                                break

                    if matched:
                        filtered.append(b)

                if not filtered and keywords:
                    empty_msg = "当前结果中没有找到更相关的书籍，试试其他搜索方向？"
                    ctx["history"].append({"role": "assistant", "content": empty_msg, "results": []})
                    # 保留历史 show_count，避免之前的书籍被隐藏
                    prev_show = min(5, len(ctx["history"][-2]["results"])) if len(ctx["history"]) >= 2 and ctx["history"][-2].get("results") else 5
                    return templates.TemplateResponse(request, "search.html", {
                        "language": lang, "current_user": current_user,
                        "results": [], "query": query, "error": empty_msg,
                        "history": ctx["history"], "suggestions": [],
                        "show_count": prev_show, "has_more": False,
                        "fallback_books": [], "reading_order_results": None,
                    })

                lib_books = filtered if keywords else [b for b in prev_books if b not in [x for x in prev_books if any(
                    ex.lower() in b.get("category_cn", "").lower() or ex.lower() in b.get("title_cn", "").lower()
                    for ex in exclude_keywords
                )]]
            else:
                lib_books = prev_books
        else:
            lib_books = search_books(query)
        ctx["history"].append({"role": "user", "content": f"🔍 {query}"})

    else:
        if ctx["last_query"]:
            reset_context(user_key)
            ctx = get_search_context(user_key)
        lib_books = search_books(query)
        ctx["last_query"] = query
        ctx["last_results"] = lib_books
        ctx["history"].append({"role": "user", "content": query})

    # 保存结果到上下文
    if mode != "reading_order":
        ctx["last_results"] = lib_books

    # === 提取建议缩小分类 ===
    suggestions = []
    if lib_books:
        from collections import Counter
        cat_counter = Counter()
        for b in lib_books:
            cc = b.get("category_cn", "").lower()
            if cc:
                for c in cc.split(";"):
                    c = c.strip()
                    if c and len(c) <= 10:
                        cat_counter[c] += 1
        top_cats = [c for c, _ in cat_counter.most_common(5) if _ >= 2]
        ctx["subjects"] = list(set(ctx["subjects"] + top_cats))
        suggestions = top_cats[:3]

    # === 无结果处理 ===
    fallback_books = []
    if not lib_books:
        fallback_books = search_books("人工智能 Python 心理学 文学 历史")[:5]
        if fallback_books:
            fb_results = []
            for fb in fallback_books:
                fb_results.append({
                    "title": fb["title"], "title_cn": fb.get("title_cn", ""),
                    "author": fb["author"], "isbn": fb["isbn"],
                    "library_status": fb["status"], "library_location": fb.get("location", ""),
                    "library_due_date": fb.get("due_date"), "relevance": 0,
                })
            empty_msg = f"图书馆暂时没有找到「{query}」相关的书，不过你可以看看这些热门书籍："
            ctx["history"].append({"role": "assistant", "content": empty_msg, "results": []})
            return templates.TemplateResponse(request, "search.html", {
                "language": lang, "current_user": current_user,
                "results": [], "query": query, "error": empty_msg,
                "history": ctx["history"], "suggestions": ["计算机", "心理学", "文学", "人工智能", "历史"],
                "show_count": 5, "has_more": False,
                "fallback_books": fb_results, "reading_order_results": None,
            })
        else:
            empty_msg = "图书馆目前没有相关书籍，你还想看看其他类型的吗？"
            ctx["history"].append({"role": "assistant", "content": empty_msg, "results": []})
            return templates.TemplateResponse(request, "search.html", {
                "language": lang, "current_user": current_user,
                "results": [], "query": query, "error": empty_msg,
                "history": ctx["history"], "suggestions": ["计算机", "心理学", "文学", "人工智能", "历史"],
                "show_count": 5, "has_more": False,
                "fallback_books": [], "reading_order_results": None,
            })

    # === 组装结果 ===
    sort_query = query
    if mode == "followup":
        for stop_word in ["再", "帮我", "看看", "相关的", "的", "还", "要", "不要", "想", "看", "书"]:
            sort_query = sort_query.replace(stop_word, " ")
        sort_query = sort_query.strip()

    results = []
    for lib_book in lib_books[:20]:
        score = 0
        query_lower = sort_query.lower()
        cat_cn = lib_book.get("category_cn", "").lower()
        title_cn = lib_book.get("title_cn", "").lower()
        title = lib_book.get("title", "").lower()
        author = lib_book.get("author", "").lower()
        if query_lower in cat_cn: score += 10
        if query_lower in title_cn: score += 5
        if query_lower in title: score += 3
        if query_lower in author: score += 2
        if score == 0 and len(query_lower) > 2:
            for word in query_lower.split():
                if len(word) > 1:
                    if word in cat_cn: score += 4
                    if word in title_cn: score += 2
        r = {
            "title": lib_book["title"], "title_cn": lib_book.get("title_cn", ""),
            "author": lib_book["author"], "isbn": lib_book["isbn"],
            "reason": "", "detail": "",
            "library_status": lib_book["status"], "library_location": lib_book.get("location", ""),
            "library_due_date": lib_book.get("due_date"),
            "forum_posts": [], "exchange_books": [], "relevance": score,
            "reading_reason": lib_book.get("reading_reason", ""),
        }
        results.append(r)

    results.sort(key=lambda x: -x["relevance"])

    show_count = min(5, len(results))
    has_more = len(results) > 5

    # === 对话回复 ===
    if mode == "reading_order":
        reply = "根据这些书的内容深度和相关度，我建议按以下顺序阅读："
    else:
        reply = f"帮你找到了 **{len(results)} 本** 相关的书，先看这 {show_count} 本："
    ctx["history"].append({"role": "assistant", "content": reply, "results": results})

    return templates.TemplateResponse(request, "search.html", {
        "language": lang, "current_user": current_user,
        "results": results, "query": query,
        "history": ctx["history"], "suggestions": suggestions,
        "show_count": show_count, "has_more": has_more,
        "fallback_books": [], "reading_order_results": None,
    })