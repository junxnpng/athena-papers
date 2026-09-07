#!/usr/bin/env python3
"""공개 원칙의 강제 — docs/PRINCIPLES.md 에 적힌 것 중 코드로 잠글 수 있는 것을 여기서 검사한다. exit 0 = 통과.

검사 대상
  data/figures.json     글에 실을 그림의 허용 목록. 여기 없는 그림은 글에 못 넣는다.
  notes/**/*.md         논문 노트 원고(Hugo front matter). 아직 없어도 된다. 제목 영어 · 본문 한국어 · 분량 상한 · 그림은 허용 목록에서만 · 금지 문구 없음.

  scripts/rules.py [--root DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import papers as P  # noqa: E402

FIGURES = P.ROOT / "data" / "figures.json"
NOTES = P.ROOT / "notes"  # 논문 노트 원고. scripts/export 가 검증 통과분만 athena-web/content/notes/ 로 보낸다
_IMG_MD = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
_IMG_HTML = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
_ASCII_TITLE = re.compile(r"^[\x20-\x7e–—·’“”]+$")  # 영문·숫자·기호(대시·가운뎃점·따옴표)만


def load_figures(path: Path = FIGURES) -> dict:
    if not path.exists():
        return {"figures": []}
    return json.loads(path.read_text(encoding="utf-8"))


def check_figures(figs: dict, papers_by_id: dict):
    """허용 목록 자체가 원칙에 맞는가."""
    problems, seen = [], set()
    for f in figs.get("figures", []):
        fid = "%s#%s" % (f.get("paper"), f.get("figure"))
        for k in ("paper", "figure", "kind", "file"):
            if not f.get(k):
                problems.append("figures: %s 에 %s 가 없다" % (fid, k))
        if f.get("file") in seen:
            problems.append("figures: 파일 중복 %s" % f.get("file"))
        seen.add(f.get("file"))
        kind = (f.get("kind") or "").lower()
        if kind in P.FIGURE_KINDS_NO:
            problems.append("figures: %s 는 결과 그래프(%s) — 원칙 4, 글로 요약한다" % (fid, kind))
        elif kind not in P.FIGURE_KINDS_OK:
            problems.append("figures: %s kind %r 는 %s 중 하나여야 한다" % (fid, kind, list(P.FIGURE_KINDS_OK)))
        paper = papers_by_id.get(f.get("paper"))
        if not paper:
            problems.append("figures: %s 의 논문 id 가 정본에 없다" % fid)
            continue
        if not f.get("redrawn") and not P.embed_allowed(paper.get("license", "")):
            problems.append("figures: %s 는 라이선스 %r 라 그대로 못 싣는다 — redrawn: true 로 다시 그리거나 뺀다 (원칙 3)"
                            % (fid, paper.get("license") or "없음"))
        if not f.get("redrawn") and not f.get("credit"):
            problems.append("figures: %s 는 원본 그림이라 credit(출처 문구) 가 있어야 한다" % fid)
    return problems


def _fm_value(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip().strip('"').strip("'") for x in inner.split(",")] if inner else []
    return v.strip('"').strip("'")


def parse_post(text: str):
    """front matter(인라인 목록·따옴표만 지원) 와 본문."""
    m = _FRONT.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "#")):
            k, v = line.split(":", 1)
            fm[k.strip()] = _fm_value(v.split("  #")[0] if "  #" in v else v)
    return fm, text[m.end():]


DEPTHS = {"core": (2000, 8000), "brief": (500, 2500)}
STATUSES = ("draft", "reviewed")
REQUIRED_SECTIONS = ["문제와 핵심 아이디어", "동작 방식", ("결과 수치", "핵심 사실"), "관련"]
_H2 = re.compile(r"^##\s+(.+?)\s*$", re.M)
_MERMAID = re.compile(r"^```mermaid\s*$", re.M)
_LINK = re.compile(r"\]\(([^)\s]+)\)")


def sections(body: str):
    """[(제목, 본문)] 순서대로."""
    heads = list(_H2.finditer(body))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        out.append((h.group(1).strip(), body[h.end():end]))
    return out


def first_paragraph(body: str) -> str:
    for para in re.split(r"\n\s*\n", body.strip()):
        p = para.strip()
        if p and not p.startswith("#"):
            return re.sub(r"\s+", " ", p)
    return ""


def check_post(path: Path, text: str, figs: dict, papers_by_id: dict):
    problems = []
    name = str(path)
    fm, body = parse_post(text)
    title = fm.get("title", "")
    if not title:
        problems.append("%s: title 없음" % name)
    elif P.has_hangul(title) or not _ASCII_TITLE.match(title):
        problems.append("%s: 제목은 영어로 (원칙 1) — %r" % (name, title[:50]))
    pid = fm.get("paper", "")
    paper = papers_by_id.get(pid)
    if not pid:
        problems.append("%s: paper 없음" % name)
    elif not paper:
        problems.append("%s: paper %r 가 정본에 없다" % (name, pid))
    depth = fm.get("depth", "")
    if depth not in DEPTHS:
        problems.append("%s: depth 는 core|brief" % name)
    status = fm.get("status", "")
    if status not in STATUSES:
        problems.append("%s: status 는 draft|reviewed" % name)
    if not P.has_hangul(body):
        problems.append("%s: 본문은 한국어 요약 (원칙 2)" % name)
    lo, hi = DEPTHS.get(depth, (0, P.SUMMARY_MAX_CHARS))
    n = len(body.strip())
    if n > hi:
        problems.append("%s: 본문 %d자 — %s 상한 %d자 초과 (요약이지 번역이 아니다)" % (name, n, depth or "?", hi))
    elif status == "reviewed" and n < lo:
        problems.append("%s: 본문 %d자 — %s 하한 %d자 미달" % (name, n, depth or "?", lo))
    if "TODO" in body or "(쓰기)" in body:
        problems.append("%s: 채우지 않은 자리(TODO)가 있다" % name)
    # 한 줄 결론 = 첫 문단
    summ = re.sub(r"\s+", " ", (fm.get("summary") or "")).strip()
    if not summ:
        problems.append("%s: summary(한 줄 결론) 없음" % name)
    elif first_paragraph(body) != summ:
        problems.append("%s: 본문 첫 문단이 summary 와 다르다" % name)
    # 필수 절, 순서
    secs = sections(body)
    names = [t for t, _ in secs]
    want = []
    is_explainer = bool(paper) and paper.get("kind") == "해설"
    for req in REQUIRED_SECTIONS:
        if isinstance(req, tuple):
            want.append(req[1] if is_explainer else req[0])
        else:
            want.append(req)
    pos = []
    for w in want:
        if w not in names:
            alt = "핵심 사실" if w == "결과 수치" else ("결과 수치" if w == "핵심 사실" else None)
            if alt and alt in names:
                problems.append("%s: '%s' 절 대신 '%s' 를 써야 한다 (kind=%s)" % (name, alt, w, paper.get("kind") if paper else "?"))
            else:
                problems.append("%s: 필수 절 '## %s' 없음" % (name, w))
            pos.append(None)
        else:
            pos.append(names.index(w))
    got = [p for p in pos if p is not None]
    if got != sorted(got):
        problems.append("%s: 필수 절 순서가 다르다 — %s" % (name, " → ".join(want)))
    sec = dict(secs)
    # core: 동작 방식에 구조도
    if depth == "core" and "동작 방식" in sec:
        howto = sec["동작 방식"]
        if not _MERMAID.search(howto) and not (_IMG_MD.search(howto) or _IMG_HTML.search(howto)):
            problems.append("%s: core 는 '동작 방식' 절에 mermaid 구조도 또는 허용 목록 그림 1개 (원칙 3)" % name)
    # related ↔ 관련 절
    related = fm.get("related", [])
    if isinstance(related, str):
        related = [related] if related else []
    for rid in related:
        if rid not in papers_by_id:
            problems.append("%s: related %r 가 정본에 없다" % (name, rid))
    if "관련" in sec:
        links = _LINK.findall(sec["관련"])
        for rid in related:
            rp = papers_by_id.get(rid)
            if not rp:
                continue
            slug = rid.split("/")[-1]
            ok = any(("/%s/" % slug) in l or l.rstrip("/").endswith(slug) or ("#%s" % rp["hub"]) in l for l in links)
            if not ok:
                problems.append("%s: 관련 절에 %s 링크가 없다 (../%s/ 또는 /papers/#%s)" % (name, rid, slug, rp["hub"]))
    # 자동 필드는 정본과 일치
    if paper:
        for k in ("venue", "source_url", "license"):
            if str(fm.get(k, "")) != str(paper.get(k, "")):
                problems.append("%s: %s 가 정본과 다르다 — scripts/export 가 맞춘다, 손으로 고치지 않는다" % (name, k))
        if str(fm.get("year", "")) != str(paper.get("year", "")):
            problems.append("%s: year 가 정본과 다르다" % name)
    # 그림 허용 목록
    allowed = {f.get("file") for f in figs.get("figures", [])}
    for src in _IMG_MD.findall(body) + _IMG_HTML.findall(body):
        key = src.split("?")[0].lstrip("/")
        if key not in allowed and not any(key.endswith(a) for a in allowed if a):
            problems.append("%s: 그림 %s 가 data/figures.json 허용 목록에 없다 (원칙 3·4)" % (name, src))
    for t in (title, body, summ):
        if P.is_internal(t, editorial=True):
            problems.append("%s: 금지 문구가 있다 (원칙 5)" % name)
            break
    return problems


def check_posts(content: Path, figs: dict, papers_by_id: dict):
    problems = []
    if not content.exists():
        return problems
    for md in sorted(content.rglob("*.md")):
        if md.name.startswith("_") or md.name.lower() == "readme.md":  # 안내 파일은 노트가 아니다
            continue
        problems += check_post(md.relative_to(P.ROOT), md.read_text(encoding="utf-8"), figs, papers_by_id)
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(P.ROOT))
    ap.add_argument("--require-notes", type=int, default=0, help="규칙을 통과한 노트가 N편 미만이면 실패 (밤 리프 게이트)")
    a = ap.parse_args(argv)
    root = Path(a.root)
    data = P.load(root / "data" / "papers.json")
    by_id = {p["id"]: p for p in data["papers"]}
    figs = load_figures(root / "data" / "figures.json")
    problems = check_figures(figs, by_id) + check_posts(root / "notes", figs, by_id)
    for pr in problems:
        print("FAIL", pr)
    pdir = root / "notes"
    notes = [m for m in pdir.rglob("*.md") if not m.name.startswith("_") and m.name.lower() != "readme.md"] if pdir.exists() else []
    statuses = {}
    for m in notes:
        fm, _ = parse_post(m.read_text(encoding="utf-8"))
        statuses[fm.get("status", "?")] = statuses.get(fm.get("status", "?"), 0) + 1
    print("rules: figures=%d notes=%d %s problems=%d" % (len(figs.get("figures", [])), len(notes),
          " ".join("%s=%d" % kv for kv in sorted(statuses.items())), len(problems)))
    if a.require_notes and (len(notes) < a.require_notes or problems):
        print("FAIL 규칙을 통과한 노트 %d편 필요, 지금 %d편" % (a.require_notes, 0 if problems else len(notes)))
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
