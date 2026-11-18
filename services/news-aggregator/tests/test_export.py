import json
from datetime import datetime, timedelta, timezone

from ashen_news.cli import main
from ashen_news.config import load_config
from ashen_news.db import Database, NewArticle, utcnow_iso
from ashen_news.export import build_export, seed_from_snapshot, write_snapshot
from ashen_news.feeds import parse_feed

NOW = datetime(2026, 11, 18, 0, 0, tzinfo=timezone.utc)


def art(i, topic, days_ago, secondary=None, location=None, eco_link=0):
    return NewArticle(
        canonical_url=f"https://x.com/{topic}/{i}",
        url=f"https://x.com/{topic}/{i}",
        title=f"Judul {topic} {i}",
        title_norm=f"judul {topic} {i}",
        source="Antara",
        published_at=utcnow_iso(NOW - timedelta(days=days_ago)),
        topic=topic,
        topic_secondary=secondary,
        topic_score=4,
        matched_keywords="k",
        location=location,
        snippet="cuplikan",
        fetched_at=utcnow_iso(NOW),
        via="rss",
        eco_link=eco_link,
    )


def fresh_db():
    return Database.scratch_copy(__import__("pathlib").Path("/nonexistent.db"))


def test_window_widens_per_topic_including_90d_for_satwa():
    cfg = load_config()
    db = fresh_db()
    for i in range(4):
        db.insert(art(i, "banjir", 1))          # cukup di 7 hari
    db.insert(art(10, "satwa", 2))               # hanya 1 dalam 7 hari ...
    db.insert(art(11, "satwa", 40))              # ... + 2 dalam 90 hari (di luar 30 hari!)
    db.insert(art(12, "satwa", 75))
    db.insert(art(13, "satwa", 120))             # di luar 90 hari
    doc = build_export(db, cfg, NOW)
    assert doc["windowDays"]["banjir"] == 7
    assert doc["windowDays"]["satwa"] == 90
    assert doc["windowDays"]["pembalakan"] == 90
    assert doc["counts"]["Satwa Terdampak"] == 3
    assert doc["counts"]["Pembalakan Liar"] == 0


def test_eco_link_ranking_and_per_location_cap():
    cfg = load_config()
    db = fresh_db()
    # 3 berita banjir di Aceh: 2 logistik (eco=-1, baru) dan 1 kejadian (eco=0, sedikit lebih lama)
    db.insert(art(1, "banjir", 0, location="Aceh", eco_link=-1))
    db.insert(art(2, "banjir", 0, location="Aceh", eco_link=-1))
    db.insert(art(3, "banjir", 1, location="Aceh", eco_link=0))
    # 1 berita banjir dengan kaitan hutan di Sumbar (eco=2, lebih lama lagi)
    db.insert(art(4, "banjir", 3, location="Sumatera Barat", eco_link=2))
    doc = build_export(db, cfg, NOW)
    banjir_items = [i for i in doc["items"] if i["topic"] == "banjir"]
    # Aceh dibatasi maks 2, dan berita eco_link=2 tampil paling atas meski 3 hari lalu
    aceh_items = [i for i in banjir_items if i["location"] == "Aceh"]
    assert len(aceh_items) == 2
    assert banjir_items[0]["location"] == "Sumatera Barat" and banjir_items[0]["ecoLink"] == 2
    # Di antara Aceh, yang eco=0 harus mengalahkan salah satu yang eco=-1
    assert any(i["ecoLink"] == 0 for i in aceh_items)


def test_logistics_hidden_once_min_per_topic_met():
    cfg = load_config()
    db = fresh_db()
    # 3 berita kejadian nyata (eco >= 0) + 2 berita logistik (eco = -1)
    for i in range(3):
        db.insert(art(i, "banjir", 1, eco_link=0))
    db.insert(art(10, "banjir", 0, eco_link=-1))
    db.insert(art(11, "banjir", 0, eco_link=-1))
    doc = build_export(db, cfg, NOW)
    banjir_items = [i for i in doc["items"] if i["topic"] == "banjir"]
    assert len(banjir_items) == 3
    assert all(i["ecoLink"] >= 0 for i in banjir_items)


def test_overrides_pin_and_block():
    cfg = load_config()
    cfg.block_urls = ("https://x.com/banjir/1",)
    cfg.pin_urls = ("https://x.com/banjir/99",)
    db = fresh_db()
    db.insert(art(1, "banjir", 1, eco_link=5))   # diblokir meski eco_link tinggi
    db.insert(art(2, "banjir", 1, eco_link=2))
    db.insert(art(99, "banjir", 5, eco_link=-1))  # di-pin meski eco_link rendah & lama
    doc = build_export(db, cfg, NOW)
    urls = [i["url"] for i in doc["items"] if i["topic"] == "banjir"]
    assert "https://x.com/banjir/1" not in urls
    assert urls[0] == "https://x.com/banjir/99"


def test_indonesian_pubdate_parsed():
    xml = (
        b'<?xml version="1.0"?><rss version="2.0"><channel>'
        b"<item><title>Orangutan</title><link>https://mongabay.co.id/a</link>"
        b"<pubDate>24 Okt 2026 05:00:31 +0000</pubDate><description>x</description></item>"
        b"</channel></rss>"
    )
    items = parse_feed(xml, "Mongabay Indonesia", "m")
    assert items[0].published_at == "2026-10-24T05:00:31Z"


def test_snapshot_written_only_when_changed_and_empty_refused(tmp_path):
    cfg = load_config()
    db = fresh_db()
    db.insert(art(1, "karhutla", 1, secondary="satwa", location="Riau"))
    out = tmp_path / "news.json"
    doc = build_export(db, cfg, NOW)
    assert write_snapshot(doc, out) == "written"
    later = build_export(db, cfg, NOW + timedelta(hours=6))
    assert write_snapshot(later, out) == "unchanged"       # hanya generatedAt yang beda
    item = json.loads(out.read_text())["items"][0]
    assert item["secondaryCategory"] == "Satwa Terdampak" and item["location"] == "Riau"
    empty = build_export(fresh_db(), cfg, NOW)
    assert write_snapshot(empty, out) == "refused_empty"
    assert json.loads(out.read_text())["items"]            # snapshot lama aman


def test_seed_roundtrip(tmp_path):
    cfg = load_config()
    db = fresh_db()
    db.insert(art(1, "banjir", 1, location="Aceh", eco_link=2))
    out = tmp_path / "news.json"
    write_snapshot(build_export(db, cfg, NOW), out)
    db2 = fresh_db()
    assert seed_from_snapshot(db2, out) == 1
    assert seed_from_snapshot(db2, out) == 0               # idempoten
    row = db2.conn.execute("SELECT location, eco_link FROM articles").fetchone()
    assert row["location"] == "Aceh" and row["eco_link"] == 2


def test_fetch_refuses_without_contact(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("ASHEN_NEWS_CONTACT")
    rc = main(["--db", str(tmp_path / "n.db"), "fetch", "--dry-run"])
    assert rc == 1
    assert "ASHEN_NEWS_CONTACT" in capsys.readouterr().err
