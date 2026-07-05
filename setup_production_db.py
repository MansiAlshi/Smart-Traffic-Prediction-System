"""
Run this script ONCE after you get your Aiven MySQL credentials.
It will create all database tables automatically.

Usage:
    python setup_production_db.py

Just paste your Aiven credentials below before running.
"""

import pymysql
import re
import os
import sys

# ─────────────────────────────────────────────────────────────
# PASTE YOUR AIVEN CREDENTIALS HERE
# ─────────────────────────────────────────────────────────────
MYSQL_HOST     = os.getenv("MYSQL_HOST", "")      # e.g. mysql-xxx.aivencloud.com
MYSQL_PORT     = int(os.getenv("MYSQL_PORT", "0")) # e.g. 12345
MYSQL_USER     = os.getenv("MYSQL_USER", "")      # e.g. avnadmin
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")  # the long password
MYSQL_DB       = os.getenv("MYSQL_DB", "")        # e.g. defaultdb
# ─────────────────────────────────────────────────────────────

def main():
    missing = [k for k, v in {
        "MYSQL_HOST": MYSQL_HOST,
        "MYSQL_PORT": MYSQL_PORT,
        "MYSQL_USER": MYSQL_USER,
        "MYSQL_PASSWORD": MYSQL_PASSWORD,
        "MYSQL_DB": MYSQL_DB,
    }.items() if not v]

    if missing:
        print(f"❌  Missing credentials: {', '.join(missing)}")
        print("    Set them as environment variables or paste them directly in this file.")
        sys.exit(1)

    print(f"Connecting to {MYSQL_HOST}:{MYSQL_PORT} as {MYSQL_USER}...")
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        ssl={"ssl": {}},  # Aiven requires SSL
    )
    cursor = conn.cursor()
    print("✅  Connected!")

    schema_path = os.path.join(os.path.dirname(__file__), "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Remove MySQL-specific CREATE DATABASE / USE statements (not valid on hosted DB)
    sql = re.sub(r"CREATE\s+DATABASE\s+.*?;", "", sql, flags=re.DOTALL | re.IGNORECASE)
    sql = re.sub(r"USE\s+\S+\s*;", "", sql, flags=re.IGNORECASE)

    statements = [s.strip() for s in sql.split(";") if s.strip()]
    ok = 0
    skipped = 0
    for stmt in statements:
        try:
            cursor.execute(stmt)
            ok += 1
        except Exception as e:
            print(f"   ⚠  Skipped (probably already exists): {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n✅  Done! {ok} statements executed, {skipped} skipped.")
    print("    Your production database is ready.")

if __name__ == "__main__":
    main()
