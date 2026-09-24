"""Agent 전용 PreToolUse 훅: 검증 담당 Agent가 허용된 폴더 밖의 파일을 쓰지 못하게 한다.

사용: python guard_paths.py <허용 경로 접두사> [<허용 경로 접두사> ...]
  예) python guard_paths.py .claude/runs      → 검토 리포트만 쓸 수 있음

Write · Edit 대상 경로가 허용 접두사 아래가 아니면 deny.
입력을 해석하지 못하면 deny (fail-closed).
"""

import json
import os
import sys


def decide(decision: str, reason: str) -> None:
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def normalize(path: str, root: str) -> str:
    if not os.path.isabs(path):
        path = os.path.join(root, path)
    return os.path.normcase(os.path.realpath(path))


def main() -> None:
    allowed = sys.argv[1:]
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        target = payload["tool_input"]["file_path"]
        root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    except Exception as exc:
        decide("deny", f"[경로 제한] 입력을 해석하지 못해 쓰기를 막습니다: {exc}")
        return

    t = normalize(target, root)
    for prefix in allowed:
        p = normalize(prefix, root)
        if t == p or t.startswith(p + os.sep):
            return  # 허용 범위 안 → 평소 권한 흐름
    decide("deny", f"[경로 제한] 이 Agent는 {', '.join(allowed)} 아래에만 쓸 수 있습니다: {target}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        decide("deny", f"[경로 제한] 훅 내부 오류로 쓰기를 막습니다: {exc}")
