# athena-papers — LLM 추론·서빙 논문 요약 사이트

읽고 정리한 논문·기술 문서를 **요약 카드 + 원문 링크**로 보여 주는 정적 사이트.
번역 본문·그림은 싣지 않는다(저작권). 정본은 `data/papers.json` 하나이고 사이트는 그 파생물이다.

## 구조
- `data/papers.json` — 정본. 공개 가능한 필드만. `scripts/papers.py` 가 스키마와 금지 문구를 검사한다.
- `data/raw/` — 작업용 원본과 로컬 설정(git 제외). `base.txt`(원본 주소), `internal-terms.txt`(공개 금지 문구), `site/`(원본 미러).
- `scripts/pull` — 원본 → raw → 정본. `--from-raw` 는 네트워크 없이 정본만 재생성.
- `scripts/mirror` — 원본 논문 페이지와 그림을 `data/raw/site/` 에 통째로 보관.
- `scripts/build` — 정본 → `site/catalog.fragment.html`(Hugo 가 감싸는 조각, 다크 모드는 테마 변수로 따라옴) + `site/index.html`(미리보기). 노트가 있는 논문엔 Note → 링크. `--check` 는 최신 여부만.
- `scripts/check` — 검증기 전부(스키마 + 공개 원칙 + 사이트 최신 + unittest). `.harness/verify` 가 이것을 부른다.
- `notes/` — 논문 노트 원고(Hugo front matter). 검증 통과분만 `scripts/export` 가 `../athena-web` 으로 내보낸다.
- `scripts/export` — 카탈로그 조각과 노트를 athena-web 에 한 방향으로 복사. 내보내기 전에 `scripts/check` 를 돌린다.
- `.harness/` — 하네스 계약 파일. 밤 작업은 오프라인 리프만(요약 재작성·학회 정규화).

## 규칙
- 공개 원칙 7개는 `docs/PRINCIPLES.md`. 지침이 아니라 검증기가 강제한다 — `scripts/rules.py`(글·그림), `scripts/papers.py`(정본).
- python3 stdlib 만. `#!/bin/sh` POSIX 만.
- `site/` 는 파생물 — 손으로 고치지 않는다. 데이터를 고치고 `scripts/build`.
- `data/raw/` 는 커밋하지 않는다. 원본 주소와 금지 문구 목록은 코드에 적지 않고 `data/raw/` 의 파일로 둔다.
- 공개 사이트에 싣는 것: 제목·원제·요약·학회·연도·저자·초록·원문 링크. 싣지 않는 것: 번역 본문·그림·금지 문구.

## 사이트
사이트는 별도 레포 `athena-web`(Hugo + PaperMod). 이 레포는 데이터와 검증만 맡고, `scripts/export` 로 내보낸다.
