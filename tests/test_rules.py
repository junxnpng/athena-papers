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
    "kv-cache/strata": {"id": "kv-cache/strata", "hub": "kv-cache", "kind": "전문 번역", "license": "cc-by-4.0",
                        "venue": "arXiv 2025-08", "year": "2025", "source_url": "https://arxiv.org/abs/2508.18572"},
    "kv-cache/mooncake": {"id": "kv-cache/mooncake", "hub": "kv-cache", "kind": "전문 번역", "license": "arxiv-nonexclusive-1.0",
                          "venue": "USENIX FAST 2025", "year": "2025", "source_url": "https://arxiv.org/abs/2407.00079"},
    "runtime/orca": {"id": "runtime/orca", "hub": "runtime", "kind": "전문 번역", "license": "", "venue": "USENIX OSDI 2022", "year": "2022", "source_url": ""},
    "concept/nvidia": {"id": "concept/nvidia", "hub": "concept", "kind": "해설", "license": "", "venue": "NVIDIA Technical Blog", "year": "2023",
                       "source_url": "https://developer.nvidia.com/blog/x/"},
}


def fig(**over):
    base = {"paper": "kv-cache/strata", "figure": 2, "kind": "architecture", "file": "figures/strata-fig2.png",
            "credit": "Figure 2, Strata, CC BY 4.0", "redrawn": False}
    base.update(over)
    return {"figures": [base]}


SUMMARY = "긴 문맥에서는 KV 로딩이 계산보다 오래 걸린다."
BODY_OK = (SUMMARY + "\n\n## 문제와 핵심 아이디어\n\n긴 문맥에서 prefill 이 전송에 막힌다. GPU 가 I/O 를 주도하게 한다.\n\n"
           "## 동작 방식\n\nGPU 커널이 host 메모리에서 KV 를 직접 끌어온다.\n\n```mermaid\nflowchart LR\n  H[Host KV] --> G[GPU]\n```\n\n"
           "## 결과 수치\n\nvLLM+LMCache 대비 TTFT 최대 5배.\n\n## 관련\n\n- [Mooncake](../mooncake/) — 원격 KV 풀.\n")


def post(title="Strata: Hierarchical Context Caching", body=BODY_OK, paper="kv-cache/strata", depth="brief", status="draft",
         related="[kv-cache/mooncake]", summary=SUMMARY, venue="arXiv 2025-08", year="2025",
         source_url="https://arxiv.org/abs/2508.18572", license="cc-by-4.0"):
    return ("---\ntitle: \"%s\"\npaper: %s\ndepth: %s\nstatus: %s\nrelated: %s\nsummary: \"%s\"\n"
            "venue: \"%s\"\nyear: %s\nsource_url: %s\nlicense: %s\n---\n%s") % (
        title, paper, depth, status, related, summary, venue, year, source_url, license, body)


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
        return R.check_post(Path("notes/x.md"), text, figs or {"figures": []}, PAPERS)

    def test_good_post_passes(self):
        self.assertEqual(self.check(post()), [])

    def test_korean_title_rejected(self):
        self.assertTrue(any("제목은 영어" in m for m in self.check(post(title="스트라타: 계층적 캐싱"))))

    def test_english_body_rejected(self):
        self.assertTrue(any("한국어 요약" in m for m in self.check(post(body="Only English here.", summary="Only English here."))))

    def test_depth_and_status_required(self):
        self.assertTrue(any("depth" in m for m in self.check(post(depth="deep"))))
        self.assertTrue(any("status" in m for m in self.check(post(status="done"))))

    def test_length_bounds_by_depth(self):
        long_body = BODY_OK + "\n" + "가" * 2600
        self.assertTrue(any("상한" in m for m in self.check(post(body=long_body))))          # brief 2,500 초과
        self.assertEqual([m for m in self.check(post(body=long_body, depth="core")) if "상한" in m], [])  # core 는 8,000
        self.assertTrue(any("하한" in m for m in self.check(post(status="reviewed", depth="core"))))  # reviewed core 는 2,000 이상
        self.assertEqual([m for m in self.check(post(status="draft", depth="core")) if "하한" in m], [])  # draft 는 하한 안 봄

    def test_first_paragraph_must_equal_summary(self):
        self.assertTrue(any("summary 와 다르다" in m for m in self.check(post(summary="다른 결론."))))

    def test_required_sections_and_order(self):
        no_sec = BODY_OK.replace("## 관련", "## 참고")
        self.assertTrue(any("'## 관련' 없음" in m for m in self.check(post(body=no_sec, related="[]"))))
        swapped = BODY_OK.replace("## 문제와 핵심 아이디어", "## XX").replace("## 동작 방식", "## 문제와 핵심 아이디어").replace("## XX", "## 동작 방식")
        self.assertTrue(any("순서" in m for m in self.check(post(body=swapped))))

    def test_explainer_uses_key_facts(self):
        msgs = self.check(post(paper="concept/nvidia", venue="NVIDIA Technical Blog", year="2023",
                               source_url="https://developer.nvidia.com/blog/x/", license="", related="[]"))
        self.assertTrue(any("'핵심 사실' 를 써야" in m for m in msgs))

    def test_core_requires_diagram(self):
        no_diag = BODY_OK.replace("```mermaid\nflowchart LR\n  H[Host KV] --> G[GPU]\n```\n", "")
        self.assertTrue(any("구조도" in m for m in self.check(post(body=no_diag, depth="core"))))
        self.assertEqual([m for m in self.check(post(body=no_diag, depth="brief")) if "구조도" in m], [])

    def test_related_must_exist_and_be_linked(self):
        self.assertTrue(any("related" in m and "정본에 없다" in m for m in self.check(post(related="[nope/x]"))))
        unlinked = BODY_OK.replace("[Mooncake](../mooncake/)", "Mooncake")
        self.assertTrue(any("링크가 없다" in m for m in self.check(post(body=unlinked))))
        anchored = BODY_OK.replace("(../mooncake/)", "(/papers/#kv-cache)")
        self.assertEqual(self.check(post(body=anchored)), [])

    def test_auto_fields_must_match_catalog(self):
        self.assertTrue(any("venue 가 정본과" in m for m in self.check(post(venue="Somewhere 2025"))))
        self.assertTrue(any("license 가 정본과" in m for m in self.check(post(license="cc0-1.0"))))

    def test_todo_rejected(self):
        self.assertTrue(any("TODO" in m for m in self.check(post(body=BODY_OK + "\n(쓰기) 나중에\n"))))

    def test_undeclared_image_rejected(self):
        body = BODY_OK.replace("## 관련", "![fig](/figures/strata-fig2.png)\n\n## 관련")
        self.assertTrue(any("허용 목록" in m for m in self.check(post(body=body))))
        self.assertEqual(self.check(post(body=body), fig()), [])

    def test_internal_term_rejected(self):
        self.assertTrue(any("금지 문구" in m for m in self.check(post(body=BODY_OK + "\nSecretProj 와 비교하면 좋다.\n"))))

    def test_unknown_paper_rejected(self):
        self.assertTrue(any("정본에 없다" in m for m in self.check(post(paper="nope/x"))))


class ParserTest(unittest.TestCase):
    def test_inline_lists_and_quotes(self):
        fm, body = R.parse_post('---\ntitle: "A: B"\nrelated: [x/y, z/w]\nempty: []\n---\n본문\n')
        self.assertEqual(fm["title"], "A: B")
        self.assertEqual(fm["related"], ["x/y", "z/w"])
        self.assertEqual(fm["empty"], [])
        self.assertEqual(body.strip(), "본문")


if __name__ == "__main__":
    unittest.main()
