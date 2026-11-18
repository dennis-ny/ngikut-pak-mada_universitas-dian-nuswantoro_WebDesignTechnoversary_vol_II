"""Orkestrasi fetch: feed -> parse -> klasifikasi -> dedupe -> SQLite.

Satu feed yang gagal (jaringan, diblokir, robots, XML rusak) hanya dicatat di
`feed_runs`; feed lain tetap berjalan.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .classify import Classifier, Classification, LocationMatcher
from .config import Config
from .db import Database, NewArticle, utcnow_iso
from .dedupe import TITLE_WINDOW_DAYS, canonical_url, normalize_title, titles_similar
from .feeds import RawItem, gnews_url, parse_feed, parse_gnews
from .http import FetchError, Fetcher

log = logging.getLogger(__name__)


@dataclass
class Job:
    id: str
    kind: str  # "rss" | "gnews"
    source: str
    url: str
    domain: str | None = None


@dataclass
class JobResult:
    job_id: str
    status: str = "ok"
    error: str | None = None
    seen: int = 0
    accepted: int = 0
    duplicates: int = 0
    rejected: int = 0


@dataclass
class FetchReport:
    results: list[JobResult] = field(default_factory=list)
    records: list[dict] = field(default_factory=list)  # untuk audit dry-run

    @property
    def ok_jobs(self) -> int:
        return sum(1 for r in self.results if r.status == "ok")

    @property
    def failed_jobs(self) -> int:
        return len(self.results) - self.ok_jobs


def build_jobs(cfg: Config, only: list[str] | None = None, include_gnews: bool = True) -> list[Job]:
    jobs = [Job(f.id, "rss", f.source, f.url) for f in cfg.feeds]
    if include_gnews and cfg.gnews_enabled:
        for dom in cfg.gnews_domains:
            for topic in cfg.topics:
                jobs.append(
                    Job(
                        id=f"gnews:{dom.domain}:{topic.key}",
                        kind="gnews",
                        source=dom.source,
                        url=gnews_url(topic.gnews_query, dom.domain, cfg.gnews_when),
                        domain=dom.domain,
                    )
                )
    if only:
        jobs = [j for j in jobs if any(j.id == o or j.id.startswith(o) for o in only)]
    return jobs


def _reject_reason(cls: Classification) -> str:
    if cls.excluded and not cls.scores:
        return "excluded:" + ",".join(f"{k}" for k in cls.excluded)
    if cls.missing_context and not cls.scores:
        return "missing_context:" + ",".join(cls.missing_context)
    if cls.scores:
        return "below_threshold"
    return "no_keyword"


def _record(item: RawItem, decision: str, cls: Classification, location: str | None, extra: dict | None = None) -> dict:
    rec = {
        "decision": decision,
        "feed": item.feed_id,
        "via": item.via,
        "source": item.source,
        "title": item.title,
        "url": item.url,
        "published_at": item.published_at,
        "topic": cls.primary,
        "topic_secondary": cls.secondary,
        "eco_link": cls.eco_link,
        "scores": cls.scores,
        "matched": cls.matched,
        "excluded": cls.excluded,
        "location": location,
        "snippet": item.snippet,
        "image_url": item.image_url,
    }
    if extra:
        rec.update(extra)
    return rec


def _process_item(item: RawItem, db: Database, classifier: Classifier, locator: LocationMatcher,
                  fetched_at: str, res: JobResult, report: FetchReport) -> None:
    res.seen += 1
    cls = classifier.classify(item.title, item.snippet)
    if cls.primary is None:
        res.rejected += 1
        report.records.append(_record(item, "rejected", cls, None, {"reason": _reject_reason(cls)}))
        return

    canonical = canonical_url(item.url)
    location = locator.find(item.title, item.snippet)
    if db.get_by_canonical(canonical):
        res.duplicates += 1
        report.records.append(_record(item, "duplicate_url", cls, location))
        return

    title_norm = normalize_title(item.title)
    when = item.published_at or fetched_at
    new = NewArticle(
        canonical_url=canonical,
        url=item.url,
        title=item.title,
        title_norm=title_norm,
        source=item.source,
        published_at=item.published_at,
        topic=cls.primary,
        topic_secondary=cls.secondary,
        topic_score=float(cls.primary_score),
        matched_keywords=",".join(cls.matched.get(cls.primary, [])),
        location=location,
        snippet=item.snippet,
        fetched_at=fetched_at,
        via=item.via,
        eco_link=cls.eco_link,
        image_url=item.image_url,
    )

    for cand in db.similar_candidates(when, TITLE_WINDOW_DAYS):
        if titles_similar(title_norm, cand["title_norm"]):
            if item.via != "gnews" and cand["via"] == "gnews":
                db.upgrade_from_direct(cand["id"], new)
                res.duplicates += 1
                report.records.append(_record(item, "upgraded_gnews", cls, location, {"dup_of": cand["canonical_url"]}))
            else:
                res.duplicates += 1
                report.records.append(_record(item, "duplicate_title", cls, location, {"dup_of": cand["canonical_url"]}))
            return

    db.insert(new)
    res.accepted += 1
    report.records.append(_record(item, "accepted", cls, location))


def run_fetch(cfg: Config, fetcher: Fetcher, db: Database, *, dry_run: bool = False,
              only: list[str] | None = None, include_gnews: bool = True,
              now: datetime | None = None) -> FetchReport:
    classifier = Classifier(cfg)
    locator = LocationMatcher(cfg.provinces)
    report = FetchReport()
    jobs = build_jobs(cfg, only, include_gnews)
    log.info("Memulai fetch: %d job%s", len(jobs), " (DRY-RUN)" if dry_run else "")

    for job in jobs:
        fetched_at = utcnow_iso(now or datetime.now(timezone.utc))
        res = JobResult(job.id)
        try:
            content = fetcher.get_feed(job.url)
            if job.kind == "gnews":
                items = parse_gnews(content, job.domain or "", job.source, job.id)
            else:
                items = parse_feed(content, job.source, job.id)
            for item in items:
                try:
                    _process_item(item, db, classifier, locator, fetched_at, res, report)
                except Exception:  # satu artikel bermasalah tidak boleh menggagalkan feed
                    log.exception("Gagal memproses artikel dari %s: %s", job.id, item.url)
            log.info("%-34s ok  seen=%-3d baru=%-3d dup=%-3d tolak=%d", job.id, res.seen, res.accepted, res.duplicates, res.rejected)
        except FetchError as exc:
            res.status, res.error = exc.status, str(exc)
            log.warning("%-34s %s: %s", job.id, exc.status.upper(), exc)
        except Exception as exc:  # parse error, bug tak terduga: feed ini gagal, lanjut yang lain
            res.status, res.error = "error", f"{type(exc).__name__}: {exc}"
            log.exception("%-34s gagal tak terduga", job.id)
        db.record_run(job.id, fetched_at, res.status, res.seen, res.accepted, res.error)
        db.commit()
        report.results.append(res)
    return report
