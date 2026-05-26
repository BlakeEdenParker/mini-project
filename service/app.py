from flask import Flask, abort, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me-in-env"

SAMPLE_POSTS = [
    {
        "id": 3,
        "title": "게시판 화면 구조 초안",
        "content": "목록, 상세, 작성, 수정 화면을 먼저 맞춘 뒤 인증과 DB를 연결합니다.",
        "author_id": 1,
        "author_name": "admin",
        "created_at": "2026-05-22",
        "views": 12,
    },
    {
        "id": 2,
        "title": "로그인이 필요한 동작",
        "content": "작성, 수정, 삭제는 로그인 여부와 작성자 권한을 서버에서 확인해야 합니다.",
        "author_id": 2,
        "author_name": "demo",
        "created_at": "2026-05-21",
        "views": 7,
    },
    {
        "id": 1,
        "title": "공개로 볼 수 있는 페이지",
        "content": "목록과 상세 페이지는 로그인하지 않아도 접근할 수 있습니다.",
        "author_id": 1,
        "author_name": "admin",
        "created_at": "2026-05-20",
        "views": 31,
    },
]


def current_user():
    return session.get("user")


def login_required():
    if not current_user():
        return redirect(url_for("login_form", next=request.path))
    return None


def find_post(post_id):
    return next((post for post in SAMPLE_POSTS if post["id"] == post_id), None)


def ensure_owner_or_admin(post):
    user = current_user()
    if not user or (post["author_id"] != user["id"] and not user.get("is_admin")):
        abort(403)


@app.get("/")
@app.get("/posts")
def list_posts():
    return render_template("posts/list.html", posts=SAMPLE_POSTS, user=current_user())


@app.get("/posts/<int:post_id>")
def detail_post(post_id):
    post = find_post(post_id)
    if not post:
        abort(404)
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
    return redirect(url_for("list_posts"))


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
    return redirect(url_for("list_posts"))


@app.get("/login")
def login_form():
    return render_template("auth/login.html", next_url=request.args.get("next", ""), user=current_user())


@app.post("/login")
def login():
    username = request.form.get("username", "demo")
    users = {
        "admin": {"id": 1, "username": "admin", "is_admin": True},
        "demo": {"id": 2, "username": "demo", "is_admin": False},
    }
    session["user"] = users.get(username, users["demo"])
    return redirect(request.form.get("next_url") or url_for("list_posts"))


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("list_posts"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("errors/403.html", user=current_user()), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("errors/404.html", user=current_user()), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
