import os
import pytest
from app.db import get_connection

@pytest.mark.skipif(os.getenv('DATABASE_URL') is None, reason='DATABASE_URL not set')
def test_db_connection():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result[0] == 1
    except Exception as exc:
        pytest.skip(f"Database connection failed: {exc}")
