import types
from typing import List, Tuple

import persist


class FakeCursor:
    def __init__(self, store: List[Tuple[str, str]]):
        self.store = store
        self.results = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query: str, params=None):
        normalized = " ".join(query.lower().split())
        params = params or ()

        if normalized.startswith("create table") or normalized.startswith("create unique index"):
            # Table setup is a no-op for the fake store.
            self.rowcount = 0
            self.results = []
            return

        if "insert into subscriptions" in normalized:
            chat_id, url = params
            if (chat_id, url) not in self.store:
                self.store.append((chat_id, url))
                self.rowcount = 1
            else:
                self.rowcount = 0
            self.results = []
            return

        if normalized.startswith("delete from subscriptions"):
            chat_id, url = params
            before = len(self.store)
            self.store[:] = [(cid, u) for (cid, u) in self.store if not (cid == chat_id and u == url)]
            self.rowcount = before - len(self.store)
            self.results = []
            return

        if normalized.startswith("select 1 from subscriptions"):
            chat_id = params[0]
            exists = any(cid == chat_id for cid, _ in self.store)
            self.results = [(1,)] if exists else []
            self.rowcount = len(self.results)
            return

        if normalized.startswith("select url"):
            chat_id = params[0]
            urls = [url for (cid, url) in self.store if cid == chat_id]
            self.results = [(url,) for url in urls]
            self.rowcount = len(self.results)
            return

        # Default: no-op
        self.results = []
        self.rowcount = 0

    def fetchone(self):
        return self.results[0] if self.results else None

    def fetchall(self):
        return list(self.results)


class FakeConnection:
    def __init__(self, store: List[Tuple[str, str]]):
        self.store = store

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def setup_fake_db(monkeypatch):
    """
    Patch psycopg2.connect to use an in-memory store for tests.
    """
    store: List[Tuple[str, str]] = []

    def fake_connect(_url):
        return FakeConnection(store)

    monkeypatch.setattr(persist, "psycopg2", types.SimpleNamespace(connect=fake_connect))
    return store


def test_add_and_get_urls(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    p.add_item("chat1", "url1")
    p.add_item("chat1", "url2")

    assert store == [("chat1", "url1"), ("chat1", "url2")]
    assert p.get_urls_by_chat_id("chat1") == ["url1", "url2"]


def test_dedup_same_chat_url(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    p.add_item("chat1", "url1")
    p.add_item("chat1", "url1")  # duplicate should be ignored

    assert store == [("chat1", "url1")]
    assert p.get_urls_by_chat_id("chat1") == ["url1"]


def test_remove_product(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    p.add_item("chat1", "url1")
    p.add_item("chat1", "url2")

    p.remove_product("chat1", "url1")
    assert store == [("chat1", "url2")]
    assert p.get_urls_by_chat_id("chat1") == ["url2"]

    # Removing non-existent entry should be a no-op
    p.remove_product("chat1", "url3")
    assert store == [("chat1", "url2")]


def test_user_exist(monkeypatch):
    setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    assert p.user_exist("chat1") is False
    p.add_item("chat1", "url1")
    assert p.user_exist("chat1") is True
