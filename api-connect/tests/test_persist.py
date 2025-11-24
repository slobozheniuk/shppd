import types
from types import SimpleNamespace
from typing import Dict, List, Tuple

import persist


class FakeCursor:
    def __init__(self, store: Dict):
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
        self.results = []
        self.rowcount = 0

        if normalized.startswith("create table") or normalized.startswith("create unique index"):
            return

        if normalized.startswith("insert into users"):
            chat_id = params[0]
            if chat_id not in self.store["users"]:
                self.store["users"].add(chat_id)
                self.rowcount = 1
            return

        if normalized.startswith("insert into products"):
            product_id, name, url, v1 = params
            existing = next(
                (p for p in self.store["products"] if p["product_id"] == product_id and p["name"] == name and p["v1"] == v1),
                None,
            )
            if existing:
                existing["url"] = url
                product_db_id = existing["id"]
            else:
                product_db_id = len(self.store["products"]) + 1
                self.store["products"].append(
                    {"id": product_db_id, "product_id": product_id, "name": name, "url": url, "v1": v1}
                )
                self.rowcount = 1
            self.results = [(product_db_id,)]
            return

        if normalized.startswith("insert into subscriptions"):
            chat_id, product_db_id = params
            if (chat_id, product_db_id) not in self.store["subscriptions"]:
                self.store["subscriptions"].append((chat_id, product_db_id))
                self.rowcount = 1
            return

        if normalized.startswith("delete from subscriptions"):
            chat_id, url = params
            product = next((p for p in self.store["products"] if p["url"] == url), None)
            if not product:
                return
            before = len(self.store["subscriptions"])
            self.store["subscriptions"] = [
                (cid, pid) for (cid, pid) in self.store["subscriptions"] if not (cid == chat_id and pid == product["id"])
            ]
            self.rowcount = before - len(self.store["subscriptions"])
            return

        if normalized.startswith("select 1 from users"):
            chat_id = params[0]
            exists = chat_id in self.store["users"]
            self.results = [(1,)] if exists else []
            self.rowcount = len(self.results)
            return

        if normalized.startswith("select p.product_id"):
            chat_id = params[0]
            products = []
            for cid, pid in self.store["subscriptions"]:
                if cid == chat_id:
                    product = next((p for p in self.store["products"] if p["id"] == pid), None)
                    if product:
                        products.append((product["product_id"], product["name"], product["url"], product["v1"]))
            self.results = products
            self.rowcount = len(self.results)
            return

    def fetchone(self):
        return self.results[0] if self.results else None

    def fetchall(self):
        return list(self.results)


class FakeConnection:
    def __init__(self, store: Dict):
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
    store = {"users": set(), "products": [], "subscriptions": []}

    def fake_connect(_url):
        return FakeConnection(store)

    monkeypatch.setattr(persist, "psycopg2", SimpleNamespace(connect=fake_connect))
    return store


def make_product(product_id: str, name: str, url: str, v1: str):
    return SimpleNamespace(productId=product_id, name=name, url=url, v1=v1)


def test_add_and_get_products(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod = make_product("p1", "Product 1", "url1", "v1a")
    created = p.add_subscription("chat1", prod)

    assert created is True
    assert store["users"] == {"chat1"}
    assert len(store["products"]) == 1
    assert p.get_products_by_chat_id("chat1") == [
        {"productId": "p1", "name": "Product 1", "url": "url1", "v1": "v1a"}
    ]


def test_dedup_same_product_for_user(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod = make_product("p1", "Product 1", "url1", "v1a")
    p.add_subscription("chat1", prod)
    created_again = p.add_subscription("chat1", prod)

    assert created_again is False
    assert len(store["subscriptions"]) == 1
    assert p.get_products_by_chat_id("chat1") == [
        {"productId": "p1", "name": "Product 1", "url": "url1", "v1": "v1a"}
    ]


def test_multiple_users_share_product(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod = make_product("p1", "Product 1", "url1", "v1a")
    p.add_subscription("chat1", prod)
    p.add_subscription("chat2", prod)

    assert len(store["products"]) == 1  # reused product row
    assert len(store["subscriptions"]) == 2
    assert p.get_products_by_chat_id("chat2") == [
        {"productId": "p1", "name": "Product 1", "url": "url1", "v1": "v1a"}
    ]


def test_remove_product(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod1 = make_product("p1", "Product 1", "url1", "v1a")
    prod2 = make_product("p2", "Product 2", "url2", "v1b")
    p.add_subscription("chat1", prod1)
    p.add_subscription("chat1", prod2)

    p.remove_product("chat1", "url1")
    assert store["subscriptions"] == [("chat1", 2)]
    assert p.get_urls_by_chat_id("chat1") == ["url2"]

    # Removing non-existent entry should be a no-op
    p.remove_product("chat1", "url3")
    assert store["subscriptions"] == [("chat1", 2)]


def test_user_exist(monkeypatch):
    setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    assert p.user_exist("chat1") is False
    p.add_subscription("chat1", make_product("p1", "Product 1", "url1", "v1a"))
    assert p.user_exist("chat1") is True
