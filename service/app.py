import json
import math
import os
import secrets
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

try:
    import pymysql
except ImportError:
    pymysql = None

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "change-me-in-env")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

PER_PAGE = 10

PASSWORD_HASH = (
    "scrypt:32768:8:1$6iGWMyFb7HZDipUh$"
    "48621b4676950c8ff87c26cfa1c5416baf8fe3a669e6788a3499749199dbc9c68275c70b8744bcbe8e78bc52770eb5cd28fe492fe37942bea3f1051f0c548a15"
)

MEMORY_USERS = {
    "admin": {
        "id": 1,
        "username": "admin",
        "display_name": "admin",
        "password_hash": PASSWORD_HASH,
        "is_admin": True,
    },
    "demo": {
        "id": 2,
        "username": "demo",
        "display_name": "demo",
        "password_hash": PASSWORD_HASH,
        "is_admin": False,
    },
}

MEMORY_POSTS = [
    {
        "id": 3,
        "title": "게시판 화면 구조 초안",
        "content": "목록, 상세, 작성, 수정 화면을 먼저 맞춘 뒤 인증과 DB를 연결합니다.",
        "author_id": 1,
        "author_name": "admin",
        "created_at": "2026-05-22",
        "views": 12,
        "is_deleted": False,
    },
    {
        "id": 2,
        "title": "로그인이 필요한 동작",
        "content": "작성, 수정, 삭제는 로그인 여부와 작성자 권한을 서버에서 확인해야 합니다.",
        "author_id": 2,
        "author_name": "demo",
        "created_at": "2026-05-21",
        "views": 7,
        "is_deleted": False,
    },
    {
        "id": 1,
        "title": "공개로 볼 수 있는 페이지",
        "content": "목록과 상세 페이지는 로그인하지 않아도 접근할 수 있습니다.",
        "author_id": 1,
        "author_name": "admin",
        "created_at": "2026-05-20",
        "views": 31,
        "is_deleted": False,
    },
]

MEMORY_STORE_PATH = Path(os.getenv("MEMORY_STORE_PATH", "/tmp/mini-board-posts.json"))


def load_memory_posts():
    if MEMORY_STORE_PATH.exists():
        return json.loads(MEMORY_STORE_PATH.read_text(encoding="utf-8"))
    save_memory_posts(MEMORY_POSTS)
    return list(MEMORY_POSTS)


def save_memory_posts(posts):
    MEMORY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_STORE_PATH.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def db_enabled():
    return os.getenv("DB_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def db_connection():
    if pymysql is None:
        raise RuntimeError("PyMySQL is required when DB_ENABLED=true")
    return pymysql.connect(
        host=os.getenv("DB_HOST", "10.0.2.11"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "board_app"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "board_db"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=3,
    )


def csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


@app.context_processor
def inject_template_helpers():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_post_requests():
    if request.method != "POST":
        return None
    submitted_token = request.form.get("csrf_token", "")
    if not submitted_token or submitted_token != session.get("csrf_token"):
        abort(403)
    return None


def current_user():
    return session.get("user")


def login_required():
    if not current_user():
        return redirect(url_for("login_form", next=request.path))
    return None


def normalize_user(row):
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "display_name": row.get("display_name") or row["username"],
        "password_hash": row["password_hash"],
        "is_admin": bool(row["is_admin"]),
    }


def get_user_by_username(username):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, username, password_hash, display_name, is_admin
                    FROM users
                    WHERE username = %s
                    """,
                    (username,),
                )
                return normalize_user(cursor.fetchone())
    return normalize_user(MEMORY_USERS.get(username))


def normalize_post(row):
    if not row:
        return None
    created_at = row["created_at"]
    if isinstance(created_at, datetime):
        created_at = created_at.strftime("%Y-%m-%d")
    return {
        "id": int(row["id"]),
        "title": row["title"],
        "content": row["content"],
        "author_id": int(row["author_id"]),
        "author_name": row["author_name"],
        "created_at": created_at,
        "views": int(row["views"]),
    }


def list_posts_from_memory(query, page, per_page):
    posts = [post for post in load_memory_posts() if not post.get("is_deleted")]
    if query:
        lowered = query.lower()
        posts = [
            post
            for post in posts
            if lowered in post["title"].lower() or lowered in post["author_name"].lower()
        ]
    posts = sorted(posts, key=lambda post: post["id"], reverse=True)
    total = len(posts)
    start = (page - 1) * per_page
    return posts[start : start + per_page], total


def list_posts_from_db(query, page, per_page):
    offset = (page - 1) * per_page
    filters = ["p.is_deleted = FALSE"]
    params = []
    if query:
        filters.append("(p.title LIKE %s OR u.display_name LIKE %s OR u.username LIKE %s)")
        keyword = f"%{query}%"
        params.extend([keyword, keyword, keyword])
    where_clause = " AND ".join(filters)

    with db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM posts p
                JOIN users u ON u.id = p.author_id
                WHERE {where_clause}
                """,
                params,
            )
            total = int(cursor.fetchone()["total"])

            cursor.execute(
                f"""
                SELECT
                    p.id,
                    p.title,
                    p.content,
                    p.author_id,
                    COALESCE(u.display_name, u.username) AS author_name,
                    p.created_at,
                    p.view_count AS views
                FROM posts p
                JOIN users u ON u.id = p.author_id
                WHERE {where_clause}
                ORDER BY p.id DESC
                LIMIT %s OFFSET %s
                """,
                params + [per_page, offset],
            )
            return [normalize_post(row) for row in cursor.fetchall()], total


def list_posts(query, page, per_page):
    if db_enabled():
        return list_posts_from_db(query, page, per_page)
    return list_posts_from_memory(query, page, per_page)


def find_post(post_id):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.title,
                        p.content,
                        p.author_id,
                        COALESCE(u.display_name, u.username) AS author_name,
                        p.created_at,
                        p.view_count AS views
                    FROM posts p
                    JOIN users u ON u.id = p.author_id
                    WHERE p.id = %s AND p.is_deleted = FALSE
                    """,
                    (post_id,),
                )
                return normalize_post(cursor.fetchone())
    return normalize_post(
        next(
            (
                post
                for post in load_memory_posts()
                if post["id"] == post_id and not post.get("is_deleted")
            ),
            None,
        )
    )


def create_post_record(title, content, author_id):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO posts (author_id, title, content)
                    VALUES (%s, %s, %s)
                    """,
                    (author_id, title, content),
                )
                return cursor.lastrowid

    posts = load_memory_posts()
    next_id = max(post["id"] for post in posts) + 1 if posts else 1
    user = current_user()
    posts.insert(
        0,
        {
            "id": next_id,
            "title": title,
            "content": content,
            "author_id": author_id,
            "author_name": user["username"],
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "views": 0,
            "is_deleted": False,
        },
    )
    save_memory_posts(posts)
    return next_id


def update_post_record(post_id, title, content):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE posts
                    SET title = %s, content = %s
                    WHERE id = %s AND is_deleted = FALSE
                    """,
                    (title, content, post_id),
                )
        return

    posts = load_memory_posts()
    for post in posts:
        if post["id"] == post_id:
            post["title"] = title
            post["content"] = content
            save_memory_posts(posts)
            return


def delete_post_record(post_id):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE posts SET is_deleted = TRUE WHERE id = %s",
                    (post_id,),
                )
        return

    posts = load_memory_posts()
    for post in posts:
        if post["id"] == post_id:
            post["is_deleted"] = True
            save_memory_posts(posts)
            return


def increase_view_count(post_id):
    if db_enabled():
        with db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE posts
                    SET view_count = view_count + 1
                    WHERE id = %s AND is_deleted = FALSE
                    """,
                    (post_id,),
                )
        return

    posts = load_memory_posts()
    for post in posts:
        if post["id"] == post_id:
            post["views"] += 1
            save_memory_posts(posts)
            return


def ensure_owner_or_admin(post):
    user = current_user()
    if not user or (post["author_id"] != user["id"] and not user.get("is_admin")):
        abort(403)


def clean_post_form():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        abort(400)
    return title[:120], content


@app.get("/")
@app.get("/posts")
def list_posts_view():
    page = max(request.args.get("page", 1, type=int), 1)
    query = request.args.get("q", "").strip()
    posts, total = list_posts(query, page, PER_PAGE)
    total_pages = max(math.ceil(total / PER_PAGE), 1)
    if page > total_pages:
        return redirect(url_for("list_posts_view", page=total_pages, q=query))
    return render_template(
        "posts/list.html",
        posts=posts,
        user=current_user(),
        query=query,
        pagination={"page": page, "total_pages": total_pages, "total": total},
    )


@app.get("/posts/<int:post_id>")
def detail_post(post_id):
    post = find_post(post_id)
    if not post:
        abort(404)
    increase_view_count(post_id)
    post["views"] += 1
    return render_template("posts/detail.html", post=post, user=current_user())


@app.get("/posts/new")
def new_post_form():
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    return render_template("posts/form.html", mode="create", post=None, user=current_user())


@app.post("/posts")
def create_post():
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    title, content = clean_post_form()
    post_id = create_post_record(title, content, current_user()["id"])
    return redirect(url_for("detail_post", post_id=post_id))


@app.get("/posts/<int:post_id>/edit")
def edit_post_form(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner_or_admin(post)
    return render_template("posts/form.html", mode="edit", post=post, user=current_user())


@app.post("/posts/<int:post_id>/edit")
def update_post(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner_or_admin(post)
    title, content = clean_post_form()
    update_post_record(post_id, title, content)
    return redirect(url_for("detail_post", post_id=post_id))


@app.post("/posts/<int:post_id>/delete")
def delete_post(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner_or_admin(post)
    delete_post_record(post_id)
    return redirect(url_for("list_posts_view"))


@app.get("/login")
def login_form():
    return render_template("auth/login.html", next_url=request.args.get("next", ""), user=current_user())


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = get_user_by_username(username)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "auth/login.html",
            next_url=request.form.get("next_url", ""),
            user=current_user(),
            error="아이디 또는 비밀번호가 올바르지 않습니다.",
        ), 401

    session.clear()
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "is_admin": user["is_admin"],
    }
    csrf_token()
    return redirect(request.form.get("next_url") or url_for("list_posts_view"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("list_posts_view"))


@app.errorhandler(400)
def bad_request(_error):
    return render_template("errors/404.html", user=current_user()), 400


@app.errorhandler(403)
def forbidden(_error):
    return render_template("errors/403.html", user=current_user()), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html", user=current_user()), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
