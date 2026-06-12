#!/bin/bash
set -e

DB_HOST="${HOST:-db}"
DB_PORT="${PORT:-5432}"
DB_USER="${USER:-uduu}"
DB_PASSWORD="${PASSWORD}"
DB_NAME="${POSTGRES_DB:-uduu}"

check_initialized() {
    python3 - <<EOF
import psycopg2, sys
try:
    conn = psycopg2.connect(
        host="$DB_HOST", port=$DB_PORT,
        user="$DB_USER", password="$DB_PASSWORD",
        dbname="$DB_NAME"
    )
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name='ir_module_module'")
    print("yes" if cur.fetchone() else "no")
    conn.close()
except Exception:
    print("no")
EOF
}

if [ "$(check_initialized)" != "yes" ]; then
    echo "==> First run: initializing Odoo database..."
    odoo --config=/etc/odoo/odoo.conf \
        --db_host="$DB_HOST" \
        --db_port="$DB_PORT" \
        --db_user="$DB_USER" \
        --db_password="$DB_PASSWORD" \
        -i uduu_base --stop-after-init
    echo "==> Database initialized."
fi

exec odoo --config=/etc/odoo/odoo.conf \
    --db_host="$DB_HOST" \
    --db_port="$DB_PORT" \
    --db_user="$DB_USER" \
    --db_password="$DB_PASSWORD"
