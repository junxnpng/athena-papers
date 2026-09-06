# 공개 원칙 (2026-09-06 결정)

이 문서는 지침이다. 강제는 오른쪽 "강제" 열의 코드가 한다 — `scripts/check` 가 실패하면 밤 작업도 커밋도 못 한다.

| # | 원칙 | 강제 |
|---|---|---|
| 1 | **제목은 영어.** 사이트 뼈대(메뉴·홈·분야·태그·소개)도 영어. 글 제목은 원제 그대로 또는 영어 한 줄. | `scripts/rules.py`(`notes/`) — 제목에 한글이 있거나 ASCII 밖 문자면 거부 |
| 2 | **본문은 한국어 요약.** 번역이 아니다. 결과는 글로만 요약한다. | `scripts/rules.py` — 본문에 한글 없으면 거부, 8,000자 넘으면 거부(번역 본문 평균 3.3만 자) |
| 3 | **그림은 라이선스가 허락할 때만 그대로.** CC 계열(BY·BY-SA·BY-NC-SA·BY-NC-ND·CC0)은 출처 표기로 싣는다. arXiv 비독점 배포·학회 저작권은 허락이 없으니 다시 그린다. 번호·링크만으로는 허락이 아니다. | `scripts/papers.py` — arXiv 원문이면 `license` 필수. `scripts/rules.py` — 허용 목록(`data/figures.json`)에 없는 그림은 글에 못 넣고, 목록의 원본 그림은 논문 license 가 CC 계열이 아니면 거부(다시 그린 것은 `redrawn: true`) |
| 4 | **결과 그래프는 싣지 않는다.** 저작권상 가장 불리하고 글로 요약하면 충분하다. 구조도·방법 그림만. | `scripts/rules.py` — `kind` 가 result·graph·plot·chart·benchmark·eval 이면 거부 |
| 5 | **내부 맥락은 공개 필드에 없다.** 내부 프로젝트명·"우리"·사설 IP. | `scripts/papers.py` — 정본 전 필드 검사. `scripts/rules.py` — 글 제목·본문 검사. 이름 목록은 `data/raw/internal-terms.txt`(git 제외) |
| 6 | **원문 링크는 지어내지 않는다.** venue 에 적힌 번호, 또는 제목 대조를 통과한 것만. | `scripts/papers.py` — 페이지 링크 목록에서 고르지 않음. `scripts/verify-links` — 제목 대조 3단 판정 |
| 7 | **번역 본문·PDF·그림 원본은 `data/raw/` 밖으로 나가지 않는다.** | `.gitignore` — `data/raw/` 제외. `.harness/domain.json` — 밤의 쓰기 범위에서 제외 |

## 그림을 싣는 절차
1. `data/papers.json` 에서 그 논문의 `license` 를 본다. 비어 있으면 `scripts/fill-licenses`.
2. CC 계열이면 원본 그림을 `figures/` 에 두고 `data/figures.json` 에 `paper·figure·kind·file·credit` 을 적는다.
3. 아니면 mermaid 로 다시 그리고 `redrawn: true` 로 적는다. 다시 그린 것은 같은 구조를 내 표현으로 그린 것이라 어느 논문이든 된다.
4. 결과 그래프는 어느 경우에도 넣지 않는다. 숫자는 본문 문장으로.

## 라이선스 코드
`cc-by-4.0` `cc-by-sa-4.0` `cc-by-nc-sa-4.0` `cc-by-nc-nd-4.0` `cc0-1.0` — 그대로 싣기 가능(출처 표기; NC 는 비상업, ND 는 무수정 조건).
`arxiv-nonexclusive-1.0` — 저자 보유, 재사용 허락 없음 → 다시 그린다.
비어 있음 — 학회 페이지·블로그 원문. 사람이 확인해 채운다. 채우기 전에는 그림 불가.
