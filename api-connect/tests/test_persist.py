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
            chat_id, product_db_id, selected_sizes = params
            sub = next((s for s in self.store["subscriptions"] if s["chat_id"] == chat_id and s["product_id"] == product_db_id), None)
            if not sub:
                self.store["subscriptions"].append(
                    {"chat_id": chat_id, "product_id": product_db_id, "selected_sizes": selected_sizes}
                )
                self.rowcount = 1
            return

        if normalized.startswith("update subscriptions"):
            selected_sizes, chat_id, product_db_id = params
            for sub in self.store["subscriptions"]:
                if sub["chat_id"] == chat_id and sub["product_id"] == product_db_id:
                    sub["selected_sizes"] = selected_sizes
                    self.rowcount = 1
            return

        if normalized.startswith("delete from subscriptions"):
            chat_id, url = params
            product = next((p for p in self.store["products"] if p["url"] == url), None)
            if not product:
                return
            before = len(self.store["subscriptions"])
            self.store["subscriptions"] = [
                s for s in self.store["subscriptions"] if not (s["chat_id"] == chat_id and s["product_id"] == product["id"])
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
            for sub in self.store["subscriptions"]:
                if sub["chat_id"] == chat_id:
                    product = next((p for p in self.store["products"] if p["id"] == sub["product_id"]), None)
                    if product:
                        products.append((product["product_id"], product["name"], product["url"], product["v1"], sub["selected_sizes"]))
            self.results = products
            self.rowcount = len(self.results)
            return

        if normalized.startswith("select s.selected_sizes"):
            chat_id, url = params
            product = next((p for p in self.store["products"] if p["url"] == url), None)
            if not product:
                return
            sub = next((s for s in self.store["subscriptions"] if s["chat_id"] == chat_id and s["product_id"] == product["id"]), None)
            if sub:
                self.results = [(sub["selected_sizes"],)]
                self.rowcount = 1
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
    created, updated = p.add_subscription("chat1", prod, selected_sizes=["S", "M"])

    assert created is True and updated is False
    assert store["users"] == {"chat1"}
    assert len(store["products"]) == 1
    assert p.get_products_by_chat_id("chat1") == [
        {"productId": "p1", "name": "Product 1", "url": "url1", "v1": "v1a", "selectedSizes": ["S", "M"]}
    ]


def test_dedup_and_update_sizes(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod = make_product("p1", "Product 1", "url1", "v1a")
    p.add_subscription("chat1", prod, selected_sizes=["S"])
    created_again, updated_again = p.add_subscription("chat1", prod, selected_sizes=["S", "M"])

    assert created_again is False and updated_again is True
    assert p.get_products_by_chat_id("chat1")[0]["selectedSizes"] == ["S", "M"]


def test_multiple_users_share_product(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod = make_product("p1", "Product 1", "url1", "v1a")
    p.add_subscription("chat1", prod, selected_sizes=["S"])
    p.add_subscription("chat2", prod, selected_sizes=["M"])

    assert len(store["products"]) == 1  # reused product row
    assert len(store["subscriptions"]) == 2
    assert p.get_products_by_chat_id("chat2")[0]["selectedSizes"] == ["M"]


def test_remove_product(monkeypatch):
    store = setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    prod1 = make_product("p1", "Product 1", "url1", "v1a")
    prod2 = make_product("p2", "Product 2", "url2", "v1b")
    p.add_subscription("chat1", prod1)
    p.add_subscription("chat1", prod2)

    p.remove_product("chat1", "url1")
    assert store["subscriptions"] == [{"chat_id": "chat1", "product_id": 2, "selected_sizes": None}]
    assert p.get_urls_by_chat_id("chat1") == ["url2"]

    # Removing non-existent entry should be a no-op
    p.remove_product("chat1", "url3")
    assert store["subscriptions"] == [{"chat_id": "chat1", "product_id": 2, "selected_sizes": None}]


def test_get_selected_sizes(monkeypatch):
    setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    p.add_subscription("chat1", make_product("p1", "Product 1", "url1", "v1a"), selected_sizes=["L", "XL"])

    assert p.get_selected_sizes("chat1", "url1") == ["L", "XL"]


def test_user_exist(monkeypatch):
    setup_fake_db(monkeypatch)
    p = persist.Persist(database_url="postgresql://fake")

    assert p.user_exist("chat1") is False
    p.add_subscription("chat1", make_product("p1", "Product 1", "url1", "v1a"))
    assert p.user_exist("chat1") is True
