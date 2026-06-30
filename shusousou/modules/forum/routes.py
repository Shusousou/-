"""
书搜搜 - 论坛模块（终极升级版）
负责：发帖回帖、双源书评、热搜榜、点赞收藏、书评搜索、高光数据
"""

from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os

from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import Session as DBSession

from ...utils import get_current_user
from ...database.models import Post, Comment, Like, Star, CelebrityReview, User
from ..search.library_api import search_books

router = APIRouter(prefix="/forum", tags=["forum"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
forum_templates = os.path.join(BASE_DIR, "modules", "forum", "templates")
global_templates = os.path.join(BASE_DIR, "templates")

loader = ChoiceLoader([
    FileSystemLoader(forum_templates),
    FileSystemLoader(global_templates)
])
env = Environment(loader=loader, cache_size=0)
templates = Jinja2Templates(env=env)

CATEGORIES = ["计算机", "科幻", "文学", "其他"]
CATEGORIES_EN = ["Computer", "Sci-Fi", "Literature", "Other"]


def translate_category(cat: str, lang: str) -> str:
    """根据语言动态映射分类标签"""
    if not cat:
        return ""
    if lang == "zh":
        return cat
    mapping = {
        "计算机": "Computer",
        "科幻": "Sci-Fi",
        "文学": "Literature",
        "其他": "Other"
    }
    return mapping.get(cat, cat)


def get_db():
    db_path = os.path.join(BASE_DIR, "database", "database.db")
    db_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    return DBSession(db_engine)


def require_login(request: Request):
    """检查登录，API 模式返回用户或 None，页面模式请使用 require_login_page。"""
    return get_current_user(request)


def require_login_page(request: Request):
    """页面模式登录检查，未登录重定向到登录页。"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    return user


# ============================================
# 书籍高光数据（Mock 数据库）
# ============================================
BOOK_HIGHLIGHTS = {
    "9781594480003": {
        "author_preface": "我花了两年时间追随着风筝的脚步，才明白父亲眼中的愧疚与救赎。这是一个关于背叛与赎罪的故事，献给所有在黑暗中寻找光明的灵魂。",
        "brilliant_quotes": [
            "为你，千千万万遍。",
            "那儿有再次成为好人的路。",
            "时间很贪婪——有时候，它会独自吞噬所有的细节。",
            "被真相伤害总比被谎言欺骗好。",
            "得到了再失去，总是比从来就没有得到更伤人。"
        ]
    },
    "9787505715660": {
        "author_preface": "人是为活着本身而活着，而不是为了活着之外的任何事物所活着。我写的是一个农民和他那头老牛的故事，却看见了整个民族的缩影。",
        "brilliant_quotes": [
            "人是为了活着本身而活着，而不是为了活着之外的任何事物而活着。",
            "以笑的方式哭，在死亡的伴随下活着。",
            "没有什么比时间更具有说服力了。",
            "做人还是平常点好，争这个争那个，争来争去赔了自己的命。",
            "生活是属于每个人自己的感受，不属于任何别人的看法。"
        ]
    },
    "9787532769278": {
        "author_preface": "人的意志可以摧毁一切，只要有信念。老人与海的故事告诉我们：一个人可以被毁灭，但不能被打败。",
        "brilliant_quotes": [
            "一个人可以被毁灭，但不能被打败。",
            "生活总是让我们遍体鳞伤，但到后来，那些受伤的地方会变成我们最强壮的地方。",
            "现在不是去想缺少什么的时候，该想一想凭现有的东西你能做什么。",
            "每一天都是一个新的日子。走运当然是好的，不过我情愿做到分毫不差。",
            "在某种意义上，所有事物都在互相残杀。"
        ]
    },
    "9787544253994": {
        "author_preface": "我想讲述一个关于命运与选择的故事。在人生的分岔路口，每一次选择都通向截然不同的未来。",
        "brilliant_quotes": [
            "人生就像一盒巧克力，你永远不知道下一颗是什么味道。",
            "死亡是生命的一部分，是我们注定要做的事。",
            "你得丢开以往的事，才能不断继续前进。",
            "如果你相信自己，你就可以做任何事。",
            "我不懂我们是否有着各自的命运，还是只是到处随风飘荡。"
        ]
    },
    "9787020002207": {
        "author_preface": "我写的不是童话，而是一个关于爱、责任与孤独的寓言。每个大人都曾经是孩子，只是他们忘了。",
        "brilliant_quotes": [
            "只有用心才能看清，本质的东西是肉眼看不见的。",
            "正是你为玫瑰付出的时间，使你的玫瑰如此重要。",
            "所有的大人最初都是孩子（但很少有人记得）。",
            "如果你驯化了我，我们就彼此需要了。",
            "沙漠之所以美丽，是因为在某个地方藏着一口水井。"
        ]
    },
    "9787544291163": {
        "author_preface": "这是一个关于银行家越狱的故事，更是一个关于希望如何拯救一个人的故事。在肖申克，希望是穿墙而过的翅膀。",
        "brilliant_quotes": [
            "希望是美好的，也许是人间至善，而美好的事物永不消逝。",
            "有些鸟儿是关不住的，它们的羽毛太鲜亮了。",
            "恐惧让你沦为囚犯，希望让你重获自由。",
            "忙活，或者等死。",
            "地质学教会我：如果有足够的时间，水滴也能穿透石头。"
        ]
    }
}

DEFAULT_HIGHLIGHTS = {
    "author_preface": "这本书凝聚了作者多年的心血与思考，希望能为读者带来启发与感动。",
    "brilliant_quotes": [
        "书籍是人类进步的阶梯。",
        "读一本好书，就是和许多高尚的人谈话。",
        "生活里没有书籍，就好像没有阳光。",
        "读书破万卷，下笔如有神。",
        "知识就是力量。"
    ]
}


# ============================================
# 名人书评数据源（模拟）
# ============================================
CELEBRITY_REVIEWS_MOCK = [
    {"isbn": "9781594480003", "reviewer_name": "奥巴马", "reviewer_title": "美国前总统", "content": "这是一个关于救赎与勇气的故事。", "rating": 5, "source": "Goodreads"},
]

# ============================================
# 名人书评数据源（模拟）
# ============================================
CELEBRITY_REVIEWS_MOCK = [
    {"isbn": "9781594480003", "reviewer_name": "奥巴马", "reviewer_title": "美国前总统", "content": "这是一个关于救赎与勇气的动人故事。阿米尔的旅程让我们看到，承认自己的软弱才是真正的强大。这本书让我重新思考了父与子之间的复杂情感。", "rating": 5, "source": "Goodreads"},
    {"isbn": "9781594480003", "reviewer_name": "村上春树", "reviewer_title": "小说家", "content": "胡赛尼用细腻的笔触描绘了阿富汗战乱背景下的人性光辉。风筝的意象贯穿全篇，既是自由的象征，也是无法逃脱的宿命。", "rating": 5, "source": "文学杂志"},
    {"isbn": "9781594480003", "reviewer_name": "周国平", "reviewer_title": "哲学家", "content": "每个人心中都有一只想要追回的风筝。这本书最打动我的不是故事情节，而是那种深刻的人性剖析——关于背叛、愧疚与最终的自我救赎。", "rating": 4, "source": "豆瓣读书"},
    {"isbn": "9787505715660", "reviewer_name": "莫言", "reviewer_title": "诺贝尔文学奖得主", "content": "余华用最朴素的文字写出了最震撼的生命力。《活着》讲述的不是苦难，而是在苦难中如何有尊严地活着。这本书是中国文学的瑰宝。", "rating": 5, "source": "文学评论"},
    {"isbn": "9787505715660", "reviewer_name": "白岩松", "reviewer_title": "主持人", "content": "我看完《活着》后沉默了整整一个下午。余华教会我们：生命的韧性远超我们的想象。福贵的一生是悲剧，但他从未放弃做人的尊严。", "rating": 5, "source": "央视"},
    {"isbn": "9787505715660", "reviewer_name": "村上春树", "reviewer_title": "小说家", "content": "余华是一位令人敬畏的作家。《活着》用平静的叙述包裹着巨大的悲剧力量，这种反差恰恰是中国文学最独特的魅力所在。", "rating": 5, "source": "纽约时报"},
    {"isbn": "9787532769278", "reviewer_name": "海明威", "reviewer_title": "诺贝尔文学奖得主（自评）", "content": "这是我一生中写得最好的一本书。老人圣地亚哥就是我自己的写照——即使被生活打败，也要保持优雅与尊严。", "rating": 5, "source": "巴黎评论"},
    {"isbn": "9787532769278", "reviewer_name": "王小波", "reviewer_title": "作家", "content": "海明威的《老人与海》是一种英雄主义的极致表达。老人与鲨鱼的搏斗，是人类不屈精神的伟大寓言。简洁的文体下蕴藏着惊人的力量。", "rating": 5, "source": "我的精神家园"},
    {"isbn": "9787544253994", "reviewer_name": "比尔·盖茨", "reviewer_title": "微软创始人", "content": "阿甘的故事告诉我们：成功不在于智商高低，而在于坚持和善良。每次重读都能获得新的力量。", "rating": 4, "source": "博客"},
    {"isbn": "9787020002207", "reviewer_name": "周国平", "reviewer_title": "哲学家", "content": "《小王子》是写给成年人的童话。圣埃克苏佩里用最简单的语言，说出了最深刻的真理。每次读都有新的感悟。", "rating": 5, "source": "豆瓣"},
    {"isbn": "9787020002207", "reviewer_name": "刘瑜", "reviewer_title": "学者", "content": "小时候读小王子觉得是童话，长大后再读发现是哲学。那朵玫瑰、那只狐狸、那些星球上的人，都在映照我们自己的生活。", "rating": 4, "source": "知乎"},
    {"isbn": "9787544291163", "reviewer_name": "史蒂芬·金", "reviewer_title": "恐怖小说大师", "content": "这是我写过的最不恐怖的故事，但却是最充满希望的故事。安迪·杜弗兰用二十年的时间告诉我们：希望是穿墙而过的翅膀。", "rating": 5, "source": "作家自述"},
    {"isbn": "9787544291163", "reviewer_name": "李开复", "reviewer_title": "创新工场CEO", "content": "在我人生最困难的时候，是《肖申克的救赎》给了我力量。安迪在监狱里挖了十九年的隧道，让我相信：只要不放弃，总有重获自由的一天。", "rating": 5, "source": "个人博客"},
]


# ============================================
# 1. 书籍热度排行榜（热搜书单）
# ============================================
# ============================================
# 1. 书籍热度排行榜（热搜书单）
# ============================================
@router.get("/api/trending")
async def get_trending_books(request: Request):
    # 🌟 核心修改点 1：从 Cookie 中获取当前语言
    lang = request.cookies.get("language", "zh")
    
    with get_db() as session:
        post_counts = session.query(
            Post.isbn, func.count(Post.id).label("cnt")
        ).filter(
            Post.isbn.isnot(None), Post.isbn != ""
        ).group_by(Post.isbn).subquery()

        celeb_counts = session.query(
            CelebrityReview.isbn, func.count(CelebrityReview.id).label("cnt")
        ).group_by(CelebrityReview.isbn).subquery()

        trending = session.query(
            post_counts.c.isbn,
            (func.coalesce(post_counts.c.cnt, 0) + func.coalesce(celeb_counts.c.cnt, 0)).label("total_cnt"),
            func.coalesce(post_counts.c.cnt, 0).label("user_cnt"),
            func.coalesce(celeb_counts.c.cnt, 0).label("celebrity_cnt")
        ).outerjoin(
            celeb_counts, post_counts.c.isbn == celeb_counts.c.isbn
        ).order_by(desc("total_cnt")).limit(10).all()

        if len(trending) < 10:
            existing_isbns = [t[0] for t in trending if t[0]]
            if existing_isbns:
                missing = session.query(
                    CelebrityReview.isbn, func.count(CelebrityReview.id).label("cnt")
                ).filter(~CelebrityReview.isbn.in_(existing_isbns)).group_by(CelebrityReview.isbn).order_by(desc("cnt")).limit(10 - len(trending)).all()
            else:
                missing = []
            for m in missing:
                trending.append((m[0], m[1], 0, m[1]))

        result = []
        for rank, (isbn, total_cnt, user_cnt, celeb_cnt) in enumerate(trending, 1):
            if not isbn:
                continue
            lib_info = None
            lib_results = search_books(isbn)
            if lib_results:
                lib = lib_results[0]
                lib_info = {"title_cn": lib.get("title_cn",""), "title": lib.get("title",""), "author": lib.get("author",""), "isbn": lib.get("isbn","")}
            sample_post = session.query(Post).filter(Post.isbn == isbn).order_by(Post.created_at.desc()).first()
            
            # 🌟 核心修改点 2：如果是英文环境且拥有英文书名，则优先使用英文名
            if lang == "en" and lib_info and lib_info.get("title"):
                book_name = lib_info["title"]
            else:
                book_name = lib_info["title_cn"] if lib_info and lib_info["title_cn"] else (sample_post.book_name if sample_post else isbn)
                
            book_author = lib_info["author"] if lib_info and lib_info["author"] else (sample_post.author if sample_post else "")

            result.append({
                "rank": rank, "isbn": isbn,
                "book_name": book_name, "author": book_author,
                "total_reviews": total_cnt,
                "user_review_count": user_cnt,
                "celebrity_review_count": celeb_cnt,
            })

        return JSONResponse({"success": True, "trending": result})
# ============================================
# 2. 书评搜索
# ============================================
@router.get("/api/search-reviews")
async def search_reviews(request: Request, q: str = Query("", description="搜索关键词")):
    lang = request.cookies.get("language", "zh")
    if not q or not q.strip():
        return JSONResponse({"success": True, "results": []})

    with get_db() as session:
        posts = session.query(Post).filter(
            (Post.book_name.contains(q)) |
            (Post.author.contains(q)) |
            (Post.content.contains(q))
        ).order_by(Post.created_at.desc()).limit(50).all()

        results = []
        for p in posts:
            comment_count = session.query(Comment).filter(Comment.post_id == p.id).count()
            results.append({
                "id": p.id, "book_name": p.book_name,
                "author": p.author or "",
                "content": p.content[:150] + ("..." if len(p.content) > 150 else ""),
                "isbn": p.isbn or "", "review_type": p.review_type or "user",
                "username": p.user.username if p.user else ("匿名" if lang == "zh" else "Anonymous"),
                "category": translate_category(p.category, lang),
                "comment_count": comment_count,
                "likes_count": p.likes_count or 0,
                "stars_count": p.stars_count or 0,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""
            })
        return JSONResponse({"success": True, "results": results})


# ============================================
# 3. 点赞/收藏 Toggle API
# ============================================
@router.post("/api/{post_id}/like")
async def toggle_like(request: Request, post_id: int):
    current_user = require_login(request)
    if not current_user:
        return JSONResponse({"success": False, "error": "请先登录"}, status_code=401)
    with get_db() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            return JSONResponse({"success": False, "error": "帖子不存在"}, status_code=404)
        existing = session.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first()
        if existing:
            session.delete(existing)
            post.likes_count = max(0, (post.likes_count or 0) - 1)
            liked = False
        else:
            session.add(Like(post_id=post_id, user_id=current_user.id))
            post.likes_count = (post.likes_count or 0) + 1
            liked = True
        session.commit()
        return JSONResponse({"success": True, "liked": liked, "likes_count": post.likes_count})


@router.post("/api/{post_id}/star")
async def toggle_star(request: Request, post_id: int):
    current_user = require_login(request)
    if not current_user:
        return JSONResponse({"success": False, "error": "请先登录"}, status_code=401)
    with get_db() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            return JSONResponse({"success": False, "error": "帖子不存在"}, status_code=404)
        existing = session.query(Star).filter(Star.post_id == post_id, Star.user_id == current_user.id).first()
        if existing:
            session.delete(existing)
            post.stars_count = max(0, (post.stars_count or 0) - 1)
            starred = False
        else:
            session.add(Star(post_id=post_id, user_id=current_user.id))
            post.stars_count = (post.stars_count or 0) + 1
            starred = True
        session.commit()
        return JSONResponse({"success": True, "starred": starred, "stars_count": post.stars_count})


# ============================================
# 4. 双源书评（用户 + 名人）
# ============================================
@router.get("/api/reviews/{isbn}")
async def get_book_reviews(request: Request, isbn: str):
    lang = request.cookies.get("language", "zh")
    clean_isbn = isbn.strip().replace("-", "").replace(" ", "")
    with get_db() as session:
        user_posts = session.query(Post).filter(
            Post.isbn == clean_isbn, Post.review_type == "user"
        ).order_by(Post.created_at.desc()).all()

        user_reviews = []
        for p in user_posts:
            comment_count = session.query(Comment).filter(Comment.post_id == p.id).count()
            user_reviews.append({
                "id": p.id, "content": p.content,
                "username": p.user.username if p.user else ("匿名" if lang == "zh" else "Anonymous"),
                "user_id": p.user_id,
                "likes_count": p.likes_count or 0,
                "stars_count": p.stars_count or 0,
                "comment_count": comment_count,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else ""
            })

        celeb_db = session.query(CelebrityReview).filter(CelebrityReview.isbn == clean_isbn).order_by(CelebrityReview.created_at.desc()).all()
        celebrity_reviews = []
        for c in celeb_db:
            celebrity_reviews.append({
                "id": c.id, "reviewer_name": c.reviewer_name,
                "reviewer_title": c.reviewer_title or "",
                "content": c.content, "rating": c.rating,
                "source": c.source or "",
                "created_at": c.created_at.strftime("%Y-%m-%d") if c.created_at else ""
            })

        if not celebrity_reviews:
            for mock in CELEBRITY_REVIEWS_MOCK:
                mid = mock["isbn"].replace("-", "").replace(" ", "")
                if mid == clean_isbn:
                    celebrity_reviews.append({
                        "id": -1, "reviewer_name": mock["reviewer_name"],
                        "reviewer_title": mock["reviewer_title"],
                        "content": mock["content"], "rating": mock["rating"],
                        "source": mock["source"], "created_at": ""
                    })

        lib_info = None
        lib_results = search_books(clean_isbn)
        if lib_results:
            lib = lib_results[0]
            lib_info = {"title_cn": lib.get("title_cn",""), "title": lib.get("title",""), "author": lib.get("author",""), "isbn": lib.get("isbn","")}
        else:
            fp = session.query(Post).filter(Post.isbn == clean_isbn).first()
            if fp:
                lib_info = {"title_cn": fp.book_name, "title": "", "author": fp.author or "", "isbn": clean_isbn}

        return JSONResponse({
            "success": True, "book": lib_info,
            "user_reviews": user_reviews, "celebrity_reviews": celebrity_reviews,
            "total_user": len(user_reviews), "total_celebrity": len(celebrity_reviews)
        })


# ============================================
# 5. 书籍高光数据
# ============================================
@router.get("/api/highlights/{isbn}")
async def get_book_highlights(request: Request, isbn: str):
    clean_isbn = isbn.strip().replace("-", "").replace(" ", "")
    highlights = BOOK_HIGHLIGHTS.get(clean_isbn, DEFAULT_HIGHLIGHTS)

    lib_info = None
    lib_results = search_books(clean_isbn)
    if lib_results:
        lib = lib_results[0]
        lib_info = {"title_cn": lib.get("title_cn",""), "title": lib.get("title",""), "author": lib.get("author",""), "isbn": lib.get("isbn","")}

    return JSONResponse({
        "success": True, "book": lib_info,
        "author_preface": highlights["author_preface"],
        "brilliant_quotes": highlights["brilliant_quotes"]
    })


# ============================================
# 批量用户状态
# ============================================
@router.get("/api/user-status")
async def get_user_post_status(request: Request, post_ids: str = Query("")):
    current_user = require_login(request)
    if not current_user:
        return JSONResponse({"success": False, "error": "未登录"}, status_code=401)
    ids = [int(i) for i in post_ids.split(",") if i.strip().isdigit()]
    if not ids:
        return JSONResponse({"success": True, "status": {}})
    with get_db() as session:
        liked_ids = {l.post_id for l in session.query(Like).filter(Like.post_id.in_(ids), Like.user_id == current_user.id).all()}
        starred_ids = {s.post_id for s in session.query(Star).filter(Star.post_id.in_(ids), Star.user_id == current_user.id).all()}
        status = {str(pid): {"liked": pid in liked_ids, "starred": pid in starred_ids} for pid in ids}
        return JSONResponse({"success": True, "status": status})


# ============================================
# 论坛首页 - 帖子列表
# ============================================
@router.get("/", response_class=HTMLResponse)
async def forum_index(request: Request):
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    lang = request.cookies.get("language", "zh")
    category = request.query_params.get("category", "")
    search_q = request.query_params.get("q", "")

    with get_db() as session:
        query = session.query(Post).order_by(Post.created_at.desc())
        if category:
            query = query.filter(Post.category == category)
        if search_q:
            query = query.filter(
                (Post.book_name.contains(search_q)) |
                (Post.content.contains(search_q)) |
                (Post.author.contains(search_q)) |
                (Post.isbn.contains(search_q))
            )
        posts = query.all()

        post_list = []
        post_ids = []
        for p in posts:
            post_ids.append(p.id)
            comment_count = session.query(Comment).filter(Comment.post_id == p.id).count()
            lib_info = None
            lib_results = search_books(p.book_name)
            if lib_results:
                lib = lib_results[0]
                lib_info = {"status": lib["status"], "location": lib.get("location",""), "due_date": lib.get("due_date")}
            post_list.append({
                "id": p.id, "book_name": p.book_name, "author": p.author or "",
                "content": p.content[:100] + ("..." if len(p.content) > 100 else ""),
                "category": translate_category(p.category or "", lang),
                "isbn": p.isbn or "",
                "review_type": p.review_type or "user",
                "username": p.user.username if p.user else ("匿名" if lang == "zh" else "Anonymous"),
                "user_id": p.user_id,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
                "comment_count": comment_count,
                "likes_count": p.likes_count or 0,
                "stars_count": p.stars_count or 0,
                "library": lib_info
            })

        user_liked_ids = set()
        user_starred_ids = set()
        if current_user and post_ids:
            user_liked_ids = {l.post_id for l in session.query(Like).filter(Like.post_id.in_(post_ids), Like.user_id == current_user.id).all()}
            user_starred_ids = {s.post_id for s in session.query(Star).filter(Star.post_id.in_(post_ids), Star.user_id == current_user.id).all()}
        for p in post_list:
            p["liked"] = p["id"] in user_liked_ids
            p["starred"] = p["id"] in user_starred_ids

    cats = CATEGORIES_EN if lang == "en" else CATEGORIES
    return templates.TemplateResponse(request, "forum_index.html", {
        "language": lang, "current_user": current_user, "posts": post_list,
        "categories": cats, "current_category": category, "search_q": search_q
    })


# ============================================
# 发帖
# ============================================
@router.get("/new", response_class=HTMLResponse)
async def new_post_page(request: Request):
    current_user = require_login_page(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    lang = request.cookies.get("language", "zh")
    cats = CATEGORIES_EN if lang == "en" else CATEGORIES
    return templates.TemplateResponse(request, "new_post.html", {
        "language": lang, "current_user": current_user, "categories": cats
    })


@router.post("/new")
async def new_post(request: Request, book_name: str = Form(...), author: str = Form(""),
                   isbn: str = Form(""), category: str = Form(""), content: str = Form(...)):
    current_user = require_login_page(request)
    if isinstance(current_user, RedirectResponse):
        return current_user

    isbn_value = isbn.strip().replace("-", "").replace(" ", "") if isbn else ""
    with get_db() as session:
        post = Post(user_id=current_user.id, book_name=book_name, author=author,
                    isbn=isbn_value,
                    category=category, content=content, review_type="user")
        session.add(post)
        session.commit()
        post_id = post.id
    return RedirectResponse(url=f"/forum/{post_id}", status_code=303)


# ============================================
# 帖子详情
# ============================================
@router.get("/{post_id}", response_class=HTMLResponse)
async def post_detail(request: Request, post_id: int):
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    lang = request.cookies.get("language", "zh")

    with get_db() as session:
        post = session.query(Post).filter(Post.id == post_id).first()
        if not post:
            return HTMLResponse("帖子不存在" if lang == "zh" else "Post not found", status_code=404)

        post_data = {
            "id": post.id, "book_name": post.book_name, "author": post.author or "",
            "content": post.content, "category": translate_category(post.category or "", lang), "isbn": post.isbn or "",
            "review_type": post.review_type or "user",
            "username": post.user.username if post.user else ("匿名" if lang == "zh" else "Anonymous"),
            "user_id": post.user_id,
            "created_at": post.created_at.strftime("%Y-%m-%d %H:%M") if post.created_at else "",
            "likes_count": post.likes_count or 0,
            "stars_count": post.stars_count or 0,
        }

        lib_info = None
        lib_results = search_books(post.book_name)
        if lib_results:
            lib = lib_results[0]
            lib_info = {"status": lib["status"], "location": lib.get("location",""), "due_date": lib.get("due_date")}

        comments = session.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()
        comment_list = []
        for c in comments:
            comment_list.append({
                "id": c.id, "content": c.content,
                "username": c.user.username if c.user else ("匿名" if lang == "zh" else "Anonymous"),
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
            })

        liked = starred = False
        if current_user:
            liked = session.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first() is not None
            starred = session.query(Star).filter(Star.post_id == post_id, Star.user_id == current_user.id).first() is not None

    return templates.TemplateResponse(request, "post_detail.html", {
        "language": lang, "current_user": current_user, "post": post_data,
        "library": lib_info, "comments": comment_list,
        "liked": liked, "starred": starred
    })


# ============================================
# 回复帖子
# ============================================
@router.post("/{post_id}/comment")
async def add_comment(request: Request, post_id: int, content: str = Form(...)):
    login_check = require_login(request)
    if isinstance(login_check, RedirectResponse):
        return login_check
    current_user = login_check
    with get_db() as session:
        comment = Comment(post_id=post_id, user_id=current_user.id, content=content)
        session.add(comment)
        session.commit()
        try:
            post = session.query(Post).filter(Post.id == post_id).first()
            author = session.query(User).filter(User.id == post.user_id).first()
            if author and author.email and author.id != current_user.id:
                from ...mailer import send_forum_comment_notification
                send_forum_comment_notification(
                    to_email=author.email, receiver_name=author.username,
                    sender_name=current_user.username, book_name=post.book_name,
                    comment_content=content,
                    post_url="http://localhost:8000/forum/" + str(post_id))
        except Exception as e:
            print("[Mail]", "send_forum_comment_notification", e)
    return RedirectResponse(url="/forum/" + str(post_id), status_code=303)


# ============================================
# 旧版兼容：页面式点赞
# ============================================
@router.post("/{post_id}/like")
async def toggle_like_legacy(request: Request, post_id: int):
    result = await toggle_like(request, post_id)
    return RedirectResponse(url="/forum/" + str(post_id), status_code=303)


# ============================================
# 旧版兼容：页面式收藏
# ============================================
@router.post("/{post_id}/star")
async def toggle_star_legacy(request: Request, post_id: int):
    result = await toggle_star(request, post_id)
    return RedirectResponse(url="/forum/" + str(post_id), status_code=303)