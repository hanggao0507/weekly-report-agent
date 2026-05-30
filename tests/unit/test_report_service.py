from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.config import load_settings
from src.services.report_service import ReportService
from src.services.summarizer import LLMSummarizer


def test_report_service_generates_artifacts():
    settings = load_settings("config/example.yaml")
    service = ReportService(settings)
    report = service.generate_report("testrun123", "manual")
    assert report.team_summary.done
    assert report.member_summaries
    assert report.artifacts is not None
    assert "团队总览" in report.artifacts.markdown
    assert Path(report.artifacts.markdown_path).exists()
    assert Path(report.artifacts.html_path).exists()
    assert Path(report.artifacts.json_path).exists()


def test_real_llm_mode_requires_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MISSING_OPENAI_API_KEY", raising=False)
    settings = load_settings("config/example.yaml")
    settings.llm.mode = "real"
    settings.llm.provider = "openai"
    settings.llm.model = "gpt-4.1"
    settings.llm.temperature = 0.2
    settings.llm.api_key_env = "MISSING_OPENAI_API_KEY"
    service = ReportService(settings)
    with pytest.raises(ValueError):
        service.generate_report("realmode001", "manual")


def test_real_llm_uses_configured_base_url(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FAKE_OPENAI_API_KEY", "test-key")
    settings = load_settings("config/example.yaml")
    settings.llm.mode = "real"
    settings.llm.api_key_env = "FAKE_OPENAI_API_KEY"
    settings.llm.base_url = "https://xxx"
    service = ReportService(settings)
    assert service.summarizer.client.base_url.host == "xxx"


def test_real_llm_mode_falls_back_to_rule_based(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FAKE_OPENAI_API_KEY", "test-key")
    settings = load_settings("config/example.yaml")
    settings.llm.mode = "real"
    settings.llm.provider = "openai"
    settings.llm.model = "gpt-4.1"
    settings.llm.api_key_env = "FAKE_OPENAI_API_KEY"
    settings.llm.fallback_to_mock = True

    service = ReportService(settings)

    def raise_error(*args, **kwargs):
        raise RuntimeError("mock llm failure")

    monkeypatch.setattr(service.summarizer.client.responses, "create", raise_error)
    report = service.generate_report("fallback001", "manual")
    assert report.team_summary.done
    assert report.member_summaries


def test_real_llm_mode_raises_when_fallback_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FAKE_OPENAI_API_KEY", "test-key")
    settings = load_settings("config/example.yaml")
    settings.llm.mode = "real"
    settings.llm.provider = "openai"
    settings.llm.model = "gpt-4.1"
    settings.llm.api_key_env = "FAKE_OPENAI_API_KEY"
    settings.llm.fallback_to_mock = False

    service = ReportService(settings)

    def raise_error(*args, **kwargs):
        raise RuntimeError("mock llm failure")

    monkeypatch.setattr(service.summarizer.client.responses, "create", raise_error)
    with pytest.raises(RuntimeError):
        service.generate_report("nofallback001", "manual")
