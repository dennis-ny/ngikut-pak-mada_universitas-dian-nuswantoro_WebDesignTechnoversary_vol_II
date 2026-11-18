"""CLI: `ashen-news fetch [--dry-run]`, `export`, `seed`, `stats`, `reapply`, `reclassify`, `health`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classify import Classifier, LocationMatcher
from .config import CONTACT_ENV, DEFAULT_AUDIT_DIR, DEFAULT_DB_PATH, load_config
from .db import Database, utcnow_iso
from .export import DEFAULT_OUT, build_export, seed_from_snapshot, write_snapshot
from .http import Fetcher
from .pipeline import run_fetch

HEALTH_FAILS = 3
HEALTH_STALE_HOURS = 48


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)


def cmd_fetch(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_dir)
    if not cfg.contact:
        print(
            f"ERROR: env {CONTACT_ENV} belum diset (email atau URL repo untuk User-Agent). "
            "Fetch dibatalkan; tidak ada request yang dikirim.",
            file=sys.stderr,
        )
        return 1
    db_path = Path(args.db)
    db = Database.scratch_copy(db_path) if args.dry_run else Database.open(db_path)
    fetcher = Fetcher(
        user_agent=cfg.user_agent,
        robots_token=cfg.robots_token,
        delay=cfg.delay_seconds,
        timeout=cfg.timeout_seconds,
        max_attempts=cfg.max_attempts,
        respect_robots=cfg.respect_robots,
    )
    before = db.count_articles()
    report = run_fetch(
        cfg,
        fetcher,
        db,
        dry_run=args.dry_run,
        only=args.only or None,
        include_gnews=not args.no_gnews,
    )

    decisions = Counter(r["decision"] for r in report.records)
    topics = Counter(r["topic"] for r in report.records if r["decision"] == "accepted")
    print()
    print("=" * 64)
    print(("DRY-RUN (tidak ada yang disimpan)" if args.dry_run else "FETCH SELESAI") + f"  |  UA: {cfg.user_agent}")
    print(f"Job OK: {report.ok_jobs}  Gagal: {report.failed_jobs}")
    for r in report.results:
        if r.status != "ok":
            print(f"  ! {r.job_id}: {r.status} — {r.error}")
    print("Keputusan:", dict(decisions))
    labels = cfg.topic_labels
    print("Artikel baru per topik:", {labels.get(k, k): v for k, v in topics.items()})
    print(f"Total artikel di DB: {before} -> {db.count_articles()}" + (" (salinan sementara)" if args.dry_run else ""))

    if args.dry_run:
        audit_dir = Path(args.audit_dir)
        audit_dir.mkdir(parents=True, exist_ok=True)
        out = audit_dir / f"fetch-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for rec in report.records:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Laporan audit klasifikasi: {out}")
        print("  Tinjau: jq -c 'select(.decision==\"accepted\")|[.topic,.eco_link,.title,.location]' <file>")
        print("          jq -c 'select(.decision==\"rejected\")|[.reason,.title]' <file>")
    db.close()
    return 2 if report.results and report.ok_jobs == 0 else 0


def cmd_health(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_dir)
    db = Database.open(Path(args.db))
    now = datetime.now(timezone.utc)
    stale_cut = utcnow_iso(now - timedelta(hours=HEALTH_STALE_HOURS))
    ids = [f.id for f in cfg.feeds]
    ids += [r["feed_id"] for r in db.conn.execute("SELECT DISTINCT feed_id FROM feed_runs WHERE feed_id LIKE 'gnews:%'")]
    unhealthy = 0
    for fid in ids:
        runs = db.conn.execute(
            "SELECT status, run_at, items_seen, error FROM feed_runs WHERE feed_id=? ORDER BY run_at DESC, id DESC LIMIT ?",
            (fid, HEALTH_FAILS),
        ).fetchall()
        if not runs:
            print(f"?  {fid}: belum pernah dijalankan")
            continue
        problems = []
        if len(runs) >= HEALTH_FAILS and all(r["status"] != "ok" for r in runs):
            problems.append(f"gagal {HEALTH_FAILS}x berturut-turut ({runs[0]['status']}: {runs[0]['error']})")
        if len(runs) >= HEALTH_FAILS and all(r["status"] == "ok" and r["items_seen"] == 0 for r in runs):
            problems.append("0 item selama beberapa run")
        last_ok = db.conn.execute(
            "SELECT MAX(run_at) FROM feed_runs WHERE feed_id=? AND status='ok' AND items_seen>0", (fid,)
        ).fetchone()[0]
        if last_ok is None or last_ok < stale_cut:
            problems.append(f"tidak ada item sejak {last_ok or 'tidak pernah'}")
        if problems:
            unhealthy += 1
            print(f"✗  {fid}: " + "; ".join(problems))
        else:
            print(f"✓  {fid}")
    db.close()
    return 1 if unhealthy else 0


def cmd_export(args: argparse.Namespace) -> int:
    cfg = load_config(args.config_dir)
    db = Database.open(Path(args.db))
    doc = build_export(db, cfg)
    db.close()
    out = Path(args.out)
    result = write_snapshot(doc, out, allow_empty=args.allow_empty)
    print(f"export: {result} -> {out}  counts={doc['counts']}  window={doc['windowDays']}")
    return 3 if result == "refused_empty" else 0


def cmd_seed(args: argparse.Namespace) -> int:
    db = Database.open(Path(args.db))
    if db.count_articles() > 0 and not args.force:
        print("seed: DB tidak kosong, dilewati")
        db.close()
        return 0
    n = seed_from_snapshot(db, Path(args.snapshot))
    print(f"seed: {n} artikel dimuat dari {args.snapshot}")
    db.close()
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    db = Database.open(Path(args.db))
    q = db.conn.execute
    total = q("SELECT COUNT(*) FROM articles").fetchone()[0]
    print(f"Total artikel: {total}")
    rng = q("SELECT MIN(published_at), MAX(published_at), MIN(fetched_at) FROM articles").fetchone()
    print(f"Terbit: {rng[0]} .. {rng[1]}   pertama diambil: {rng[2]}")
    print("Per topik (primer / sekunder terisi / rata-rata eco_link):")
    for r in q(
        "SELECT topic, COUNT(*) n, SUM(topic_secondary IS NOT NULL) sec, ROUND(AVG(eco_link), 2) eco "
        "FROM articles GROUP BY topic ORDER BY n DESC"
    ):
        print(f"  {r['topic']:<11} {r['n']:>4}   sekunder: {r['sec'] or 0:<3}  avg_eco: {r['eco']}")
    print("Per sumber:", {r["source"]: r["n"] for r in q("SELECT source, COUNT(*) n FROM articles GROUP BY source")})
    sec = q("SELECT topic, topic_secondary, COUNT(*) n FROM articles WHERE topic_secondary IS NOT NULL GROUP BY 1,2").fetchall()
    print("topic_secondary pernah terisi:", "YA " + str([tuple(r) for r in sec]) if sec else "BELUM")
    db.close()
    return 0


def cmd_reapply(args: argparse.Namespace) -> int:
    """Terapkan ulang aturan klasifikasi saat ini ke artikel yang sudah tersimpan (default: hanya tampilkan)."""
    cfg = load_config(args.config_dir)
    clf, loc = Classifier(cfg), LocationMatcher(cfg.provinces)
    db = Database.open(Path(args.db))
    dropped = updated = 0
    for r in db.conn.execute(
        "SELECT id, title, snippet, topic, topic_secondary, eco_link, location FROM articles"
    ).fetchall():
        c = clf.classify(r["title"], r["snippet"])
        new_loc = loc.find(r["title"], r["snippet"])
        if c.primary is None:
            dropped += 1
            print(f"HAPUS  [{r['topic']}] {r['title'][:100]}")
            if args.apply:
                db.conn.execute("DELETE FROM articles WHERE id=?", (r["id"],))
        elif (c.primary, c.secondary, c.eco_link, new_loc) != (
            r["topic"],
            r["topic_secondary"],
            int(r["eco_link"] or 0),
            r["location"],
        ):
            updated += 1
            print(
                f"UBAH   {r['topic']}/{r['topic_secondary']} (eco={r['eco_link']}) -> "
                f"{c.primary}/{c.secondary} (eco={c.eco_link})  {r['title'][:85]}"
            )
            if args.apply:
                db.conn.execute(
                    "UPDATE articles SET topic=?, topic_secondary=?, topic_score=?, eco_link=?, "
                    "matched_keywords=?, location=? WHERE id=?",
                    (
                        c.primary,
                        c.secondary,
                        float(c.primary_score),
                        c.eco_link,
                        ",".join(c.matched.get(c.primary, [])),
                        new_loc,
                        r["id"],
                    ),
                )
    if args.apply:
        db.commit()
    print(f"{'DITERAPKAN' if args.apply else 'DRY-RUN (tambahkan --apply)'}: hapus={dropped} ubah={updated}")
    db.close()
    return 0


def cmd_reclassify(args: argparse.Namespace) -> int:
    """Jalankan ulang klasifikasi atas laporan audit lama (tanpa jaringan) untuk menguji perubahan keyword."""
    cfg = load_config(args.config_dir)
    clf, loc = Classifier(cfg), LocationMatcher(cfg.provinces)
    changed = 0
    for line in Path(args.audit_file).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        c = clf.classify(rec["title"], rec.get("snippet"))
        old = rec.get("topic") if rec["decision"] != "rejected" else None
        if c.primary != old or args.all:
            changed += 1
            print(
                f"{(old or '-'):<10} -> {(c.primary or '-'):<10} sec={c.secondary or '-':<10} eco={c.eco_link:<2} "
                f"[{rec['feed']}] {rec['title'][:85]}  | {loc.find(rec['title'], rec.get('snippet')) or ''}"
            )
    print(f"{changed} baris berubah/ditampilkan")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ashen-news", description=__doc__)
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--config-dir", default=None)
    p.add_argument("--db", default=str(DEFAULT_DB_PATH))
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="ambil feed, klasifikasi, dedupe, simpan")
    f.add_argument("--dry-run", action="store_true", help="jalankan penuh tapi tidak menyimpan; tulis laporan audit JSONL")
    f.add_argument("--only", action="append", help="batasi ke job id/prefiks (boleh berulang), mis. --only cnn-nasional")
    f.add_argument("--no-gnews", action="store_true", help="lewati Google News")
    f.add_argument("--audit-dir", default=str(DEFAULT_AUDIT_DIR))
    f.set_defaults(func=cmd_fetch)

    h = sub.add_parser("health", help="cek kesehatan feed dari feed_runs")
    h.set_defaults(func=cmd_health)

    e = sub.add_parser("export", help="tulis snapshot JSON untuk situs Astro")
    e.add_argument("--out", default=str(DEFAULT_OUT))
    e.add_argument("--allow-empty", action="store_true", help="izinkan menimpa snapshot dengan hasil kosong")
    e.set_defaults(func=cmd_export)

    sd = sub.add_parser("seed", help="isi DB kosong dari snapshot terkomit")
    sd.add_argument("--snapshot", default=str(DEFAULT_OUT))
    sd.add_argument("--force", action="store_true")
    sd.set_defaults(func=cmd_seed)

    st = sub.add_parser("stats", help="ringkasan isi DB (termasuk apakah topic_secondary pernah terisi)")
    st.set_defaults(func=cmd_stats)

    ra = sub.add_parser("reapply", help="terapkan ulang aturan klasifikasi ke DB (hapus yang kini ditolak)")
    ra.add_argument("--apply", action="store_true")
    ra.set_defaults(func=cmd_reapply)

    rc = sub.add_parser("reclassify", help="uji ulang klasifikasi dari file audit lama (offline)")
    rc.add_argument("audit_file")
    rc.add_argument("--all", action="store_true")
    rc.set_defaults(func=cmd_reclassify)

    args = p.parse_args(argv)
    _setup_logging(args.verbose)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
