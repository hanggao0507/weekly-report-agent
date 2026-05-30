from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.adapters import FeishuMockAdapter, GitHubMockAdapter
from src.config import load_settings
from src.models import TimeWindow
from src.services.member_service import MemberDirectory


def _window():
    tz = ZoneInfo("Asia/Shanghai")
    end_at = datetime(2026, 5, 30, 23, 59, tzinfo=tz)
    start_at = end_at - timedelta(days=7)
    return TimeWindow(start_at=start_at, end_at=end_at, timezone="Asia/Shanghai", label="test")


def test_github_mock_adapter_maps_items():
    settings = load_settings("config/example.yaml")
    adapter = GitHubMockAdapter(settings)
    member = MemberDirectory(settings).all()[0]
    items = adapter.fetch(member, _window())
    assert any(item.category == "commit" for item in items)
    assert any(item.category == "pull_request" for item in items)
    assert all(item.source == "github" for item in items)


def test_feishu_mock_adapter_maps_items():
    settings = load_settings("config/example.yaml")
    adapter = FeishuMockAdapter(settings)
    member = MemberDirectory(settings).all()[1]
    items = adapter.fetch(member, _window())
    assert any(item.category == "calendar" for item in items)
    assert any(item.category == "message" for item in items)
    assert any(item.risk_flag for item in items)

