#!/bin/sh
# 훅 실행기 — 맥 · 리눅스 · 윈도우(Git Bash)에서 같은 설정으로 훅 스크립트를 실행한다.
#
# 사용: sh run_hook.sh <실패 시 판정: ask|deny> <훅 스크립트 파일 이름> [스크립트 인자...]
#   예) sh run_hook.sh ask  guard_critical.py
#       sh run_hook.sh deny guard_paths.py .claude/runs
#
# 왜 이 파일이 필요한가.
#   훅 설정에 `python`을 직접 적으면 맥에는 그 이름의 실행 파일이 없어(있는 것은 `python3`)
#   훅이 시작조차 못 하고 죽는다. 훅이 죽으면 Claude Code는 명령을 그대로 통과시킨다 —
#   즉 fail-open이다. 이것은 docs/wiki/troubleshooting/hook-cp949-fail-open.md 와 같은 계열의
#   구멍이며, CLAUDE.md 불변 원칙 1(문제가 생기면 전부 막는다)을 훅 자신에게 적용하지 않은 결과다.
#
# 그래서 이 실행기는 두 가지를 한다.
#   1. 인터프리터를 OS에 상관없이 찾는다 (프로젝트 .venv 우선 → python3 → python → py).
#      후보는 이름이 있는 것만으로는 부족하고 `-c ''`가 실제로 도는 것만 고른다
#      (윈도우 Microsoft Store의 python3 스텁은 이름만 있고 실행되지 않는다).
#   2. 인터프리터를 못 찾거나 훅 스크립트가 0이 아닌 코드로 끝나면, 조용히 통과시키지 않고
#      <실패 시 판정>(ask 또는 deny)을 직접 출력한다.
set -u

decision=${1:-ask}
script_name=${2:-}
if [ "$#" -ge 2 ]; then shift 2; else shift "$#"; fi

# dirname 같은 외부 명령에 기대지 않는다. PATH 가 비어 있어도 여기까지는 돌아야
# "인터프리터를 못 찾았다"는 정확한 사유로 막을 수 있다.
case "$0" in
    */*) hooks_dir=${0%/*} ;;
    *)   hooks_dir=. ;;
esac
hooks_dir=$(CDPATH= cd -- "$hooks_dir" && pwd) || hooks_dir=.
repo_root=$(CDPATH= cd -- "$hooks_dir/../.." && pwd) || repo_root=.
script="$hooks_dir/$script_name"

# permissionDecisionReason 은 JSON 문자열 안에 그대로 들어가므로 따옴표 · 역슬래시를 쓰지 않는다.
emit() {
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}\n' \
        "$decision" "$1"
}

usable() {
    [ -n "${1:-}" ] || return 1
    "$1" -c '' >/dev/null 2>&1
}

find_python() {
    for c in "$repo_root/.venv/bin/python" "$repo_root/.venv/Scripts/python.exe"; do
        if [ -f "$c" ] && usable "$c"; then printf '%s\n' "$c"; return 0; fi
    done
    for name in python3 python py; do
        c=$(command -v "$name" 2>/dev/null) || continue
        if usable "$c"; then printf '%s\n' "$c"; return 0; fi
    done
    return 1
}

if [ -z "$script_name" ]; then
    emit "[하네스] run_hook.sh 에 훅 스크립트 이름이 넘어오지 않았습니다 (설정 오류)."
    exit 0
fi
if [ ! -f "$script" ]; then
    emit "[하네스] 훅 스크립트를 찾지 못했습니다: $script_name"
    exit 0
fi

py=$(find_python) || {
    emit "[하네스] 실행 가능한 python 을 찾지 못해 훅을 돌리지 못했습니다. 통과시키지 않고 막습니다 (fail-closed). .claude/hooks/run_hook.sh 참고."
    exit 0
}

# 훅 스크립트의 stdout 은 판정 JSON 이다. 스크립트가 비정상 종료하면 그 출력은 믿지 않는다.
out=$("$py" "$script" "$@")
code=$?
if [ "$code" -ne 0 ]; then
    emit "[하네스] 훅 스크립트가 비정상 종료했습니다 (exit $code). 통과시키지 않고 막습니다 (fail-closed)."
    exit 0
fi
# 판정할 것이 없으면 아무것도 출력하지 않는다 → 평소 권한 흐름을 그대로 따른다.
[ -n "$out" ] && printf '%s\n' "$out"
exit 0
