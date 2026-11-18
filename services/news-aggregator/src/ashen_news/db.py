"""SQLite: tabel articles & feed_runs."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY,
  canonical_url TEXT NOT NULL UNIQUE,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  title_norm TEXT NOT NULL,
  source TEXT NOT NULL,
  published_at TEXT,
  topic TEXT NOT NULL,
  topic_secondary TEXT,
  topic_score REAL,
  eco_link INTEGER NOT NULL DEFAULT 0,
  matched_keywords TEXT,
  location TEXT,
  snippet TEXT,
  image_url TEXT,
  fetched_at TEXT NOT NULL,
  via TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_articles_topic_pub ON articles(topic, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles(published_at);

CREATE TABLE IF NOT EXISTS feed_runs (
  id INTEGER PRIMARY KEY,
  feed_id TEXT NOT NULL,
  run_at TEXT NOT NULL,
  status TEXT NOT NULL,      -- ok | error | blocked | robots | not_feed
  http_code INTEGER,
  items_seen INTEGER NOT NULL DEFAULT 0,
  items_new INTEGER NOT NULL DEFAULT 0,
  error TEXT
);
CREATE INDEX IF NOT EXISTS idx_feed_runs_feed ON feed_runs(feed_id, run_at DESC);
"""


@dataclass
class NewArticle:
    canonical_url: str
    url: str
    title: str
    title_norm: str
    source: str
    published_at: str | None
    topic: str
    topic_secondary: str | None
    topic_score: float
    matched_keywords: str
    location: str | None
    snippet: str | None
    fetched_at: str
    via: str
    eco_link: int = 0
    image_url: str | None = None


def utcnow_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


class Database:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(articles)").fetchall()}
        if "eco_link" not in cols:
            self.conn.execute("ALTER TABLE articles ADD COLUMN eco_link INTEGER NOT NULL DEFAULT 0")
            self.conn.commit()
        if "image_url" not in cols:
            self.conn.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
            self.conn.commit()

    @classmethod
    def open(cls, path: Path) -> "Database":
        path.parent.mkdir(parents=True, exist_ok=True)
        return cls(sqlite3.connect(path))

    @classmethod
    def scratch_copy(cls, path: Path) -> "Database":
        """Salinan in-memory dari DB (untuk dry-run): tulis apa pun, tak ada yang tersimpan."""
        mem = sqlite3.connect(":memory:")
        if path.exists():
            src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            src.backup(mem)
            src.close()
        return cls(mem)

    # -- articles -----------------------------------------------------
    def get_by_canonical(self, canonical: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM articles WHERE canonical_url = ?", (canonical,)).fetchone()

    def similar_candidates(self, when_iso: str, days: int) -> list[sqlite3.Row]:
        center = datetime.strptime(when_iso, "%Y-%m-%dT%H:%M:%SZ")
        lo = (center - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        hi = (center + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.conn.execute(
            "SELECT id, title_norm, via, canonical_url FROM articles "
            "WHERE COALESCE(published_at, fetched_at) BETWEEN ? AND ?",
            (lo, hi),
        ).fetchall()

    def insert(self, a: NewArticle) -> int:
        cur = self.conn.execute(
            "INSERT INTO articles (canonical_url,url,title,title_norm,source,published_at,topic,topic_secondary,"
            "topic_score,eco_link,matched_keywords,location,snippet,image_url,fetched_at,via) "
            "VALUES (:canonical_url,:url,:title,:title_norm,:source,:published_at,:topic,:topic_secondary,"
            ":topic_score,:eco_link,:matched_keywords,:location,:snippet,:image_url,:fetched_at,:via)",
            a.__dict__,
        )
        return int(cur.lastrowid)

    def upgrade_from_direct(self, row_id: int, a: NewArticle) -> None:
        """Ganti entri Google News dengan versi RSS langsung (URL asli) dari artikel yang sama."""
        d = dict(a.__dict__, id=row_id)
        self.conn.execute(
            "UPDATE articles SET canonical_url=:canonical_url,url=:url,source=:source,via=:via,"
            "eco_link=:eco_link,snippet=COALESCE(:snippet,snippet),image_url=COALESCE(:image_url,image_url),"
            "published_at=COALESCE(:published_at,published_at) WHERE id=:id",
            d,
        )

    def count_articles(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0])

    # -- feed_runs ------------------------------------------------------
    def record_run(self, feed_id: str, run_at: str, status: str, items_seen: int, items_new: int,
                   error: str | None = None, http_code: int | None = None) -> None:
        self.conn.execute(
            "INSERT INTO feed_runs (feed_id,run_at,status,http_code,items_seen,items_new,error) VALUES (?,?,?,?,?,?,?)",
            (feed_id, run_at, status, http_code, items_seen, items_new, error),
        )
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.conn.execute("DELETE FROM feed_runs WHERE run_at < ?", (cutoff,))

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
