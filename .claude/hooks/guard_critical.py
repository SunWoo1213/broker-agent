"""PreToolUse 훅: 되돌리기 어렵거나 밖으로 나가는 명령은 항상 사람 승인을 받게 한다.

Bash · PowerShell 도구의 명령 문자열을 검사해서, 아래 패턴에 걸리면
permissionDecision "ask"를 돌려준다. auto 모드 · allow 규칙이 있어도 승인 창이 뜬다.

이 프로젝트의 원칙 1(fail-closed)을 훅에도 적용한다:
입력을 해석하지 못하면 통과시키지 않고 "ask"로 떨어진다.
"""

import json
import re
import sys

# (이름, 정규식) — 대소문자 무시. 명령 문자열 전체에서 찾는다 (체인 · 서브셸 포함).
CRITICAL_PATTERNS = [
    ("git commit", r"\bgit\b[^;&|\n]*?\s(commit)\b"),
    ("git push", r"\bgit\b[^;&|\n]*?\s(push)\b"),
    ("git reset --hard", r"\bgit\b[^;&|\n]*?\sreset\b[^;&|\n]*--hard\b"),
    ("git clean -f", r"\bgit\b[^;&|\n]*?\sclean\b[^;&|\n]*\s-[a-z]*f"),
    ("git branch -D", r"\bgit\b[^;&|\n]*?\sbranch\b[^;&|\n]*\s(-D\b|--delete\s+--force)"),
    ("gh pr create/merge", r"\bgh\s+pr\s+(create|merge)\b"),
    ("gh release create", r"\bgh\s+release\s+create\b"),
    ("terraform apply/destroy", r"\b(terraform|tofu)\b[^;&|\n]*?\s(apply|destroy)\b"),
    ("docker compose down -v", r"\bdocker[- ]compose\b[^;&|\n]*?\sdown\b[^;&|\n]*\s(-v\b|--volumes\b)"),
    ("docker volume rm/prune", r"\bdocker\s+volume\s+(rm|prune)\b"),
    ("docker prune", r"\bdocker\s+(system|container|image|builder|network)?\s*prune\b"),
]


def ask(reason: str) -> None:
    # ensure_ascii=True: Windows 콘솔 인코딩(cp949)에서도 출력이 깨지거나 예외가 나지 않게 한다.
    # 출력에 실패하면 훅 오류 → 명령이 그대로 실행되므로(fail-open) 여기서 실패하면 안 된다.
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def main() -> None:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        command = payload.get("tool_input", {}).get("command", "")
        if not isinstance(command, str):
            raise ValueError("command is not a string")
    except Exception as exc:  # 해석 실패 = 사람 확인 (fail-closed)
        ask(f"[승인 필요] 훅이 명령을 해석하지 못했습니다: {exc}")
        return

    hits = [name for name, pattern in CRITICAL_PATTERNS
            if re.search(pattern, command, re.IGNORECASE)]
    if hits:
        ask(f"[승인 필요] 중요 작업 감지: {', '.join(hits)} — CLAUDE.md 규칙상 사람 승인 후에만 실행합니다.")
    # 해당 없으면 아무것도 출력하지 않는다 → 평소 권한 흐름을 그대로 따른다.


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # 어떤 예외도 "통과"로 새지 않게 한다
        ask(f"[승인 필요] 훅 내부 오류: {exc}")
