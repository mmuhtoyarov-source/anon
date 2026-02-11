import json
import time

import pytest

from storage.redis_store import RedisStorage


class InMemoryRedis:
    def __init__(self):
        self.kv = {}
        self.exp = {}
        self.lists = {}
        self.hashes = {}

    def _alive(self, key):
        deadline = self.exp.get(key)
        if deadline and deadline < time.time():
            self.kv.pop(key, None)
            self.hashes.pop(key, None)
            self.exp.pop(key, None)
            return False
        return True

    async def set(self, key, value, ex=None):
        self.kv[key] = str(value)
        if ex:
            self.exp[key] = time.time() + ex

    async def get(self, key):
        if key in self.kv and self._alive(key):
            return self.kv[key]
        return None

    async def delete(self, key):
        self.kv.pop(key, None)
        self.hashes.pop(key, None)

    async def rpush(self, key, value):
        self.lists.setdefault(key, []).append(int(value))

    async def lpop(self, key):
        arr = self.lists.get(key, [])
        return arr.pop(0) if arr else None

    async def lrem(self, key, _count, value):
        arr = self.lists.get(key, [])
        self.lists[key] = [v for v in arr if v != int(value)]

    async def hset(self, key, mapping):
        self.hashes[key] = dict(mapping)

    async def expire(self, key, ttl):
        self.exp[key] = time.time() + ttl

    async def hgetall(self, key):
        if self._alive(key):
            return self.hashes.get(key, {})
        return {}

    async def exists(self, key):
        if key in self.kv and self._alive(key):
            return 1
        return 0

    async def keys(self, pattern):
        prefix = pattern.replace("*", "")
        return [k for k in self.hashes if k.startswith(prefix) and self._alive(k)]


class FakePG:
    def __init__(self):
        self.dialogs = []
        self.reports = []

    async def create_dialog(self, dialog_id, user1, user2):
        self.dialogs.append((dialog_id, user1, user2))

    async def end_dialog(self, dialog_id, reason):
        return None

    async def create_topic(self, topic_id, user_id, text, expires_at):
        return None

    async def create_report(self, from_id, target_id, reason):
        self.reports.append((from_id, target_id, reason))


@pytest.fixture
def redis_store():
    return RedisStorage(InMemoryRedis())


@pytest.fixture
def fake_pg():
    return FakePG()