"""Kanonikalisasi URL & deteksi judul mirip."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from rapidfuzz import fuzz

TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "source", "campaign", "mc_cid", "mc_eid", "igshid", "_ga"}
TITLE_SIMILARITY = 90
TITLE_WINDOW_DAYS = 3
_HOST_PREFIXES = ("www.", "m.", "amp.", "mobile.")
_PUNCT = re.compile(r"[^\w\s]")
_WS = re.compile(r"\s+")


def canonical_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower()
    if host.endswith(":80") or host.endswith(":443"):
        host = host.rsplit(":", 1)[0]
    for pre in _HOST_PREFIXES:
        if host.startswith(pre):
            host = host[len(pre):]
            break
    path = re.sub(r"/amp/?$", "", p.path)
    path = re.sub(r"/{2,}", "/", path)
    if len(path) > 1:
        path = path.rstrip("/")
    query = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS
    ]
    query.sort()
    return urlunsplit(("https", host, path or "/", urlencode(query), ""))


def normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKC", title).lower()
    t = _PUNCT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def titles_similar(a_norm: str, b_norm: str) -> bool:
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm:
        return True
    score = fuzz.token_sort_ratio(a_norm, b_norm)
    # token_set_ratio memberi 100 bila satu judul subset yang lain -> hanya untuk judul cukup panjang
    if min(len(a_norm.split()), len(b_norm.split())) >= 6:
        score = max(score, fuzz.token_set_ratio(a_norm, b_norm) - 4)
    return score >= TITLE_SIMILARITY
