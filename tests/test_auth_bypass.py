from app import auth
from app.models import User, UserRole


class _FakeQuery:
    def __init__(self, users):
        self._users = users

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._users[0] if self._users else None


class _FakeSession:
    def __init__(self, users):
        self._users = users

    def query(self, *args, **kwargs):
        return _FakeQuery(self._users)


def _admin_user():
    return User(id=1, name="Admin", email="admin@frampol.local", role=UserRole.admin, password_hash="x")


def test_bypass_disabled_by_default(monkeypatch):
    monkeypatch.setattr(auth.settings, "skip_auth", False)
    assert auth._dev_bypass_user(_FakeSession([_admin_user()])) is None


def test_bypass_returns_admin_when_enabled(monkeypatch):
    monkeypatch.setattr(auth.settings, "skip_auth", True)
    admin = _admin_user()
    result = auth._dev_bypass_user(_FakeSession([admin]))
    assert result is admin
