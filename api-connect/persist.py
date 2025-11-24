import logging
import os
from typing import List, Optional

import psycopg2

logger = logging.getLogger(__name__)


class Persist:
    """
    Simple Postgres-backed persistence for chat subscriptions.
    Stores chat_id, url (unique per chat), and timestamp for future expansion.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/postgres",
        )
        self._ensure_tables()

    def _get_conn(self):
        return psycopg2.connect(self.database_url)

    def _ensure_tables(self):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        id SERIAL PRIMARY KEY,
                        chat_id TEXT NOT NULL,
                        url TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_chat_url
                        ON subscriptions (chat_id, url);
                    """
                )
            conn.commit()
        logger.info("Ensured subscriptions table exists")

    def add_item(self, chat_id: str, url: str):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO subscriptions (chat_id, url)
                    VALUES (%s, %s)
                    ON CONFLICT (chat_id, url) DO NOTHING;
                    """,
                    (chat_id, url),
                )
            conn.commit()
        logger.info("Stored subscription for chat %s: %s", chat_id, url)

    def remove_product(self, chat_id: str, url: str):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM subscriptions WHERE chat_id = %s AND url = %s",
                    (chat_id, url),
                )
                removed = cur.rowcount
            conn.commit()
        if removed:
            logger.info("Removed subscription for chat %s: %s", chat_id, url)
        else:
            logger.warning("Subscription not found for chat %s: %s", chat_id, url)

    def user_exist(self, chat_id: str) -> bool:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM subscriptions WHERE chat_id = %s LIMIT 1",
                    (chat_id,),
                )
                return cur.fetchone() is not None

    def get_urls_by_chat_id(self, chat_id: str) -> List[str]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT url
                    FROM subscriptions
                    WHERE chat_id = %s
                    ORDER BY created_at ASC;
                    """,
                    (chat_id,),
                )
                rows = cur.fetchall()
        return [row[0] for row in rows]
