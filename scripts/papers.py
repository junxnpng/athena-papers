#!/usr/bin/env python3
"""공개용 논문 요약 데이터의 정본 규약 — 로드·정화(scrub)·검증. python3 stdlib 만.

data/raw/papers.raw.json    원본 사이트에서 긁은 그대로 (git 제외, 사람만 갱신)
data/raw/base.txt           원본 주소 (git 제외) — 코드에 적지 않는다
data/raw/internal-terms.txt 공개 금지 문구 정규식, 한 줄에 하나 (git 제외) — 코드에는 일반 규칙만
data/papers.json            공개 가능 필드만 남긴 정본 (사이트는 이 파일의 파생물)

CLI:  scripts/papers.py --validate [--strict-rewrite] [--strict-venue]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "papers.json"
RAW_DIR = ROOT / "data" / "raw"
RAW = RAW_DIR / "papers.raw.json"
TERMS_FILE = RAW_DIR / "internal-terms.txt"
BASE_FILE = RAW_DIR / "base.txt"

HUB_ORDER = ["concept", "model", "runtime", "kv-cache", "distributed", "storage",
             "hardware-path", "session-reuse", "workload", "sim-method"]
KINDS = ["전문 번역", "핵심 발췌 번역", "정독·분석", "해설", "기타"]
VENUE_TYPES = ["conference", "journal", "arxiv", "blog", "docs", "other"]

# 공개 사이트에 실리면 안 되는 문구.
# HARD: 어느 필드에서든 거부. SOFT: 편집 문장(요약·배지·칩·제목·소개문)에서만 거부 — 논문 초록의 "우리는 …제안한다" 는 저자의 말이라 허용.
# 코드에는 일반 규칙만 둔다. 구체적 이름은 data/raw/internal-terms.txt (git 제외) 에서 읽어 HARD 에 더한다.
INTERNAL_HARD = [r"이 스터디", r"🔑", r"\b10\.\d+\.\d+\.\d+\b", r"\b192\.168\.\d+\.\d+\b", r"\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+\b"]
INTERNAL_SOFT = [r"우리"]
_HARD_RE = _SOFT_RE = None


def configure_terms(hard=None, soft=None) -> None:
    """검사에 쓸 정규식을 조립한다. 테스트는 여기로 가짜 이름을 넣는다."""
    global _HARD_RE, _SOFT_RE
    h = list(INTERNAL_HARD) + list(hard or [])
    _HARD_RE = re.compile("|".join(h))
    _SOFT_RE = re.compile("|".join(h + list(soft if soft is not None else INTERNAL_SOFT)))


def load_terms_file(path: Path = TERMS_FILE):
    if not Path(path).exists():
        return []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def resolve_base(arg: str = "") -> str:
    """원본 주소: --base > PAPERS_BASE > data/raw/base.txt. 코드에는 적지 않는다."""
    base = arg or os.environ.get("PAPERS_BASE", "")
    if not base and BASE_FILE.exists():
        base = BASE_FILE.read_text(encoding="utf-8").strip()
    if not base:
        sys.exit("원본 주소가 없다: --base, PAPERS_BASE, 또는 %s" % BASE_FILE.relative_to(ROOT))
    return base if base.endswith("/") else base + "/"


configure_terms(load_terms_file())

EDITORIAL_FIELDS = ("summary", "badge", "chips", "subcategory", "title_ko", "title_en", "blurb", "name")

PUBLIC_FIELDS = ["id", "hub", "subcategory", "title_ko", "title_en", "kind", "badge", "venue", "year",
                 "venue_short", "venue_type", "chips", "summary", "authors", "affil", "abstract",
                 "source_url", "figures", "needs_rewrite"]

_SENT_SPLIT = re.compile(r"(?<=[.다\)])\s+(?=\S)")


def is_internal(text: str, editorial: bool = False) -> bool:
    rx = _SOFT_RE if editorial else _HARD_RE
    return bool(rx.search(text or ""))


def scrub_text(text: str, editorial: bool = True):
    """내부 맥락이 처음 나오는 문장부터 잘라낸다. (남은 문장, 잘렸는가)."""
    parts = _SENT_SPLIT.split(text or "")
    kept = []
    for s in parts:
        if is_internal(s, editorial):
            return " ".join(kept).strip(), True
        kept.append(s)
    return " ".join(kept).strip(), False


def derive_year(venue: str, year_chip: str = "") -> str:
    for src in (year_chip or "", venue or ""):
        m = re.search(r"\b(20\d\d)\b", src)
        if m:
            return m.group(1)
    m = re.search(r"'(\d\d)\b", venue or "")
    if m:
        return "20" + m.group(1)
    m = re.search(r"arXiv[: ]*(\d{2})\d{2}\.\d{4,5}", venue or "")
    if m:
        return "20" + m.group(1)
    return ""


def derive_source_url(venue: str, links=None) -> str:
    """venue 문자열에 적힌 arXiv 번호만 쓴다.
    페이지 본문의 링크 목록은 참고문헌이 섞여 있어 그 논문의 원문이라는 보장이 없다 — 그쪽은
    scripts/fill-links 가 제목 대조를 거쳐 채운다."""
    m = re.search(r"arXiv[:\s]*(\d{4}\.\d{4,5})", venue or "", re.I) or re.search(r"\b(\d{4}\.\d{4,5})\b", venue or "")
    return "https://arxiv.org/abs/" + m.group(1) if m else ""


def paper_id(path: str) -> str:
    p = (path or "").strip("/")
    return p[len("papers/"):] if p.startswith("papers/") else p


def scrub_paper(raw: dict) -> dict:
    summary, cut = scrub_text(raw.get("summary", ""))
    badge = raw.get("badge", "")
    if is_internal(badge, editorial=True):
        badge, cut = "", True
    chips = [c for c in raw.get("chips", []) if not is_internal(c, editorial=True)]
    if len(chips) != len(raw.get("chips", [])):
        cut = True
    abstract = raw.get("abstract", "")
    if is_internal(abstract):
        abstract, cut = "", True
    venue = raw.get("venue", "")
    title_ko, title_en = raw.get("title_ko", ""), raw.get("title_en", "")
    if is_internal(title_ko, editorial=True):  # 논문이 아닌 내부 정리 글 — 대시 앞 이름만 남긴다
        head = title_ko.split(" — ")[0].strip()
        title_ko = head if head and not is_internal(head, editorial=True) else paper_id(raw.get("path", "")).split("/")[-1]
        cut = True
    if is_internal(title_en, editorial=True):
        title_en, cut = "", True
    return {
        "id": paper_id(raw.get("path", raw.get("id", ""))),
        "hub": raw.get("hub", ""),
        "subcategory": raw.get("subcategory", ""),
        "title_ko": title_ko,
        "title_en": title_en,
        "kind": raw.get("kind", "기타"),
        "badge": badge,
        "venue": venue,
        "year": raw.get("year_norm") or derive_year(venue, raw.get("year", "")),
        "venue_short": raw.get("venue_short", ""),
        "venue_type": raw.get("venue_type", ""),
        "chips": chips,
        "summary": summary,
        "authors": raw.get("authors", ""),
        "affil": raw.get("affil", ""),
        "abstract": abstract,
        "source_url": raw.get("source_url") or derive_source_url(venue, raw.get("links", [])),
        "figures": raw.get("figures", 0),
        "needs_rewrite": cut,
    }


def scrub_hub(raw: dict) -> dict:
    blurb, _ = scrub_text(raw.get("blurb", ""))
    return {"id": raw["id"], "name": raw.get("name", raw["id"]), "blurb": blurb}


def build_public(raw: dict) -> dict:
    """원본(raw) → 공개 정본. 결정론적 — 같은 raw 면 같은 결과."""
    hubs = [scrub_hub(h) for h in raw.get("hubs", [])]
    papers = [scrub_paper(p) for p in raw.get("papers", [])]
    order = {h: i for i, h in enumerate(HUB_ORDER)}
    papers.sort(key=lambda p: (order.get(p["hub"], 99), p["subcategory"], p["id"]))
    return {"version": 1, "source": "study notes", "hubs": hubs, "papers": papers}


def merge_public(old: dict, new: dict) -> dict:
    """재추출 시 사람이 손본 필드(요약 재작성·venue 정규화·원문 링크)를 잃지 않는다."""
    keep = ("summary", "badge", "chips", "venue_short", "venue_type", "year", "source_url", "needs_rewrite")
    prev = {p["id"]: p for p in old.get("papers", [])}
    for p in new["papers"]:
        o = prev.get(p["id"])
        if not o:
            continue
        if o.get("needs_rewrite") is False and p.get("needs_rewrite"):
            for k in ("summary", "badge", "chips", "needs_rewrite"):
                p[k] = o[k]
        for k in ("venue_short", "venue_type", "year", "source_url"):
            if o.get(k) and not p.get(k):
                p[k] = o[k]
    return new


def load(path: Path = DATA) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(data: dict, path: Path = DATA) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _walk_strings(obj, prefix=""):
    if isinstance(obj, str):
        yield prefix, obj
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, "%s[%d]" % (prefix, i))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, "%s.%s" % (prefix, k) if prefix else k)


def validate(data: dict, strict_rewrite: bool = False, strict_venue: bool = False):
    """문제 목록을 돌려준다. 비어 있으면 통과."""
    problems = []
    papers = data.get("papers", [])
    if not papers:
        problems.append("papers 가 비어 있다")
    ids = [p.get("id") for p in papers]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append("id 중복: %s" % dup)
    hub_ids = {h["id"] for h in data.get("hubs", [])}
    for p in papers:
        pid = p.get("id") or "(id 없음)"
        for f in PUBLIC_FIELDS:
            if f not in p:
                problems.append("%s: 필드 누락 %s" % (pid, f))
        extra = set(p) - set(PUBLIC_FIELDS)
        if extra:
            problems.append("%s: 공개 필드가 아닌 키 %s" % (pid, sorted(extra)))
        if p.get("hub") not in HUB_ORDER:
            problems.append("%s: 모르는 hub %r" % (pid, p.get("hub")))
        elif hub_ids and p["hub"] not in hub_ids:
            problems.append("%s: hubs 에 없는 hub %r" % (pid, p["hub"]))
        if p.get("kind") not in KINDS:
            problems.append("%s: 모르는 kind %r" % (pid, p.get("kind")))
        if not p.get("title_ko"):
            problems.append("%s: title_ko 비어 있음" % pid)
        if not (p.get("summary") or p.get("abstract")):
            problems.append("%s: 요약도 초록도 없음" % pid)
        for path, s in _walk_strings(p):
            field = path.split(".")[0].split("[")[0]
            if is_internal(s, editorial=field in EDITORIAL_FIELDS):
                problems.append("%s: 내부 맥락이 공개 필드에 남아 있음 (%s)" % (pid, path))
        if strict_rewrite and p.get("needs_rewrite"):
            problems.append("%s: needs_rewrite — 요약을 아직 다시 쓰지 않았다" % pid)
        if strict_venue:
            if p.get("venue_type") not in VENUE_TYPES:
                problems.append("%s: venue_type 가 %s 중 하나가 아님" % (pid, VENUE_TYPES))
            if not p.get("venue_short"):
                problems.append("%s: venue_short 비어 있음" % pid)
            if not re.fullmatch(r"(19|20)\d\d", p.get("year") or ""):
                problems.append("%s: year 가 네 자리 연도가 아님" % pid)
    for h in data.get("hubs", []):
        for path, s in _walk_strings(h):
            if is_internal(s, editorial=True):
                problems.append("hub %s: 내부 맥락 (%s)" % (h.get("id"), path))
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--strict-rewrite", action="store_true", help="needs_rewrite 가 남아 있으면 실패")
    ap.add_argument("--strict-venue", action="store_true", help="venue_short/venue_type/year 정규화가 안 됐으면 실패")
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args(argv)
    if not a.validate:
        ap.print_help()
        return 2
    data = load(Path(a.data))
    probs = validate(data, a.strict_rewrite, a.strict_venue)
    for p in probs:
        print("FAIL", p)
    n = len(data.get("papers", []))
    todo = sum(1 for p in data.get("papers", []) if p.get("needs_rewrite"))
    nolink = sum(1 for p in data.get("papers", []) if not p.get("source_url"))
    extra = len(load_terms_file())
    if not extra:
        print("WARN %s 없음 — 일반 규칙만으로 검사했다" % TERMS_FILE.relative_to(ROOT))
    print("papers=%d needs_rewrite=%d no_source_url=%d terms=%d problems=%d" % (n, todo, nolink, extra, len(probs)))
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main())
