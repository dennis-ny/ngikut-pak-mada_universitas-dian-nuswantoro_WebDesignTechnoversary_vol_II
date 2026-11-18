"""Uji pipeline end-to-end dengan transport HTTP palsu (tanpa jaringan)."""

import httpx
import pytest

from ashen_news.config import load_config
from ashen_news.db import Database
from ashen_news.http import Fetcher
from ashen_news.pipeline import run_fetch


def rss(items):
    body = "".join(
        f"<item><title>{t}</title><link>{u}</link><pubDate>Tue, 17 Nov 2026 03:00:00 +0000</pubDate>"
        f"<description>{d}</description></item>"
        for t, u, d in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


GOOD = rss(
    [
        ("Kabut asap karhutla selimuti Pekanbaru, Riau", "https://news.detik.com/berita/d-1/asap?utm_source=a", "ISPU berbahaya"),
        ("Harga cabai naik jelang Natal", "https://news.detik.com/berita/d-2/cabai", "ekonomi"),
        ("Banjir diskon akhir tahun", "https://news.detik.com/berita/d-3/diskon", "belanja"),
    ]
)
SAME_STORY_OTHER_SITE = rss(
    [("Kabut asap karhutla selimuti Pekanbaru, Riau!", "https://www.cnnindonesia.com/nasional/2026-asap", "x")]
)
CLOUDFLARE = b"<!DOCTYPE html><html><head><title>Just a moment...</title></head></html>"


def make_fetcher(routes, cfg):
    def handler(req: httpx.Request) -> httpx.Response:
        url = str(req.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(404)
        for key, (code, body) in routes.items():
            if key in url:
                if isinstance(body, Exception):
                    raise body
                return httpx.Response(code, content=body, headers={"content-type": "application/xml"})
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": cfg.user_agent})
    return Fetcher(cfg.user_agent, cfg.robots_token, delay=(0, 0), max_attempts=2, client=client, sleep=lambda s: None)


def test_failed_feeds_do_not_stop_others():
    cfg = load_config()
    routes = {
        "antaranews.com": (200, b"<rss><channel></channel></rss>"),  # feed kosong yang valid -> ok, 0 item
        "cnnindonesia.com": (200, SAME_STORY_OTHER_SITE),
        "news.detik.com": (200, GOOD),
        "rss.tempo.co": (200, CLOUDFLARE),          # challenge -> not_feed
        "mongabay.co.id": (503, b"err"),             # selalu 503 -> error setelah retry
    }
    f = make_fetcher(routes, cfg)
    db = Database.scratch_copy(__import__("pathlib").Path("/nonexistent.db"))
    report = run_fetch(cfg, f, db, include_gnews=False)

    by_id = {r.job_id: r for r in report.results}
    assert by_id["tempo-nasional"].status == "not_feed"
    assert by_id["mongabay-id"].status == "error"
    assert by_id["detik-berita"].status == "ok"
    assert by_id["cnn-nasional"].status == "ok"
    # artikel Detik masuk (1 lolos topik), CNN duplikat judul
    assert db.count_articles() == 1
    row = db.conn.execute("SELECT * FROM articles").fetchone()
    assert row["topic"] == "karhutla"
    assert row["location"] == "Riau"
    assert "utm_" not in row["canonical_url"]
    # feed CNN diproses lebih dulu; versi Detik adalah duplikat judul
    assert by_id["detik-berita"].duplicates == 1
    # feed_runs tercatat untuk semua job, termasuk yang gagal
    runs = {r["feed_id"]: r["status"] for r in db.conn.execute("SELECT feed_id, status FROM feed_runs")}
    assert runs["tempo-nasional"] == "not_feed" and runs["mongabay-id"] == "error"
    assert report.failed_jobs == 5  # tempo + 4 feed mongabay gagal; sisanya tetap jalan


def test_network_exception_isolated():
    cfg = load_config()
    routes = {
        "news.detik.com": (200, GOOD),
        "antaranews.com": (200, httpx.ConnectError("boom")),
    }
    f = make_fetcher(routes, cfg)
    db = Database.scratch_copy(__import__("pathlib").Path("/nonexistent.db"))
    report = run_fetch(cfg, f, db, include_gnews=False)
    by_id = {r.job_id: r for r in report.results}
    assert by_id["antara-terkini"].status == "error"
    assert by_id["detik-berita"].status == "ok" and db.count_articles() == 1


def test_robots_disallow_respected():
    cfg = load_config()

    def handler(req):
        if str(req.url).endswith("/robots.txt"):
            return httpx.Response(200, text="User-agent: *\nDisallow: /nasional/\n")
        return httpx.Response(200, content=GOOD)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    f = Fetcher(cfg.user_agent, cfg.robots_token, delay=(0, 0), client=client, sleep=lambda s: None)
    db = Database.scratch_copy(__import__("pathlib").Path("/nonexistent.db"))
    report = run_fetch(cfg, f, db, only=["cnn-nasional"], include_gnews=False)
    assert report.results[0].status == "robots"


def test_gnews_upgraded_by_direct_rss():
    cfg = load_config()
    cfg.gnews_enabled = True  # di config produksi nonaktif (robots.txt Google News)
    gnews = (
        '<?xml version="1.0"?><rss version="2.0"><channel>'
        "<item><title>Kabut asap karhutla selimuti Pekanbaru, Riau - Kompas.com</title>"
        "<link>https://news.google.com/rss/articles/CBMiXYZ?oc=5</link>"
        "<pubDate>Tue, 17 Nov 2026 03:00:00 +0000</pubDate>"
        '<source url="https://www.kompas.com">Kompas.com</source></item>'
        "</channel></rss>"
    ).encode()
    routes = {"news.google.com": (200, gnews)}
    f = make_fetcher(routes, cfg)
    db = Database.scratch_copy(__import__("pathlib").Path("/nonexistent.db"))
    run_fetch(cfg, f, db, only=["gnews:kompas.com:karhutla"])
    row = db.conn.execute("SELECT * FROM articles").fetchone()
    assert row["via"] == "gnews" and row["title"].endswith("Riau") and "google.com" in row["url"]

    f2 = make_fetcher({"news.detik.com": (200, GOOD)}, cfg)
    run_fetch(cfg, f2, db, only=["detik-berita"], include_gnews=False)
    assert db.count_articles() == 1
    row = db.conn.execute("SELECT * FROM articles").fetchone()
    assert row["via"] == "rss" and "detik.com" in row["url"]
