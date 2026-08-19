"""Edge-case test: intentionally insecure code to verify the reviewer flags security issues.

NOT real credentials — placeholder values only, used to test that the AI reviewer
correctly detects hardcoded secrets, SQL injection, and command injection patterns.
"""
import os
import sqlite3

# Intentionally bad: hardcoded credential (fake value, for detection testing only).
API_KEY = "FAKE_TEST_KEY_DO_NOT_USE_1234567890abcdef"


def get_user(db_path: str, username: str):
    """Intentionally bad: SQL injection via string interpolation."""
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return conn.execute(query).fetchone()


def ping_host(host: str):
    """Intentionally bad: command injection via unsanitized shell input."""
    os.system("ping -c 1 " + host)
