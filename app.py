import os
import logging
from datetime import timedelta
from flask import Flask, render_template
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

    # Session lasts 1 hour
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(hours=1)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

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
    login_manager.login_message = "Please sign in to access this page."
    login_manager.login_message_category = "info"
    migrate.init_app(app, db)

    # ─── Blueprints ───────────────────────────────────────────────────────────
    from routes.auth          import auth_bp
    from routes.videos        import videos_bp
    from routes.main          import main_bp
    from routes.admin         import admin_bp
    from routes.notifications import notif_bp
    from routes.posts         import posts_bp
    from routes.chat          import chat_bp
    from routes.live          import live_bp
    from routes.rewards        import rewards_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(videos_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notif_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(live_bp)
    app.register_blueprint(rewards_bp)

    # ─── Error Handlers ───────────────────────────────────────────────────────
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/403.html"), 404

    # ─── Auto-create tables on first run ──────────────────────────────────────
    with app.app_context():
        from models.user         import User
        from models.video        import Video
        from models.comment      import Comment
        from models.rating       import Rating
        from models.notification import Notification
        from models.post         import Post, PostComment, PostLike
        from models.chat         import ChatMessage
        from models.otp          import OTPCode
        from models.rewards      import PointTransaction, RewardRequest, PlatformRating
        try:
            db.create_all()
            app.logger.info("✅ Database tables created/verified successfully.")
        except Exception as e:
            app.logger.error(f"❌ Database init error: {e}")

        # ─── Safe column migrations (add missing columns without dropping data) ─
        try:
            from sqlalchemy import text, inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            # Add total_points to users if missing
            if 'users' in existing_tables:
                cols = [c['name'] for c in inspector.get_columns('users')]
                if 'total_points' not in cols:
                    db.session.execute(text('ALTER TABLE users ADD COLUMN total_points INTEGER DEFAULT 0 NOT NULL'))
                    db.session.commit()
                    app.logger.info("✅ Added total_points column to users table.")

            app.logger.info("✅ Column migrations completed.")
        except Exception as e:
            app.logger.error(f"❌ Column migration error: {e}")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False)
