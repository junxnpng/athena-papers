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


def parse_post(text: str):
    m = _FRONT.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, text[m.end():]


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
    if pid and pid not in papers_by_id:
        problems.append("%s: paper %r 가 정본에 없다" % (name, pid))
    if not P.has_hangul(body):
        problems.append("%s: 본문은 한국어 요약 (원칙 2)" % name)
    if len(body) > P.SUMMARY_MAX_CHARS:
        problems.append("%s: 본문 %d자 — 요약 상한 %d자 초과, 번역이 아니라 요약이다 (원칙 2)" % (name, len(body), P.SUMMARY_MAX_CHARS))
    allowed = {f.get("file") for f in figs.get("figures", [])}
    for src in _IMG_MD.findall(body) + _IMG_HTML.findall(body):
        key = src.split("?")[0].lstrip("/")
        if key not in allowed and not any(key.endswith(a) for a in allowed if a):
            problems.append("%s: 그림 %s 가 data/figures.json 허용 목록에 없다 (원칙 3·4)" % (name, src))
    for s in (title, body):
        if P.is_internal(s, editorial=True):
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
    a = ap.parse_args(argv)
    root = Path(a.root)
    data = P.load(root / "data" / "papers.json")
    by_id = {p["id"]: p for p in data["papers"]}
    figs = load_figures(root / "data" / "figures.json")
    problems = check_figures(figs, by_id) + check_posts(root / "notes", figs, by_id)
    for pr in problems:
        print("FAIL", pr)
    pdir = root / "notes"
    nposts = len([m for m in pdir.rglob("*.md") if not m.name.startswith("_") and m.name.lower() != "readme.md"]) if pdir.exists() else 0
    print("rules: figures=%d notes=%d problems=%d" % (len(figs.get("figures", [])), nposts, len(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
