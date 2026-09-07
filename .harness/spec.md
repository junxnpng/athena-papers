# 사양 (도메인 계약 ①) — papers: LLM 추론·서빙 논문 요약 공개 사이트

## 목표
읽고 정리한 논문 67편을 **요약 카드 + 원문 링크**만으로 외부에 공개하는 정적 사이트. 정본은 `data/papers.json` 하나이고 사이트(`site/index.html`)는 그 파생물이다(I3). 완성은 (1) 내부 맥락이 섞여 잘린 요약이 전부 공개용으로 다시 쓰이고, (2) 학회·연도가 정규화되어 필터가 깨끗하고, (3) 검증기가 통과한 상태다.

## 도메인 지시문
- **노트 양식은 `docs/NOTE-TEMPLATE.md`.** 밤은 `notes/` 의 status: draft 노트만 채운다. status 를 reviewed 로 바꾸지 않는다(사람 몫). 본보기는 `notes/mooncake.md`.
- **공개 원칙은 `docs/PRINCIPLES.md` 7개.** 제목 영어 · 본문 한국어 요약(8,000자 상한) · 그림은 CC 라이선스일 때만 그대로(아니면 다시 그림) · 결과 그래프 금지 · 내부 맥락 금지 · 링크 지어내기 금지 · raw 반출 금지. 검증기가 거부한다(`scripts/rules.py`, `scripts/papers.py`).
- **밤은 네트워크가 없다.** 원본 재추출(`scripts/pull`)·미러(`scripts/mirror`)는 사람이 대화형에서 돌린다. 밤은 `data/papers.json` 과 `site/` 만 고친다.
- `data/raw/` 는 읽기 참고용이다. 그 안의 문장을 공개 필드로 옮길 때 사적 프로젝트·"우리" 언급은 절대 옮기지 않는다 — `scripts/papers.py --validate` 가 거부한다. 금지 문구의 정본은 `data/raw/internal-terms.txt`(git 제외)이고, 코드에는 일반 규칙(사설 IP·🔑·"이 스터디"·편집 문장의 "우리")만 있다.
- 요약을 다시 쓸 때는 **논문 자체의 기여**만 쓴다: 문제 → 핵심 아이디어 → 결과 수치 순, 3~5문장, 한국어. 확립된 기술 용어(KV cache·prefill·decode·TTFT 등)는 원어 유지. 다 쓰면 `needs_rewrite: false`.
- 학회 정규화는 `venue_short`(예: OSDI·SOSP·MLSys·arXiv·NVIDIA Blog), `venue_type`(conference|journal|arxiv|blog|docs|other), `year`(네 자리). 원문 `venue` 문자열은 건드리지 않는다.
- 카탈로그(`site/index.html`)는 손으로 고치지 않는다. 데이터를 고치고 `scripts/build`. 실제 사이트는 별도 레포 athena-web 이고 밤은 그쪽을 건드리지 않는다 — `scripts/export` 는 사람이 돌린다.
- 코드는 python3 stdlib, 셸은 POSIX sh. 테스트는 `unittest`.
- 원문 URL 을 **지어내지 않는다.** raw 의 링크나 venue 의 arXiv 번호에서만 만든다. 모르면 비워 둔다(사람이 채운다).

## 완성도 기준 (P7-lite 제안이 따를 우선순위)
1. `needs_rewrite` 0건. 2. `--strict-venue` 통과. 3. 원문 링크 없는 논문 목록이 `docs/` 에 정리되어 사람이 채우기 쉽다. 4. 카드에 소분류·허브 소개문이 자연스럽다. 5. 모바일에서 읽기 좋다.
