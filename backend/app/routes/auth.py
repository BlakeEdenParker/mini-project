from flask import Blueprint, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login_form():
    return render_template("auth/login.html", next_url=request.args.get("next", ""))


@auth_bp.post("/login")
def login():
    # Temporary front skeleton login. Replace with MariaDB user lookup later.
    username = request.form.get("username", "demo")
    users = {
        "admin": {"id": 1, "username": "admin", "is_admin": True},
        "demo": {"id": 2, "username": "demo", "is_admin": False},
    }
    session["user"] = users.get(username, users["demo"])
    return redirect(request.form.get("next_url") or url_for("posts.list_posts"))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("posts.list_posts"))
