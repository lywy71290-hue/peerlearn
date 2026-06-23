#!/usr/bin/env bash
set -e
echo "=== PeerLearn Starting ==="
echo "Python: $(python3 --version)"
echo "PORT: ${PORT:-8000}"

# ── Run DB migrations to add new columns if they don't exist ──────────────────
python3 - <<'PYEOF'
import os, sys
import psycopg2

db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# Convert SQLAlchemy URL to psycopg2 DSN
dsn = db_url.replace("postgresql://", "postgres://", 1)

try:
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    cur = conn.cursor()

    migrations = [
        # Users columns
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS program VARCHAR(30) DEFAULT '';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS level  VARCHAR(30) DEFAULT '';",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;",
        # Videos moderation column
        "ALTER TABLE videos ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT FALSE;",
        # Notifications table
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            message    VARCHAR(300) NOT NULL,
            link       VARCHAR(300) DEFAULT '',
            is_read    BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """,
    ]

    for sql in migrations:
        cur.execute(sql)
        print(f"✅ Migration OK: {sql.strip()[:60]}")

    cur.close()
    conn.close()
    print("✅ All migrations applied successfully.")
except Exception as e:
    print(f"⚠️  Migration warning (non-fatal): {e}", file=sys.stderr)
PYEOF

exec gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
