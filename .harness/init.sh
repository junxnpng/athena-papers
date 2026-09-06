#!/bin/sh
# 도메인 계약 ③ — 부트스트랩. 의존성 없음(stdlib). python3 3.9+ 만 확인한다.
cd "$(dirname "$0")/.." || exit 1
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "python3 >= 3.9 필요"; exit 1; }
[ -f data/papers.json ] || { echo "data/papers.json 없음 — 사람이 scripts/pull 을 먼저 돌린다"; exit 1; }
exit 0
