import pytest


@pytest.fixture(autouse=True)
def _contact(monkeypatch):
    # Kontak palsu khusus tes (tidak ada request jaringan nyata di test suite).
    monkeypatch.setenv("ASHEN_NEWS_CONTACT", "tests.invalid")
