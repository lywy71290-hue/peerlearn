import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

logging.basicConfig(level=logging.INFO)

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # ─── Configuration ────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set!")

    # Render injects postgres:// but SQLAlchemy needs postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB

    # ─── Extensions ───────────────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    migrate.init_app(app, db)

    # ─── Blueprints ───────────────────────────────────────────────────────────
    from routes.auth import auth_bp
    from routes.videos import videos_bp
    from routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(main_bp)

    # ─── Auto-create tables on first run ──────────────────────────────────────
    with app.app_context():
        from models.user import User
        from models.video import Video
        from models.comment import Comment
        from models.rating import Rating
        try:
            db.create_all()
            app.logger.info("✅ Database tables created/verified successfully.")
        except Exception as e:
            app.logger.error(f"❌ Database init error: {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False)
