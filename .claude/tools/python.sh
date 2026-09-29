#!/bin/sh
# 이 저장소의 python 을 OS에 상관없이 같은 문자열로 부르기 위한 실행기.
#
#   sh .claude/tools/python.sh -m pytest -q
#   sh .claude/tools/python.sh .claude/tools/evidence.py <run 폴더> --verify
#
# 맥 · 리눅스의 .venv/bin/python 과 윈도우의 .venv/Scripts/python.exe 는 경로가 다르고,
# 맥에는 `python` 이라는 이름 자체가 없다(있는 것은 `python3`). 문서와 완료 조건(AC)에
# 한쪽 OS의 경로를 적으면 다른 쪽에서 그대로 실행되지 않으므로, 명령 원문을 하나로
# 맞추려면 이 실행기를 거친다. 증거 로그(evidence.py)의 명령 원문도 두 OS에서 같아진다.
#
# 찾는 순서: 프로젝트 .venv → python3 → python → py.
# 이름만 있고 실제로 돌지 않는 후보(윈도우 Microsoft Store 의 python3 스텁 등)는 건너뛴다.
# 하나도 없으면 127 로 끝낸다.
set -u

case "$0" in
    */*) here=${0%/*} ;;
    *)   here=. ;;
esac
repo_root=$(CDPATH= cd -- "$here/../.." && pwd) || repo_root=.

usable() {
    [ -n "${1:-}" ] || return 1
    "$1" -c '' >/dev/null 2>&1
}

for c in "$repo_root/.venv/bin/python" "$repo_root/.venv/Scripts/python.exe"; do
    if [ -f "$c" ] && usable "$c"; then exec "$c" "$@"; fi
done
for name in python3 python py; do
    c=$(command -v "$name" 2>/dev/null) || continue
    if usable "$c"; then exec "$c" "$@"; fi
done

echo "실행 가능한 python 을 찾지 못했습니다 (.venv → python3 → python → py 순서로 확인)." >&2
exit 127
