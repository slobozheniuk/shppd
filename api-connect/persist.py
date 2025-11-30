import logging
import os
from typing import Dict, List, Optional, Tuple

import psycopg2

logger = logging.getLogger(__name__)


class Persist:
    """
    Postgres-backed persistence for chat subscriptions.
    Stores users, products, and subscriptions (many-to-many) with optional size selections.
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
                    CREATE TABLE IF NOT EXISTS users (
                        chat_id TEXT PRIMARY KEY,
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS products (
                        id SERIAL PRIMARY KEY,
                        product_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL,
                        v1 TEXT NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(product_id, name, v1)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        chat_id TEXT NOT NULL REFERENCES users(chat_id) ON DELETE CASCADE,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        selected_sizes TEXT[],
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(chat_id, product_id)
                    );
                    """
                )
                # Add column if upgrading an existing DB.
                cur.execute(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'subscriptions'
                              AND column_name = 'selected_sizes'
                        ) THEN
                            ALTER TABLE subscriptions ADD COLUMN selected_sizes TEXT[];
                        END IF;
                    END$$;
                    """
                )
            conn.commit()
        logger.info("Ensured users, products, subscriptions tables exist")

    def _ensure_user(self, chat_id: str):
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (chat_id)
                    VALUES (%s)
                    ON CONFLICT (chat_id) DO NOTHING;
                    """,
                    (chat_id,),
                )
            conn.commit()

    def _ensure_product(self, product: Dict[str, str]) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO products (product_id, name, url, v1)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id, name, v1)
                    DO UPDATE SET url = EXCLUDED.url
                    RETURNING id;
                    """,
                    (
                        product["product_id"],
                        product["name"],
                        product["url"],
                        product["v1"],
                    ),
                )
                product_db_id = cur.fetchone()[0]
            conn.commit()
        return product_db_id

    def add_subscription(self, chat_id: str, product, selected_sizes: Optional[List[str]] = None) -> Tuple[bool, bool]:
        """
        Ensure a user and product exist, then link them.
        Returns (created, updated_sizes) where created is True if a new link was created,
        and updated_sizes is True if an existing subscription had its sizes updated.
        """
        product_dict = {
            "product_id": getattr(product, "productId"),
            "name": getattr(product, "name"),
            "url": getattr(product, "url"),
            "v1": getattr(product, "v1"),
        }
        if not all(product_dict.values()):
            raise ValueError("Product must include productId, name, url, and v1")

        self._ensure_user(chat_id)
        product_db_id = self._ensure_product(product_dict)

        created = False
        updated_sizes = False

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO subscriptions (chat_id, product_id, selected_sizes)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (chat_id, product_id) DO NOTHING;
                    """,
                    (chat_id, product_db_id, selected_sizes),
                )
                created = cur.rowcount > 0

                if (not created) and selected_sizes is not None:
                    cur.execute(
                        """
                        UPDATE subscriptions
                        SET selected_sizes = %s
                        WHERE chat_id = %s AND product_id = %s;
                        """,
                        (selected_sizes, chat_id, product_db_id),
                    )
                    updated_sizes = cur.rowcount > 0
            conn.commit()

        logger.info(
            "Stored subscription chat_id=%s product_id=%s created=%s updated_sizes=%s",
            chat_id,
            product_dict["product_id"],
            created,
            updated_sizes,
        )
        return created, updated_sizes

    def remove_product(self, chat_id: str, url: str):
        """
        Remove a subscription for the given chat_id and product URL.
        """
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM subscriptions s
                    USING products p
                    WHERE s.chat_id = %s AND s.product_id = p.id AND p.url = %s;
                    """,
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
                    "SELECT 1 FROM users WHERE chat_id = %s LIMIT 1",
                    (chat_id,),
                )
                return cur.fetchone() is not None

    def get_products_by_chat_id(self, chat_id: str) -> List[Dict[str, str]]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.product_id, p.name, p.url, p.v1, s.selected_sizes
                    FROM subscriptions s
                    JOIN products p ON s.product_id = p.id
                    WHERE s.chat_id = %s
                    ORDER BY s.created_at ASC;
                    """,
                    (chat_id,),
                )
                rows = cur.fetchall()

        return [
            {
                "productId": row[0],
                "name": row[1],
                "url": row[2],
                "v1": row[3],
                "selectedSizes": row[4] or [],
            }
            for row in rows
        ]

    def get_urls_by_chat_id(self, chat_id: str) -> List[str]:
        """
        Convenience helper for code paths that only need URLs.
        """
        return [row["url"] for row in self.get_products_by_chat_id(chat_id)]

    def get_selected_sizes(self, chat_id: str, url: str) -> Optional[List[str]]:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.selected_sizes
                    FROM subscriptions s
                    JOIN products p ON s.product_id = p.id
                    WHERE s.chat_id = %s AND p.url = %s;
                    """,
                    (chat_id, url),
                )
                row = cur.fetchone()
        if not row:
            return None
        return row[0] or []
