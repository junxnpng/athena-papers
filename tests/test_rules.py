from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import papers as P  # noqa: E402
import rules as R  # noqa: E402


def setUpModule():
    P.configure_terms(hard=["SecretProj"])

PAPERS = {
    "kv-cache/strata": {"id": "kv-cache/strata", "license": "cc-by-4.0"},
    "kv-cache/mooncake": {"id": "kv-cache/mooncake", "license": "arxiv-nonexclusive-1.0"},
    "runtime/orca": {"id": "runtime/orca", "license": ""},
}


def fig(**over):
    base = {"paper": "kv-cache/strata", "figure": 2, "kind": "architecture", "file": "figures/strata-fig2.png",
            "credit": "Figure 2, Strata, CC BY 4.0", "redrawn": False}
    base.update(over)
    return {"figures": [base]}


def post(title="Strata: Hierarchical Context Caching", body="긴 문맥에서는 KV 로딩이 계산보다 오래 걸린다.", paper="kv-cache/strata"):
    return "---\ntitle: \"%s\"\npaper: %s\n---\n%s\n" % (title, paper, body)


class LicenseTest(unittest.TestCase):
    def test_embed_allowed(self):
        self.assertTrue(P.embed_allowed("cc-by-4.0"))
        self.assertTrue(P.embed_allowed("cc-by-sa-4.0"))
        self.assertTrue(P.embed_allowed("cc-by-nc-nd-4.0"))
        self.assertTrue(P.embed_allowed("cc0-1.0"))
        self.assertFalse(P.embed_allowed("arxiv-nonexclusive-1.0"))
        self.assertFalse(P.embed_allowed(""))

    def test_validate_requires_license_for_arxiv(self):
        raw = {"hubs": [{"id": "kv-cache", "name": "KV", "blurb": "b"}],
               "papers": [{"path": "/papers/kv-cache/x/", "hub": "kv-cache", "title_ko": "X", "title_en": "X",
                           "kind": "전문 번역", "venue": "arXiv 2405.04437", "summary": "요약.", "chips": [], "links": []}]}
        data = P.build_public(raw)
        self.assertTrue(any("license" in m for m in P.validate(data)))
        data["papers"][0]["license"] = "cc-by-4.0"
        self.assertEqual(P.validate(data), [])


class FigureRulesTest(unittest.TestCase):
    def test_cc_figure_with_credit_passes(self):
        self.assertEqual(R.check_figures(fig(), PAPERS), [])

    def test_result_graph_rejected(self):
        msgs = R.check_figures(fig(kind="result"), PAPERS)
        self.assertTrue(any("결과 그래프" in m for m in msgs))

    def test_non_cc_original_rejected_but_redrawn_ok(self):
        msgs = R.check_figures(fig(paper="kv-cache/mooncake"), PAPERS)
        self.assertTrue(any("그대로 못 싣는다" in m for m in msgs))
        self.assertEqual(R.check_figures(fig(paper="kv-cache/mooncake", redrawn=True, credit=""), PAPERS), [])

    def test_unknown_license_rejected(self):
        msgs = R.check_figures(fig(paper="runtime/orca"), PAPERS)
        self.assertTrue(any("그대로 못 싣는다" in m for m in msgs))

    def test_missing_credit_rejected(self):
        msgs = R.check_figures(fig(credit=""), PAPERS)
        self.assertTrue(any("credit" in m for m in msgs))


class PostRulesTest(unittest.TestCase):
    def check(self, text, figs=None):
        return R.check_post(Path("content/posts/x.md"), text, figs or {"figures": []}, PAPERS)

    def test_good_post_passes(self):
        self.assertEqual(self.check(post()), [])

    def test_korean_title_rejected(self):
        self.assertTrue(any("제목은 영어" in m for m in self.check(post(title="스트라타: 계층적 캐싱"))))

    def test_english_body_rejected(self):
        self.assertTrue(any("한국어 요약" in m for m in self.check(post(body="Only English here."))))

    def test_too_long_body_rejected(self):
        self.assertTrue(any("상한" in m for m in self.check(post(body="가" * (P.SUMMARY_MAX_CHARS + 1)))))

    def test_undeclared_image_rejected(self):
        msgs = self.check(post(body="구조도. ![fig](/figures/strata-fig2.png)"))
        self.assertTrue(any("허용 목록" in m for m in msgs))
        self.assertEqual(self.check(post(body="구조도. ![fig](/figures/strata-fig2.png)"), fig()), [])

    def test_internal_term_rejected(self):
        self.assertTrue(any("금지 문구" in m for m in self.check(post(body="SecretProj 와 비교하면 좋다."))))

    def test_unknown_paper_rejected(self):
        self.assertTrue(any("정본에 없다" in m for m in self.check(post(paper="nope/x"))))


if __name__ == "__main__":
    unittest.main()
