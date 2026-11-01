"""What every test of the hooks shares: the package of the hooks on sys.path, where
their entry puts it, and the fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".github"))

import hub.releases


@pytest.fixture(autouse=True)
def no_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tests write nothing into the summary of the job of the CI that runs them,
    which the hooks write into when GitHub Actions names its file."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


@pytest.fixture
def no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """No token of a workflow, as on a computer without one."""
    for name in hub.releases.TOKENS:
        monkeypatch.delenv(name, raising=False)
