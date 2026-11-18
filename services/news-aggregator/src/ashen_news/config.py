"""Memuat konfigurasi YAML (sumber, topik, provinsi, overrides)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

CONTACT_ENV = "ASHEN_NEWS_CONTACT"
SERVICE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_DIR = SERVICE_ROOT / "config"
DEFAULT_DB_PATH = SERVICE_ROOT / "data" / "news.db"
DEFAULT_AUDIT_DIR = SERVICE_ROOT / "data" / "audit"


@dataclass(frozen=True)
class Feed:
    id: str
    source: str
    url: str


@dataclass(frozen=True)
class GNewsDomain:
    domain: str
    source: str


@dataclass(frozen=True)
class Topic:
    key: str
    label: str
    gnews_query: str
    strong: tuple[str, ...]
    weak: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    require_context: tuple[str, ...] = ()
    logistics_downrank: tuple[str, ...] = ()
    threshold: int = 4
    widen_days: int = 30


@dataclass
class Config:
    contact: str | None
    user_agent_name: str
    delay_seconds: tuple[float, float]
    timeout_seconds: float
    max_attempts: int
    respect_robots: bool
    feeds: list[Feed]
    gnews_enabled: bool
    gnews_when: str
    gnews_domains: list[GNewsDomain]
    topics: list[Topic]  # urutan = pemecah seri
    ecological_link: tuple[str, ...] = ()
    provinces: dict[str, list[str]] = field(default_factory=dict)
    pin_urls: tuple[str, ...] = ()
    block_urls: tuple[str, ...] = ()

    @property
    def user_agent(self) -> str:
        return f"{self.user_agent_name} (+{self.contact or 'kontak-belum-diset'})"

    @property
    def robots_token(self) -> str:
        return self.user_agent_name.split("/")[0]

    @property
    def topic_labels(self) -> dict[str, str]:
        return {t.key: t.label for t in self.topics}


def _read(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(config_dir: Path | None = None) -> Config:
    d = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    src = _read(d / "sources.yaml")
    top = _read(d / "topics.yaml")
    prov = _read(d / "provinces.yaml")
    ovr = _read(d / "overrides.yaml")

    # Kontak hanya dari env (jangan di-commit). Divalidasi di CLI sebelum fetch nyata.
    contact = (os.environ.get(CONTACT_ENV) or "").strip() or None

    http = src.get("http", {})
    delay = http.get("delay_seconds", [1.0, 2.0])
    gn = src.get("gnews", {})

    topics = []
    for key, t in top["topics"].items():
        topics.append(
            Topic(
                key=key,
                label=t["label"],
                gnews_query=t["gnews_query"],
                strong=tuple(t.get("strong", [])),
                weak=tuple(t.get("weak", [])),
                exclude=tuple(t.get("exclude", [])),
                require_context=tuple(t.get("require_context", [])),
                logistics_downrank=tuple(t.get("logistics_downrank", [])),
                threshold=int(t.get("threshold", 4)),
                widen_days=int(t.get("widen_days", 30)),
            )
        )

    feeds = [Feed(**f) for f in src.get("feeds", [])]
    ids = [f.id for f in feeds]
    if len(ids) != len(set(ids)):
        raise ValueError("id feed di sources.yaml harus unik")

    return Config(
        contact=contact,
        user_agent_name=src.get("user_agent_name", "AshenNewsBot/0.1"),
        delay_seconds=(float(delay[0]), float(delay[1])),
        timeout_seconds=float(http.get("timeout_seconds", 20)),
        max_attempts=int(http.get("max_attempts", 3)),
        respect_robots=bool(http.get("respect_robots", True)),
        feeds=feeds,
        gnews_enabled=bool(gn.get("enabled", True)),
        gnews_when=str(gn.get("when", "7d")),
        gnews_domains=[GNewsDomain(**x) for x in gn.get("domains", [])],
        topics=topics,
        ecological_link=tuple(top.get("ecological_link", [])),
        provinces={k: list(v) for k, v in (prov.get("provinces") or {}).items()},
        pin_urls=tuple(ovr.get("pin_urls") or ()),
        block_urls=tuple(ovr.get("block_urls") or ()),
    )
