"""Parsing feed RSS/Atom -> RawItem (judul, URL, tanggal, cuplikan pendek)."""

from __future__ import annotations

import calendar
import email.utils
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlsplit

import feedparser

SNIPPET_MAX = 300
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_IMG_EXT = re.compile(r"\.(jpe?g|png|webp|avif)(\?|$)", re.IGNORECASE)
_HTML_IMG = re.compile(r'<img[^>]+src=["\'](https?://[^"\'>\s]+)["\']', re.IGNORECASE)

# Beberapa feed Indonesia (mis. Mongabay) menulis nama bulan/hari Bahasa Indonesia di <pubDate>
# seperti "24 Okt 2026 05:00:31 +0000" sehingga feedparser gagal mem-parse tanpa normalisasi.
_ID_DATE_TOKENS = {
    "januari": "Jan",
    "februari": "Feb",
    "pebruari": "Feb",
    "maret": "Mar",
    "april": "Apr",
    "mei": "May",
    "juni": "Jun",
    "juli": "Jul",
    "agustus": "Aug",
    "agu": "Aug",
    "ags": "Aug",
    "september": "Sep",
    "oktober": "Oct",
    "okt": "Oct",
    "november": "Nov",
    "nopember": "Nov",
    "nop": "Nov",
    "desember": "Dec",
    "des": "Dec",
    "senin": "Mon",
    "sen": "Mon",
    "selasa": "Tue",
    "sel": "Tue",
    "rabu": "Wed",
    "rab": "Wed",
    "kamis": "Thu",
    "kam": "Thu",
    "jumat": "Fri",
    "jum": "Fri",
    "sabtu": "Sat",
    "sab": "Sat",
    "minggu": "Sun",
    "min": "Sun",
}
_ID_DATE_RE = re.compile(
    r"\b(" + "|".join(sorted(_ID_DATE_TOKENS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


@dataclass
class RawItem:
    title: str
    url: str
    source: str
    via: str  # "rss" | "gnews"
    published_at: str | None  # ISO-8601 UTC
    snippet: str | None
    feed_id: str
    image_url: str | None = None


def _upgrade_image_quality(url: str) -> str:
    """Naikkan parameter lebar thumbnail kecil (mis. ?w=360 di CDN Detik/CNN) ke w=720."""
    if "akcdn.detik.net.id" in url:
        return re.sub(r"([?&])w=\d+", r"\g<1>w=720", url)
    return url


def extract_image(entry: dict) -> str | None:
    """Ambil URL thumbnail resmi dari tag RSS (media, enclosure, img, atau HTML description)."""
    for m in (entry.get("media_content") or []) + (entry.get("media_thumbnail") or []):
        u = (m.get("url") or "").strip()
        if u.startswith(("https://", "http://")):
            return _upgrade_image_quality(u)
    for l in (entry.get("enclosures") or []) + (entry.get("links") or []):
        u = (l.get("href") or l.get("url") or "").strip()
        t = (l.get("type") or "").lower()
        if u.startswith(("https://", "http://")) and ("image" in t or _IMG_EXT.search(u)):
            return _upgrade_image_quality(u)
    img_tag = (entry.get("img") or "").strip()
    if img_tag.startswith(("https://", "http://")):
        return _upgrade_image_quality(img_tag)
    blobs = [entry.get("summary") or "", entry.get("description") or ""]
    for c in entry.get("content") or []:
        blobs.append(c.get("value") or "")
    for b in blobs:
        m = _HTML_IMG.search(b)
        if m:
            return _upgrade_image_quality(m.group(1).strip())
    return None


def clean_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = _TAG.sub(" ", html.unescape(raw))
    text = html.unescape(text)
    return _WS.sub(" ", text).strip()


def make_snippet(raw: str | None, title: str = "", limit: int = SNIPPET_MAX) -> str | None:
    """Cuplikan pendek (<= limit karakter, dipotong di batas kata). Bukan isi artikel penuh."""
    text = clean_text(raw)
    if not text:
        return None
    # Cuplikan yang hanya mengulang judul tidak berguna.
    if title and text.lower().startswith(title.lower()) and len(text) <= len(title) + 40:
        return None
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return cut + "…"


def _iso(struct_time, raw_str: str | None = None) -> str | None:
    if struct_time:
        ts = calendar.timegm(struct_time)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if raw_str:
        norm = _ID_DATE_RE.sub(lambda m: _ID_DATE_TOKENS[m.group(1).lower()], raw_str.strip())
        try:
            dt = email.utils.parsedate_to_datetime(norm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            return None
    return None


def parse_feed(content: bytes, source: str, feed_id: str, via: str = "rss") -> list[RawItem]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Feed tidak bisa di-parse: {parsed.bozo_exception!r}")
    items: list[RawItem] = []
    for e in parsed.entries:
        title = clean_text(e.get("title"))
        url = (e.get("link") or "").strip()
        if not title or not url:
            continue
        pub_parsed = e.get("published_parsed") if "published" in e else e.get("updated_parsed")
        published = _iso(
            pub_parsed,
            e.get("published") or e.get("updated"),
        )
        summary = e.get("summary") or e.get("description")
        items.append(
            RawItem(
                title=title,
                url=url,
                source=source,
                via=via,
                published_at=published,
                snippet=make_snippet(summary, title),
                feed_id=feed_id,
                image_url=extract_image(e),
            )
        )
    return items


def gnews_url(query: str, domain: str, when: str) -> str:
    q = f"({query}) site:{domain} when:{when}"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=id&gl=ID&ceid=ID:id"


def _domain_matches(host: str, domain: str) -> bool:
    host = host.lower()
    return host == domain or host.endswith("." + domain)


def parse_gnews(content: bytes, domain: str, source: str, feed_id: str) -> list[RawItem]:
    """Item Google News: URL dibiarkan apa adanya; sumber divalidasi lewat <source url>."""
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Feed GNews tidak bisa di-parse: {parsed.bozo_exception!r}")
    items: list[RawItem] = []
    for e in parsed.entries:
        src = e.get("source") or {}
        src_url = src.get("href", "")
        if src_url and not _domain_matches(urlsplit(src_url).netloc, domain):
            continue  # bukan dari domain whitelist yang diminta
        title = clean_text(e.get("title"))
        src_title = clean_text(src.get("title", ""))
        if src_title and title.endswith(f" - {src_title}"):
            title = title[: -len(f" - {src_title}")].rstrip()
        url = (e.get("link") or "").strip()
        if not title or not url:
            continue
        items.append(
            RawItem(
                title=title,
                url=url,
                source=source,
                via="gnews",
                published_at=_iso(e.get("published_parsed"), e.get("published")),
                snippet=None,  # deskripsi GNews hanya mengulang judul
                feed_id=feed_id,
            )
        )
    return items
