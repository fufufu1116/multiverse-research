"""Deterministic fake DB-API harness for repository-only adapter tests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ExpectedCall:
    query: str
    params: tuple[Any, ...]
    fetchone: Any = None


class ScriptedCursor:
    def __init__(self, expected: list[ExpectedCall]):
        self.expected = list(expected)
        self._last = None
        self.closed = False
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    @staticmethod
    def _norm(query: str) -> str:
        return " ".join(query.split())

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        if not self.expected:
            raise AssertionError(f"UNEXPECTED_SQL:{self._norm(query)}:{params!r}")
        expected = self.expected.pop(0)
        actual_norm = self._norm(query)
        expected_norm = self._norm(expected.query)
        if actual_norm != expected_norm:
            raise AssertionError(f"SQL_MISMATCH:{actual_norm!r}!={expected_norm!r}")
        if tuple(params) != tuple(expected.params):
            raise AssertionError(f"PARAM_MISMATCH:{params!r}!={expected.params!r}")
        self.calls.append((query, tuple(params)))
        self._last = expected.fetchone

    def fetchone(self) -> Any:
        return self._last

    def close(self) -> None:
        self.closed = True


class ScriptedConnection:
    def __init__(self, expected: list[ExpectedCall]):
        self.cursor_obj = ScriptedCursor(expected)
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> ScriptedCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


class ConnectionFactoryQueue:
    def __init__(self, connections: list[ScriptedConnection]):
        self.connections = list(connections)
        self.calls = 0

    def __call__(self) -> ScriptedConnection:
        self.calls += 1
        if not self.connections:
            raise AssertionError("NO_SCRIPTED_CONNECTION")
        return self.connections.pop(0)
