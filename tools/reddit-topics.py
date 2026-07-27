#!/usr/bin/env python3
"""reddit-topics.py — what people are actually asking about warranties, receipts
and durable purchases, right now.

Feeds the weekly blog job (see prompt.md) with real reader demand instead of
whatever the model imagines shoppers worry about.

    python3 tools/reddit-topics.py                 # ranked digest, ~60 lines
    python3 tools/reddit-topics.py --json          # same data, machine-readable
    python3 tools/reddit-topics.py --refresh       # ignore the cache

WHY RSS AND NOT THE JSON API: reddit.com/r/<sub>/top.json returns 403 to both a
datacenter IP and a home IP now. The Atom feed at /r/<sub>/top/.rss is still
served, so that is what this uses. It is rate-limited though: hammer it and you
get 429s, which is why requests are paced, retried with backoff, and cached to
.cache/ for a day.

WHY A SCRIPT AND NOT A FEW CURL COMMANDS IN THE BRIEF: the Hermes agent's
terminal blocks `-c` / `-e` flags, so `python3 -c '...'` and clever one-liners
fail at runtime with BLOCKED. And raw feeds are ~50 KB each — a dozen of them
would bury the model's context. A plain command that prints a small digest
survives both constraints.

Failure is not fatal: if every feed fails, this exits 2 having printed a clear
message, and the brief falls back to the ranked topic bank in prompt.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "reddit-topics"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
ATOM = {"a": "http://www.w3.org/2005/Atom"}

# Where people ask about warranties, receipts, product longevity and claims.
# Ordered roughly by signal-to-noise for this topic.
SUBREDDITS = [
    "personalfinance", "BuyItForLife", "Frugal", "appliances",
    "HomeImprovement", "homeowners", "applehelp", "techsupport",
    "Insurance", "DIY", "smallbusiness", "PhoneRepair",
]
WINDOWS = ["month", "year"]

# Theme buckets. A title can land in several; each is counted once per theme.
# Keep these lowercase and substring-matched — cheap, and good enough to rank.
THEMES: dict[str, tuple[str, list[str]]] = {
    "warranty-tracking": ("Keeping track of warranties and their expiry dates", [
        "keep track", "track my", "keep track of warrant", "warranty expir",
        "expire", "expiration", "when does my warranty", "forgot the warranty",
        "how do you track", "spreadsheet"]),
    "receipts-organizing": ("Organising receipts and purchase paperwork", [
        "receipt", "receipts", "organize", "organise", "filing", "paperwork",
        "shoebox", "scan", "digital copy", "keep receipts", "store receipts"]),
    "proof-of-purchase": ("Proof of purchase — lost, faded or missing", [
        "proof of purchase", "lost receipt", "no receipt", "faded receipt",
        "without a receipt", "order confirmation", "serial number", "cant find the receipt",
        "can't find the receipt"]),
    "extended-warranty": ("Extended warranties and protection plans", [
        "extended warranty", "protection plan", "applecare", "squaretrade",
        "asurion", "geek squad", "service plan", "worth it", "worth buying",
        "should i get the warranty", "add on warranty"]),
    "claims-and-returns": ("Making a warranty claim, RMA or return", [
        "warranty claim", "rma", "make a claim", "return", "refund", "replacement",
        "honor the warranty", "honour the warranty", "manufacturer", "denied",
        "how do i claim"]),
    "consumer-rights": ("Consumer rights and faulty-goods law", [
        "consumer rights", "statutory", "faulty", "refund rights", "chargeback",
        "small claims", "section 75", "sale of goods", "dispute", "my rights",
        "consumer protection"]),
    "repair-vs-replace": ("Repair it or replace it", [
        "repair or replace", "worth repairing", "worth fixing", "cost to fix",
        "fix or buy", "out of warranty repair", "should i repair", "replace or repair"]),
    "appliance-lifespan": ("How long appliances and gear actually last", [
        "how long do", "how long does", "lifespan", "last", "died", "broke",
        "stopped working", "failed", "how long should", "keeps breaking"]),
    "buying-durable": ("Which brands last — buy-it-for-life questions", [
        "which brand", "most reliable", "buy it for life", "bifl", "lasts longest",
        "best value", "durable", "reliable brand", "recommend a", "what brand"]),
    "product-registration": ("Registering products and activating warranties", [
        "register", "registration", "activate warranty", "warranty card",
        "register my", "do i need to register", "register the product"]),
    "tech-warranties": ("Phone, laptop and gadget warranties", [
        "applecare", "iphone warranty", "laptop warranty", "macbook", "battery",
        "cracked screen", "out of warranty", "warranty on my phone", "warranty on my laptop"]),
    "insurance-vs-warranty": ("Home/contents insurance vs a warranty", [
        "home insurance", "contents insurance", "accidental damage", "insurance claim",
        "deductible", "excess", "insured", "insurance or warranty"]),
    "big-ticket": ("Cars, furniture and other big-ticket guarantees", [
        "car warranty", "powertrain", "furniture warranty", "mattress warranty",
        "bumper to bumper", "vehicle warranty", "sofa warranty", "tv warranty"]),
    "scams-and-gotchas": ("Void warranties, denied claims and fine print", [
        "void", "voided", "denied", "scam", "loophole", "fine print", "exclusion",
        "refuse to", "wont honor", "won't honor", "wont honour", "won't honour"]),
    "home-inventory": ("Home inventory, valuables and moving", [
        "home inventory", "inventory", "valuables", "moving", "estate", "catalog",
        "catalogue", "list of everything i own", "for insurance"]),
}

# Titles that are jokes, screenshots, brag-posts or venting. On these subs the
# "my X lasted 20 years" story posts dominate /top and carry no query intent.
NOISE = [
    "haha", "lol", "lmao", "meme", "rate my", "my setup", "look what", "found this",
    "haul", "unboxing", "still going", "still works", "20 years", "30 years",
    "built like", "thrift", "day in the life", "psa:", "just wanted to share",
    "guess the", "who else", "relatable", "me when", "pov", "before and after",
    "update:",
]
QUESTION_WORDS = [
    "how", "what", "why", "when", "which", "anyone", "does", "do you", "should",
    "tips", "advice", "help", "is it", "can i", "any way", "best way", "struggl",
    "cant", "can't", "trouble", "problem", "recommend", "worth", " vs ", "or replace",
]


def cache_path(sub: str, window: str) -> Path:
    return CACHE / f"{sub}-{window}.xml"


def read_cache(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def save_cache(path: Path, body: str, verbose: bool) -> None:
    """Best effort. A read-only checkout must not cost us a fetched feed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    except OSError as e:
        if verbose:
            print(f"  (cache not written: {e.__class__.__name__})", file=sys.stderr)


def fetch(sub: str, window: str, pace: float, ttl: int, refresh: bool,
          verbose: bool, deadline: float) -> tuple[str | None, bool]:
    """Return (xml, from_cache). None means this feed is unavailable.

    Reddit rate-limits anonymous RSS hard — 429 is the normal response to any
    enthusiasm — so requests are paced, backed off, and finally given up on.
    Progress goes to stderr on every feed: a scheduled run is killed after 600s
    of silence, and the backoffs alone can exceed that.
    """
    path = cache_path(sub, window)
    if not refresh and path.exists() and (time.time() - path.stat().st_mtime) < ttl:
        cached = read_cache(path)
        if cached:
            if verbose:
                print(f"  r/{sub:<16} [{window}] cached", file=sys.stderr)
            return cached, True

    url = f"https://www.reddit.com/r/{sub}/top/.rss?t={window}"
    for attempt in range(4):
        if time.time() > deadline:
            if verbose:
                print(f"  r/{sub:<16} [{window}] skipped (time budget spent)", file=sys.stderr)
            break
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/atom+xml"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read().decode("utf-8", "replace")
            save_cache(path, body, verbose)
            if verbose:
                print(f"  r/{sub:<16} [{window}] ok", file=sys.stderr)
            time.sleep(pace)
            return body, False
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < 3:
                wait = 30 * (attempt + 1)
                if verbose:
                    print(f"  r/{sub:<16} [{window}] {e.code} — waiting {wait}s",
                          file=sys.stderr)
                time.sleep(min(wait, max(0.0, deadline - time.time())))
                continue
            if verbose:
                print(f"  r/{sub:<16} [{window}] unavailable (HTTP {e.code})", file=sys.stderr)
            break
        except Exception as e:                                    # network, DNS, timeout
            if verbose:
                print(f"  r/{sub:<16} [{window}] unavailable ({type(e).__name__})",
                      file=sys.stderr)
            break

    stale = read_cache(path) if path.exists() else None            # stale beats nothing
    if stale:
        if verbose:
            print(f"  r/{sub:<16} [{window}] using stale cache", file=sys.stderr)
        return stale, True
    return None, False


def titles_from(xml: str) -> list[str]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    out = []
    for entry in root.findall("a:entry", ATOM):
        node = entry.find("a:title", ATOM)
        if node is not None and node.text:
            out.append(re.sub(r"\s+", " ", node.text).strip())
    return out


def is_useful(title: str) -> bool:
    low = title.lower()
    if len(title) < 20:
        return False
    if any(n in low for n in NOISE):
        return False
    # All-caps venting posts carry no query intent.
    if sum(c.isupper() for c in title) > len(title) * 0.6:
        return False
    return any(w in low for w in QUESTION_WORDS) or "?" in title


def themes_of(title: str) -> list[str]:
    low = f" {title.lower()} "
    return [key for key, (_, words) in THEMES.items() if any(w in low for w in words)]


def covered_themes() -> dict[str, list[str]]:
    """Map theme -> [slugs] for themes an existing post already addresses.

    Matched against the title and keywords only — a summary that mentions
    receipts in passing is not a post about organising receipts.
    """
    out: dict[str, list[str]] = {}
    posts_dir = ROOT / "posts"
    if not posts_dir.is_dir():
        return out
    for path in sorted(posts_dir.glob("*.md")):
        head = path.read_text(encoding="utf-8")[:3000].split("\n---", 1)[0]
        subject = " ".join(
            line.split(":", 1)[1] for line in head.split("\n")
            if line.split(":", 1)[0].strip() in ("title", "keywords") and ":" in line
        )
        for key in themes_of(f"{subject} {path.stem.replace('-', ' ')}"):
            out.setdefault(key, []).append(path.stem)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subs", help="comma-separated subreddits (default: the consumer set)")
    ap.add_argument("--windows", default=",".join(WINDOWS), help="top windows: month,year")
    ap.add_argument("--pace", type=float, default=8.0, help="seconds between requests")
    ap.add_argument("--max-seconds", type=float, default=600.0,
                    help="total time budget; stops fetching and reports what it has")
    ap.add_argument("--ttl", type=int, default=20 * 3600, help="cache lifetime in seconds")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    ap.add_argument("--themes", type=int, default=8, help="how many themes to report")
    ap.add_argument("--examples", type=int, default=3, help="example titles per theme")
    ap.add_argument("--json", action="store_true", dest="as_json")
    ap.add_argument("--quiet", action="store_true", help="no progress on stderr")
    a = ap.parse_args()

    subs = [s.strip() for s in (a.subs.split(",") if a.subs else SUBREDDITS) if s.strip()]
    windows = [w.strip() for w in a.windows.split(",") if w.strip()]
    verbose = not a.quiet

    if verbose:
        print(f"Reading {len(subs)} subreddits x {len(windows)} windows "
              f"(~{a.pace:.0f}s apart, cached {a.ttl // 3600}h, "
              f"{a.max_seconds:.0f}s budget)...", file=sys.stderr)

    deadline = time.time() + a.max_seconds
    seen: set[str] = set()
    entries: list[tuple[str, str, int]] = []          # (title, sub, rank)
    ok = cached = failed = 0
    for sub in subs:
        for window in windows:
            xml, from_cache = fetch(sub, window, a.pace, a.ttl, a.refresh, verbose, deadline)
            if xml is None:
                failed += 1
                continue
            ok += 1
            cached += 1 if from_cache else 0
            for rank, title in enumerate(titles_from(xml)):
                key = re.sub(r"[^a-z0-9]+", "", title.lower())[:60]
                if key in seen:
                    continue
                seen.add(key)
                entries.append((title, sub, rank))

    if not entries:
        print("reddit-topics: every feed failed (Reddit is blocking or offline).\n"
              "Fall back to the ranked topic bank in prompt.md — that is expected "
              "and fine.", file=sys.stderr)
        return 2

    useful = [(t, s, r) for t, s, r in entries if is_useful(t)]
    covered = covered_themes()

    buckets: dict[str, dict] = {}
    for title, sub, rank in useful:
        for key in themes_of(title):
            b = buckets.setdefault(key, {"key": key, "label": THEMES[key][0],
                                         "count": 0, "weight": 0.0,
                                         "titles": [], "covered_by": covered.get(key, [])})
            b["count"] += 1
            b["weight"] += 1.0 / (rank + 3)           # higher in /top = stronger demand
            b["titles"].append(title)

    ranked = sorted(buckets.values(), key=lambda b: (b["weight"], b["count"]), reverse=True)
    for b in ranked:
        b["weight"] = round(b["weight"], 2)
        b["titles"] = sorted(b["titles"], key=len)[-a.examples * 3:][::-1][:a.examples]

    fresh_themes = [b for b in ranked if not b["covered_by"]]
    done_themes = [b for b in ranked if b["covered_by"]]

    if a.as_json:
        print(json.dumps({
            "feeds_ok": ok, "feeds_failed": failed, "feeds_from_cache": cached,
            "posts_seen": len(entries), "posts_useful": len(useful),
            "themes": ranked,
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"REDDIT DEMAND — {ok} feeds ({cached} cached, {failed} unavailable), "
          f"{len(entries)} posts, {len(useful)} carrying a real question")
    print()
    print(f"UNCOVERED THEMES — strongest demand first")
    if not fresh_themes:
        print("  (every theme is already covered — write a fresher angle on a top one)")
    for i, b in enumerate(fresh_themes[:a.themes], 1):
        print(f"{i:2}. {b['label']}  [{b['key']}]  {b['count']} posts, weight {b['weight']}")
        for t in b["titles"]:
            print(f"      · {t[:110]}")
    print()
    print("ALREADY COVERED")
    for b in done_themes[:8]:
        print(f"  - {b['label']} ({b['count']}) → {', '.join(sorted(set(b['covered_by'])))}")
    print()
    print("TOP QUESTION TITLES VERBATIM — the reader's own words, use them")
    on_topic = [e for e in useful if themes_of(e[0])]
    for title, sub, rank in sorted(on_topic, key=lambda e: e[2])[:15]:
        print(f"  · [r/{sub}] {title[:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
