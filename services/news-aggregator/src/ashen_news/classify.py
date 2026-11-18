"""Klasifikasi topik berbasis keyword berbobot + skor eco_link + pencocokan provinsi."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import Config, Topic

STRONG_TITLE, STRONG_BODY = 4, 2
WEAK_TITLE, WEAK_BODY = 2, 1


def _term_re(term: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(term.strip()).replace(r"\ ", r"\s+") + r"(?!\w)", re.IGNORECASE)


@dataclass
class _CompiledTopic:
    topic: Topic
    strong: list[tuple[str, re.Pattern]]
    weak: list[tuple[str, re.Pattern]]
    exclude: list[re.Pattern]
    context: list[re.Pattern]
    logistics_downrank: list[re.Pattern]


@dataclass
class Classification:
    primary: str | None
    secondary: str | None
    primary_score: float
    eco_link: int = 0
    scores: dict[str, int] = field(default_factory=dict)
    matched: dict[str, list[str]] = field(default_factory=dict)
    excluded: dict[str, str] = field(default_factory=dict)  # topik -> pola exclude yang cocok
    missing_context: list[str] = field(default_factory=list)


class Classifier:
    def __init__(self, config: Config) -> None:
        self._order = [t.key for t in config.topics]
        self._eco_terms = [(term, _term_re(term)) for term in config.ecological_link]
        self._topics = [
            _CompiledTopic(
                topic=t,
                strong=[(s, _term_re(s)) for s in t.strong],
                weak=[(s, _term_re(s)) for s in t.weak],
                exclude=[re.compile(p, re.IGNORECASE) for p in t.exclude],
                context=[_term_re(c) for c in t.require_context],
                logistics_downrank=[re.compile(p, re.IGNORECASE) for p in t.logistics_downrank],
            )
            for t in config.topics
        ]
        self._by_key = {ct.topic.key: ct for ct in self._topics}

    def classify(self, title: str, snippet: str | None) -> Classification:
        body = snippet or ""
        text = f"{title}\n{body}"
        res = Classification(primary=None, secondary=None, primary_score=0)
        for ct in self._topics:
            key = ct.topic.key
            hit = next((p.pattern for p in ct.exclude if p.search(text)), None)
            if hit:
                res.excluded[key] = hit
                continue
            score, matched = 0, []
            for term, rx in ct.strong:
                in_t, in_b = bool(rx.search(title)), bool(body and rx.search(body))
                if in_t or in_b:
                    score += STRONG_TITLE if in_t else STRONG_BODY
                    matched.append(term)
            if matched:  # kata lemah/ambigu hanya sah bila ditemani kata strong (pendamping)
                for term, rx in ct.weak:
                    in_t, in_b = bool(rx.search(title)), bool(body and rx.search(body))
                    if in_t or in_b:
                        score += WEAK_TITLE if in_t else WEAK_BODY
                        matched.append(term)
            if score <= 0:
                continue
            if ct.context:
                if not any(c.search(text) for c in ct.context):
                    res.missing_context.append(key)
                    continue
                score += 1  # bonus konteks dampak agar satwa terdampak bencana masuk topik utama satwa
            res.scores[key] = score
            res.matched[key] = matched

        passing = [(k, s) for k, s in res.scores.items() if s >= self._threshold(k)]
        # urut: skor turun, lalu urutan di topics.yaml
        passing.sort(key=lambda ks: (-ks[1], self._order.index(ks[0])))
        if passing:
            res.primary, res.primary_score = passing[0][0], passing[0][1]
            eco = sum(1 for _, rx in self._eco_terms if rx.search(text))
            ct_primary = self._by_key[res.primary]
            if eco == 0 and any(rx.search(text) for rx in ct_primary.logistics_downrank):
                eco = -1
            res.eco_link = eco
        if len(passing) > 1:
            res.secondary = passing[1][0]
        return res

    def _threshold(self, key: str) -> int:
        return self._by_key[key].topic.threshold


class LocationMatcher:
    """Cocokkan nama provinsi (kata utuh, terpanjang dulu). Kosong bila tidak ketemu."""

    MAX_LOCATIONS = 2

    def __init__(self, provinces: dict[str, list[str]]) -> None:
        pairs = [(alias, name) for name, aliases in provinces.items() for alias in aliases]
        pairs.sort(key=lambda p: -len(p[0]))
        self._pairs = [(_term_re(alias), name) for alias, name in pairs]

    def find(self, title: str, snippet: str | None) -> str | None:
        found: list[tuple[int, str]] = []
        for text in (title, snippet or ""):
            masked = text
            for rx, name in self._pairs:
                m = rx.search(masked)
                while m:
                    if name not in [n for _, n in found]:
                        found.append((len(found), name))
                    masked = masked[: m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
                    m = rx.search(masked)
            if found:
                break  # judul menang; cuplikan dipakai hanya bila judul tidak menyebut provinsi
        names = [n for _, n in found][: self.MAX_LOCATIONS]
        return " & ".join(names) if names else None
