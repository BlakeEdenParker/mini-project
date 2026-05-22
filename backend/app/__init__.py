from pathlib import Path

from flask import Flask, render_template


def create_app():
    project_root = Path(__file__).resolve().parents[2]
    frontend_root = project_root / "frontend"

    app = Flask(
        __name__,
        template_folder=str(frontend_root / "templates"),
        static_folder=str(frontend_root / "static"),
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = "change-me-in-env"

    from app.routes.auth import auth_bp
    from app.routes.posts import posts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    return app

