"""authz.rego 정책 파일의 정적 성질을 검사한다 (D18, broker-invariants 원칙 1 · 2).

- S1: `default` 줄은 모두 거부 쪽이다. `default decision`은 정확히 한 번, 다른 default 줄은
  `:= false` 형태만 허용한다 (예: `default allow_ok := true`처럼 관대한 기본값을 막는다).
- S2: `opa.runtime` · `http.send` · `net.lookup_ip_addr`(개발용 우회 스위치 · 네트워크 의존)를
  정책 어디에도 쓰지 않는다.

대상 파일: `policies/` 아래 `_test.rego`로 끝나지 않는 `*.rego` 전부. 텍스트만 읽는다 (opa 실행 없음).
"""

import re
from pathlib import Path

DEFAULT_DECISION_LINE = 'default decision := {"result": "deny", "reason": "no_matching_rule"}'
DEFAULT_FALSE_RE = re.compile(r"^default [A-Za-z_][A-Za-z0-9_]* := false$")
FORBIDDEN_BUILTINS = ("opa.runtime", "http.send", "net.lookup_ip_addr")


def _policy_files(request) -> list[Path]:
    root = request.config.rootpath / "policies"
    return sorted(p for p in root.glob("*.rego") if not p.name.endswith("_test.rego"))


def test_policy_default_lines_are_deny_only(request):
    files = _policy_files(request)
    assert files, "policies/ 아래 검사 대상 .rego 파일이 없다"

    decision_line_count = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("default "):
                continue
            if stripped == DEFAULT_DECISION_LINE:
                decision_line_count += 1
                continue
            assert DEFAULT_FALSE_RE.match(stripped), (
                f"{path}: default 줄은 거부 쪽이어야 한다: {stripped!r}"
            )
    assert decision_line_count == 1, (
        f"default decision 줄은 정확히 1개여야 한다 (실제 {decision_line_count})"
    )


def test_policy_has_no_runtime_env_or_network_builtins(request):
    files = _policy_files(request)
    assert files, "policies/ 아래 검사 대상 .rego 파일이 없다"

    for path in files:
        text = path.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_BUILTINS:
            assert forbidden not in text, f"{path}: 금지된 내장 함수 {forbidden!r}가 있다"
