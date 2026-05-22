from flask import Blueprint, abort, redirect, render_template, request, session, url_for

posts_bp = Blueprint("posts", __name__)

# SAMPLE_POSTS = [
#     {
#         "id": 3,
#         "title": "게시판 화면 구조 초안",
#         "content": "목록, 상세, 작성, 수정 화면을 먼저 맞춘 뒤 인증과 DB를 연결합니다.",
#         "author_id": 1,
#         "author_name": "admin",
#         "created_at": "2026-05-22",
#         "views": 12,
#     },
#     {
#         "id": 2,
#         "title": "로그인이 필요한 동작",
#         "content": "작성, 수정, 삭제는 로그인 여부와 작성자 권한을 서버에서 확인해야 합니다.",
#         "author_id": 2,
#         "author_name": "demo",
#         "created_at": "2026-05-21",
#         "views": 7,
#     },
#     {
#         "id": 1,
#         "title": "공개로 볼 수 있는 페이지",
#         "content": "목록과 상세 페이지는 로그인하지 않아도 접근할 수 있습니다.",
#         "author_id": 1,
#         "author_name": "admin",
#         "created_at": "2026-05-20",
#         "views": 31,
#     },
# ]


def current_user():
    return session.get("user")


def login_required():
    if not current_user():
        return redirect(url_for("auth.login_form", next=request.path))
    return None


def find_post(post_id):
    return next((post for post in SAMPLE_POSTS if post["id"] == post_id), None)


def ensure_owner(post):
    user = current_user()
    if not user or (post["author_id"] != user["id"] and not user.get("is_admin")):
        abort(403)


@posts_bp.get("/")
@posts_bp.get("/posts")
def list_posts():
    return render_template("posts/list.html", posts=SAMPLE_POSTS, user=current_user())


@posts_bp.get("/posts/<int:post_id>")
def detail_post(post_id):
    post = find_post(post_id)
    if not post:
        abort(404)
    return render_template("posts/detail.html", post=post, user=current_user())


@posts_bp.get("/posts/new")
def new_post_form():
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    return render_template("posts/form.html", mode="create", post=None, user=current_user())


@posts_bp.post("/posts")
def create_post():
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    return redirect(url_for("posts.list_posts"))


@posts_bp.get("/posts/<int:post_id>/edit")
def edit_post_form(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner(post)
    return render_template("posts/form.html", mode="edit", post=post, user=current_user())


@posts_bp.post("/posts/<int:post_id>/edit")
def update_post(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner(post)
    return redirect(url_for("posts.detail_post", post_id=post_id))


@posts_bp.post("/posts/<int:post_id>/delete")
def delete_post(post_id):
    auth_redirect = login_required()
    if auth_redirect:
        return auth_redirect
    post = find_post(post_id)
    if not post:
        abort(404)
    ensure_owner(post)
    return redirect(url_for("posts.list_posts"))
