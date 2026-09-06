from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import papers as P  # noqa: E402

P.configure_terms(hard=["SecretProj", "Acme"])  # 실제 이름은 data/raw 에만 — 테스트는 가짜 이름으로


def _load_build():
    loader = importlib.machinery.SourceFileLoader("build", str(ROOT / "scripts" / "build"))
    spec = importlib.util.spec_from_loader("build", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def raw_paper(**over):
    base = {"path": "/papers/kv-cache/x/", "hub": "kv-cache", "subcategory": "재사용·공유",
            "title_ko": "X: 제목", "title_en": "X: Title", "kind": "전문 번역", "badge": "★ 핵심",
            "venue": "USENIX OSDI 2024", "year": "", "chips": ["USENIX OSDI 2024", "prefix 재사용"],
            "summary": "첫 문장이다. 둘째 문장이다.", "authors": "A, B", "affil": "Univ",
            "abstract": "우리는 X를 제안한다.", "figures": 3, "links": ["https://arxiv.org/abs/2401.00001"]}
    base.update(over)
    return base


def raw(*ps):
    return {"hubs": [{"id": "kv-cache", "name": "KV 캐시", "blurb": "KV를 어디에 두나."}], "papers": list(ps)}


class ScrubTest(unittest.TestCase):
    def test_clean_summary_untouched(self):
        p = P.scrub_paper(raw_paper())
        self.assertEqual(p["summary"], "첫 문장이다. 둘째 문장이다.")
        self.assertFalse(p["needs_rewrite"])
        self.assertEqual(p["id"], "kv-cache/x")
        self.assertEqual(p["year"], "2024")
        self.assertEqual(p["source_url"], "https://arxiv.org/abs/2401.00001")

    def test_internal_sentence_cuts_rest(self):
        p = P.scrub_paper(raw_paper(summary="첫 문장이다. 🔑 이 스터디에 중요한 것은 SecretProj 다 — 그래서 셋째. 넷째 문장이다."))
        self.assertEqual(p["summary"], "첫 문장이다.")
        self.assertTrue(p["needs_rewrite"])

    def test_soft_term_only_in_editorial_fields(self):
        p = P.scrub_paper(raw_paper(summary="우리가 서빙하는 모델이다.", badge="★ 우리 서빙 모델", chips=["우리 1차 대상", "MoE"]))
        self.assertEqual(p["summary"], "")
        self.assertEqual(p["badge"], "")
        self.assertEqual(p["chips"], ["MoE"])
        self.assertTrue(p["needs_rewrite"])
        self.assertEqual(p["abstract"], "우리는 X를 제안한다.")  # 저자의 '우리' 는 허용

    def test_hard_term_in_abstract_is_dropped(self):
        p = P.scrub_paper(raw_paper(abstract="SecretProj 과 비교한다."))
        self.assertEqual(p["abstract"], "")
        self.assertTrue(p["needs_rewrite"])

    def test_internal_title_falls_back_to_name(self):
        p = P.scrub_paper(raw_paper(title_ko="GPGPU-Sim — 메모리 모델과 우리 층위", title_en="우리가 미모델링으로 선언한 층"))
        self.assertEqual(p["title_ko"], "GPGPU-Sim")
        self.assertEqual(p["title_en"], "")
        self.assertTrue(p["needs_rewrite"])

    def test_year_derivation(self):
        self.assertEqual(P.derive_year("USENIX FAST '25"), "2025")
        self.assertEqual(P.derive_year("arXiv:2607.18141"), "2026")
        self.assertEqual(P.derive_year("arXiv 2602.21547 · 2026-02"), "2026")
        self.assertEqual(P.derive_year("ACM Computing Surveys 29(2)"), "")
        self.assertEqual(P.derive_year("blog", "2024"), "2024")

    def test_source_url_from_venue_when_no_links(self):
        self.assertEqual(P.derive_source_url("arXiv 2405.04437", []), "https://arxiv.org/abs/2405.04437")
        self.assertEqual(P.derive_source_url("MLSys 2024", ["https://example.com/x"]), "")


class ValidateTest(unittest.TestCase):
    def test_public_build_validates(self):
        data = P.build_public(raw(raw_paper(), raw_paper(path="/papers/kv-cache/y/", title_ko="Y")))
        self.assertEqual(P.validate(data), [])

    def test_internal_term_rejected(self):
        data = P.build_public(raw(raw_paper()))
        data["papers"][0]["summary"] = "정상 문장. Acme 스택 언급."
        self.assertTrue(any("내부 맥락" in m for m in P.validate(data)))

    def test_duplicate_and_unknown_hub(self):
        data = P.build_public(raw(raw_paper(), raw_paper()))
        data["papers"][0]["hub"] = "nope"
        msgs = P.validate(data)
        self.assertTrue(any("중복" in m for m in msgs))
        self.assertTrue(any("모르는 hub" in m for m in msgs))

    def test_strict_flags(self):
        data = P.build_public(raw(raw_paper(summary="SecretProj 언급.")))
        self.assertEqual(P.validate(data), [])
        self.assertTrue(any("needs_rewrite" in m for m in P.validate(data, strict_rewrite=True)))
        self.assertTrue(any("venue_type" in m for m in P.validate(data, strict_venue=True)))

    def test_merge_keeps_human_edits(self):
        new = P.build_public(raw(raw_paper(summary="SecretProj 언급.")))
        old = json.loads(json.dumps(new))
        old["papers"][0].update({"summary": "사람이 다시 쓴 요약.", "needs_rewrite": False, "venue_short": "OSDI",
                                 "venue_type": "conference"})
        merged = P.merge_public(old, new)
        self.assertEqual(merged["papers"][0]["summary"], "사람이 다시 쓴 요약.")
        self.assertFalse(merged["papers"][0]["needs_rewrite"])
        self.assertEqual(merged["papers"][0]["venue_short"], "OSDI")


class BuildTest(unittest.TestCase):
    def test_render_is_deterministic_and_complete(self):
        B = _load_build()
        data = P.build_public(raw(raw_paper(), raw_paper(path="/papers/kv-cache/y/", title_ko="Y <b>제목</b>", venue="MLSys 2024", links=[])))
        h1, h2 = B.render(data), B.render(data)
        self.assertEqual(h1, h2)
        self.assertIn("X: 제목", h1)
        self.assertIn("Y &lt;b&gt;제목&lt;/b&gt;", h1)
        self.assertIn('data-year="2024"', h1)
        self.assertIn("원문 링크 미확인", h1)
        self.assertNotIn("<script src", h1)  # 외부 자원 없음

    def test_check_detects_stale_site(self):
        B = _load_build()
        data = P.build_public(raw(raw_paper()))
        with tempfile.TemporaryDirectory() as d:
            dp, out = Path(d) / "p.json", Path(d) / "index.html"
            P.dump(data, dp)
            self.assertEqual(B.main(["--data", str(dp), "--out", str(out)]), 0)
            self.assertEqual(B.main(["--check", "--data", str(dp), "--out", str(out)]), 0)
            out.write_text(out.read_text(encoding="utf-8") + "<!-- 손으로 고침 -->", encoding="utf-8")
            self.assertEqual(B.main(["--check", "--data", str(dp), "--out", str(out)]), 1)


if __name__ == "__main__":
    unittest.main()
