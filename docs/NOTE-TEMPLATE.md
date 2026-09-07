# 논문 노트 양식 (2026-09-07 인터뷰로 결정)

독자는 **6개월 뒤의 나**. 논문을 다시 읽지 않고 핵심 아이디어·동작·수치를 복원한다. 지침은 이 문서, 강제는 `scripts/rules.py`.

## 파일
`notes/<slug>.md` — slug 는 정본 id 의 마지막 조각(`kv-cache/mooncake` → `mooncake.md`). 충돌하면 `<hub>--<slug>.md`. 뼈대는 `scripts/note-new <id>` 가 만든다.

## front matter (인라인 목록만 — `[a, b]`)
| 키 | 누가 | 뜻 |
|---|---|---|
| `title` | 자동 | 영어 원제 |
| `paper` | 자동 | 정본 id. 검사기가 존재 확인 |
| `depth` | 사람 | `core`(★, 길고 구조도 필수) 또는 `brief`. 배지 ★ 면 기본 core |
| `status` | 사람 | `draft`(밤이 씀) 또는 `reviewed`(내가 읽고 확정). **사이트에는 reviewed 만 나간다** |
| `related` | 사람 | 관련 논문 id 목록. 관련 절과 일치 |
| `summary` | 사람 | 한 줄 결론 = 본문 첫 문단. 목록 카드에 뜬다 |
| `venue` `year` `source_url` `license` `categories` `tags` `date` | 자동 | 정본에서. 내보낼 때 다시 맞춘다 — 손으로 고치지 않는다 |

## 본문 (한국어, 이 순서)
```
<한 줄 결론>                       ← summary 와 같은 문장
## 문제와 핵심 아이디어              ← 무엇이 병목이었고 어떤 한 가지 발상으로 풀었나
## 동작 방식                        ← 그 발상이 실제로 어떻게 도나. core 는 mermaid 구조도 1개 필수
## 결과 수치                        ← 가장 중요한 숫자 두세 개를 비교 대상·조건과 함께. 그래프 대신 문장
## 관련                             ← related 의 각 id 를 한 줄 설명 + 링크
## 한계와 의심                      ← 선택. 저자가 인정한 한계, 내가 안 믿는 부분
```
- `kind` 가 해설(explainer)이면 "## 결과 수치" 대신 "## 핵심 사실".
- 관련 링크: 노트가 있으면 `../<slug>/`, 없으면 카탈로그 앵커 `/papers/#<hub>`.
- 그림: `docs/PRINCIPLES.md` 3·4. 결과 그래프 금지. 원본 그림은 license 가 CC 계열일 때만, 아니면 mermaid.
- 금지: TODO 표시, 내부 프로젝트 언급, 번역 문장 통째 옮기기(요약이다).

## 분량 (본문 글자 수)
| depth | 하한 | 상한 |
|---|---|---|
| core | 2,000 | 8,000 |
| brief | 500 | 2,500 |

## 흐름
1. `scripts/note-new <id>` → 뼈대 (status: draft).
2. 밤 리프가 초안을 채운다. 밤은 status 를 바꾸지 않는다.
3. 아침에 읽고 고치고 한 줄 결론을 확정한 뒤 `status: reviewed`.
4. `scripts/check` → `scripts/export --to ../athena-web` (reviewed 만 간다, 보낸 목록을 출력).
