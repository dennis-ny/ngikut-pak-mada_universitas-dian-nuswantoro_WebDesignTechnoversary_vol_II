"""Ekspor SQLite -> JSON snapshot untuk Astro."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import SERVICE_ROOT, Config
from .db import Database, NewArticle, utcnow_iso
from .dedupe import canonical_url, normalize_title

DEFAULT_OUT = SERVICE_ROOT.parents[1] / "src" / "data" / "generated" / "news.json"
SCHEMA_VERSION = 1

WINDOW_DAYS = 7          # jendela normal
WIDEN_DAYS = 30          # default bila kategori sedikit artikel (dapat di-override per topik)
MIN_PER_TOPIC = 3        # di bawah ini -> perluas ke widen_days
MAX_PER_TOPIC = 12
MAX_PER_LOCATION = 2     # maks berita per (topik, provinsi) kecuali di-pin


def _item_id(canonical: str) -> str:
    return "n-" + hashlib.sha1(canonical.encode()).hexdigest()[:10]


def _select_topic_rows(
    rows: list,
    pinned_set: set[str],
    blocked_set: set[str],
    max_per_topic: int,
    max_per_location: int,
    min_per_topic: int = MIN_PER_TOPIC,
) -> list:
    filtered = [
        r for r in rows
        if r["canonical_url"] not in blocked_set and r["url"] not in blocked_set
    ]
    # Urutkan: pin_urls dulu, lalu eco_link menurun, lalu tanggal terbit menurun
    filtered.sort(
        key=lambda r: (
            1 if (r["canonical_url"] in pinned_set or r["url"] in pinned_set) else 0,
            int(r["eco_link"] or 0),
            r["published_at"] or r["fetched_at"] or "",
        ),
        reverse=True,
    )
    selected = []
    loc_counts: Counter[str] = Counter()
    for r in filtered:
        is_pinned = r["canonical_url"] in pinned_set or r["url"] in pinned_set
        eco = int(r["eco_link"] or 0)
        # Bila kejadian nyata (eco >= 0) sudah mencapai kuota minimum (min_per_topic),
        # lewati liputan logistik/pejabat/drainase murni (eco < 0) kecuali di-pin.
        if eco < 0 and not is_pinned and len(selected) >= min_per_topic:
            continue
        loc = r["location"]
        if loc and not is_pinned and max_per_location > 0:
            if loc_counts[loc] >= max_per_location:
                continue
            loc_counts[loc] += 1
        selected.append(r)
        if len(selected) >= max_per_topic:
            break
    return selected


def build_export(
    db: Database,
    cfg: Config,
    now: datetime | None = None,
    *,
    window_days: int = WINDOW_DAYS,
    widen_days: int | None = None,
    min_per_topic: int = MIN_PER_TOPIC,
    max_per_topic: int = MAX_PER_TOPIC,
    max_per_location: int = MAX_PER_LOCATION,
) -> dict:
    now = now or datetime.now(timezone.utc)
    labels = cfg.topic_labels
    pinned_set = {canonical_url(u) for u in cfg.pin_urls} | set(cfg.pin_urls)
    blocked_set = {canonical_url(u) for u in cfg.block_urls} | set(cfg.block_urls)

    items: list[dict] = []
    windows: dict[str, int] = {}
    for topic in cfg.topics:
        topic_widen = widen_days if widen_days is not None else topic.widen_days
        steps = sorted({window_days, WIDEN_DAYS, topic_widen})
        used = window_days
        selected_rows: list = []
        for days in steps:
            cutoff = utcnow_iso(now - timedelta(days=days))
            raw_rows = db.conn.execute(
                "SELECT * FROM articles WHERE topic = ? AND COALESCE(published_at, fetched_at) >= ?",
                (topic.key, cutoff),
            ).fetchall()
            selected_rows = _select_topic_rows(
                raw_rows, pinned_set, blocked_set, max_per_topic, max_per_location, min_per_topic
            )
            used = days
            if len(selected_rows) >= min_per_topic:
                break
        windows[topic.key] = used
        for r in selected_rows:
            items.append(
                {
                    "id": _item_id(r["canonical_url"]),
                    "title": r["title"],
                    "topic": r["topic"],
                    "category": labels[r["topic"]],
                    "topicSecondary": r["topic_secondary"],
                    "secondaryCategory": labels.get(r["topic_secondary"]) if r["topic_secondary"] else None,
                    "ecoLink": int(r["eco_link"] or 0),
                    "source": r["source"],
                    "publishedAt": r["published_at"] or r["fetched_at"],
                    "location": r["location"],
                    "summary": r["snippet"],
                    "image": r["image_url"],
                    "url": r["url"],
                }
            )
    # Urutkan gabungan ("Semua"): artikel pinned -> eco_link tertinggi -> tanggal terbaru:
    items.sort(
        key=lambda i: (
            1 if (canonical_url(i["url"]) in pinned_set or i["url"] in pinned_set) else 0,
            i["ecoLink"],
            i["publishedAt"],
        ),
        reverse=True,
    )
    counts = {labels[t.key]: sum(1 for i in items if i["topic"] == t.key) for t in cfg.topics}
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": utcnow_iso(now),
        "windowDays": windows,
        "counts": counts,
        "items": items,
    }


def _comparable(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k != "generatedAt"}


def write_snapshot(doc: dict, out: Path, *, allow_empty: bool = False) -> str:
    """Tulis hanya bila isi berubah. Return: 'written' | 'unchanged' | 'refused_empty'."""
    existing = None
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = None
    if not doc["items"] and existing and existing.get("items") and not allow_empty:
        return "refused_empty"  # jangan timpa snapshot yang ada dengan DB kosong (mis. cache hilang)
    if existing and _comparable(existing) == _comparable(doc):
        return "unchanged"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "written"


def seed_from_snapshot(db: Database, snapshot: Path, now: datetime | None = None) -> int:
    """Isi DB kosong dari snapshot terkomit (fallback bila cache DB di CI hilang)."""
    if not snapshot.exists():
        return 0
    doc = json.loads(snapshot.read_text(encoding="utf-8"))
    fetched = utcnow_iso(now)
    n = 0
    for it in doc.get("items", []):
        canon = canonical_url(it["url"])
        if db.get_by_canonical(canon):
            continue
        db.insert(
            NewArticle(
                canonical_url=canon,
                url=it["url"],
                title=it["title"],
                title_norm=normalize_title(it["title"]),
                source=it["source"],
                published_at=it.get("publishedAt"),
                topic=it["topic"],
                topic_secondary=it.get("topicSecondary"),
                topic_score=0.0,
                matched_keywords="(snapshot)",
                location=it.get("location"),
                snippet=it.get("summary"),
                fetched_at=fetched,
                via="rss",
                eco_link=int(it.get("ecoLink", 0)),
                image_url=it.get("image"),
            )
        )
        n += 1
    db.commit()
    return n
