/* 书搜搜 - 前端交互脚本 */

// 页面加载完成后执行
document.addEventListener("DOMContentLoaded", function() {
    bindForumActions();
    loadTrendingBooks();
});

function bindForumActions() {
    document.querySelectorAll("[data-action='like'], [data-action='star']").forEach(function(button) {
        button.addEventListener("click", function() {
            toggleForumAction(button);
        });
    });
}

async function toggleForumAction(button) {
    const postId = button.getAttribute("data-post-id");
    const action = button.getAttribute("data-action");
    if (!postId || !action) {
        return;
    }

    const icon = button.querySelector(".action-icon");
    const count = button.querySelector(".count");
    if (!icon || !count) {
        return;
    }

    button.disabled = true;
    try {
        const response = await fetch(`/forum/api/${postId}/${action}`, {
            method: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest"
            }
        });
        const data = await response.json();

        if (!response.ok || !data.success) {
            if (response.status === 401) {
                window.location.href = "/auth/login";
            } else {
                alert(data.error || "操作失败，请稍后再试");
            }
            return;
        }

        const isActive = action === "like" ? Boolean(data.liked) : Boolean(data.starred);
        const nextCount = action === "like" ? (data.likes_count ?? 0) : (data.stars_count ?? 0);
        const nextIcon = action === "like"
            ? (isActive ? "❤️" : "🤍")
            : (isActive ? "⭐" : "☆");

        button.classList.toggle("active", isActive);
        icon.textContent = nextIcon;
        count.textContent = nextCount;
    } catch (error) {
        console.error("Forum action failed", error);
        alert("操作失败，请稍后再试");
    } finally {
        button.disabled = false;
    }
}

async function loadTrendingBooks() {
    const container = document.getElementById("trending-list");
    if (!container) {
        return;
    }

    try {
        const response = await fetch("/forum/api/trending");
        const data = await response.json();
        if (!response.ok || !data.success) {
            container.innerHTML = '<div class="trending-empty">热榜暂时不可用</div>';
            return;
        }

        const trending = data.trending || [];
        if (!trending.length) {
            container.innerHTML = '<div class="trending-empty">暂无热榜数据</div>';
            return;
        }

        container.innerHTML = trending.map(function(item) {
            const title = item.book_name || item.isbn || "未知书名";
            const query = encodeURIComponent(title);
            return [
                '<a class="trending-item" href="/forum/?q=' + query + '">',
                '<span class="trending-rank">' + item.rank + '</span>',
                '<span class="trending-content">',
                '<strong>' + title + '</strong>',
                '<small>' + (item.total_reviews || 0) + ' 条书评</small>',
                '</span>',
                '</a>'
            ].join("");
        }).join("");
    } catch (error) {
        console.error("Trending load failed", error);
        container.innerHTML = '<div class="trending-empty">热榜暂时不可用</div>';
    }
}
