import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # ─── Configuration ────────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL", "postgresql://localhost/peer_learning"
    )
    # Render injects postgres:// but SQLAlchemy needs postgresql://
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config[
            "SQLALCHEMY_DATABASE_URI"
        ].replace("postgres://", "postgresql://", 1)

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
        # Import all models so SQLAlchemy knows about them
        from models.user import User
        from models.video import Video
        from models.comment import Comment
        from models.rating import Rating
        try:
            db.create_all()
            print("✅ Database tables created/verified successfully.")
        except Exception as e:
            print(f"⚠️  Database init warning: {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False)
