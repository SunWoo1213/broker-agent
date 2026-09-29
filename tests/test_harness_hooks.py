"""하네스(훅 · 권한 규칙)가 이 OS에서 실제로 살아 있는지 확인한다.

왜 이 파일이 있나.
    훅은 실행에 실패하면 **판정을 내지 않고 조용히 사라진다**. Claude Code는 그때
    명령을 그대로 통과시키므로(fail-open), 훅이 죽은 것과 훅이 "허용"한 것을
    밖에서는 구분할 수 없다. 2026-09-29에 실제로 이 일이 있었다: 훅 설정이
    `command: python`이었는데 맥에는 그 이름의 실행 파일이 없어(있는 것은 `python3`)
    `guard_critical` · `guard_paths`가 전부 죽은 채로 세션이 돌아갔다.
    그래서 "설정에 훅이 적혀 있다"가 아니라 "이 OS에서 훅을 돌리면 막힌다"를 확인한다.

    같은 이유로 여기서는 목(mock)을 쓰지 않는다. 실제 `run_hook.sh`를 서브프로세스로
    실행하고 표준 입력으로 훅 페이로드를 넣어, 나온 JSON을 그대로 본다.

내용은 ASCII만 쓴다(주석 · docstring 제외). tests/test_pytest_config.py와 같은 규칙이다.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"
RUNNER = HOOKS / "run_hook.sh"
PYTHON_SH = REPO / ".claude" / "tools" / "python.sh"
SETTINGS = REPO / ".claude" / "settings.json"
AGENTS = REPO / ".claude" / "agents"

# 훅 설정이 가리켜야 하는 실행기. 이 문자열이 바뀌면 아래 테스트가 전부 잡는다.
RUNNER_CALL = 'sh "$CLAUDE_PROJECT_DIR/.claude/hooks/run_hook.sh"'


def _sh() -> str:
    """POSIX 셸. 맥 · 리눅스는 /bin/sh, 윈도우는 Git Bash의 sh."""
    found = shutil.which("sh") or shutil.which("bash")
    if not found:
        pytest.fail("sh/bash not found: the harness hooks cannot run on this machine")
    return found


def _run_hook(decision: str, script: str, *args: str, payload: object,
              env: dict | None = None,
              runner: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_sh(), str(runner or RUNNER), decision, script, *args],
        input=json.dumps(payload),
        capture_output=True, text=True, encoding="utf-8", timeout=30,
        cwd=REPO, env=env,
    )


def _decision(proc: subprocess.CompletedProcess) -> dict | None:
    """훅 출력에서 판정을 꺼낸다. 출력이 비어 있으면 '판정 없음'(평소 흐름)이다."""
    out = proc.stdout.strip()
    if not out:
        return None
    return json.loads(out)["hookSpecificOutput"]


# ---------------------------------------------------------------- 실행기 자체

def test_runner_and_python_launcher_exist():
    assert RUNNER.is_file(), f"missing {RUNNER}"
    assert PYTHON_SH.is_file(), f"missing {PYTHON_SH}"


def test_shell_scripts_use_lf_only():
    """CRLF로 받아지면 셸이 스크립트를 실행하지 못한다 (.gitattributes가 막는다)."""
    for path in (RUNNER, PYTHON_SH):
        assert b"\r\n" not in path.read_bytes(), f"{path.name} has CRLF line endings"


def test_python_launcher_resolves_an_interpreter():
    proc = subprocess.run(
        [_sh(), str(PYTHON_SH), "-c", "import sys; print(sys.version_info[0])"],
        capture_output=True, text=True, encoding="utf-8", timeout=30, cwd=REPO,
    )
    assert proc.returncode == 0, f"python.sh failed: {proc.stderr}"
    assert proc.stdout.strip() == "3"


# ------------------------------------------------- guard_critical (ask 판정)

CRITICAL_COMMANDS = [
    "git commit -m wip",
    "git push origin dev",
    "git reset --hard HEAD~1",
    "git clean -fd",
    "git branch -D feature",
    "gh pr create --fill",
    "gh release create v1",
    "terraform apply -auto-approve",
    "terraform destroy",
    "docker compose down -v",
    "docker volume rm pgdata",
    "docker system prune -af",
    # 체인 · 서브셸로 숨겨도 걸려야 한다
    "echo hi && git push",
    "bash -c 'terraform destroy'",
]


@pytest.mark.parametrize("command", CRITICAL_COMMANDS)
def test_critical_command_is_sent_to_a_human(command):
    out = _decision(_run_hook("ask", "guard_critical.py",
                              payload={"tool_input": {"command": command}}))
    assert out is not None, f"hook let {command!r} through without a decision"
    assert out["permissionDecision"] == "ask"
    assert out["hookEventName"] == "PreToolUse"


@pytest.mark.parametrize("command", ["ls -la", "sh .claude/tools/python.sh -m pytest -q",
                                     "docker compose ps", "git status --porcelain"])
def test_ordinary_command_is_not_intercepted(command):
    proc = _run_hook("ask", "guard_critical.py",
                     payload={"tool_input": {"command": command}})
    assert proc.returncode == 0
    assert _decision(proc) is None, f"hook wrongly intercepted {command!r}"


def test_unparseable_payload_asks_instead_of_passing():
    proc = subprocess.run(
        [_sh(), str(RUNNER), "ask", "guard_critical.py"],
        input="this is not json", capture_output=True, text=True,
        encoding="utf-8", timeout=30, cwd=REPO,
    )
    out = _decision(proc)
    assert out is not None and out["permissionDecision"] == "ask"


# --------------------------------------------------- guard_paths (deny 판정)

def test_write_outside_allowed_prefix_is_denied():
    out = _decision(_run_hook("deny", "guard_paths.py", ".claude/runs",
                              payload={"tool_input": {"file_path": "gateway/main.py"},
                                       "cwd": str(REPO)}))
    assert out is not None, "guard_paths let an out-of-scope write through"
    assert out["permissionDecision"] == "deny"


def test_write_inside_allowed_prefix_is_not_denied():
    proc = _run_hook("deny", "guard_paths.py", ".claude/runs",
                     payload={"tool_input": {"file_path": ".claude/runs/x/01-plan.md"},
                              "cwd": str(REPO)})
    assert _decision(proc) is None


# ------------------------------------------- 인터프리터가 없을 때 (fail-closed)

def _env_without_python(tmp_path: Path) -> dict:
    """python을 하나도 찾을 수 없는 환경. 셸 자신은 절대 경로로 부르므로 PATH가 비어도 된다."""
    env = {"PATH": str(tmp_path)}
    if os.name == "nt":  # 윈도우 셸은 SystemRoot 없이는 뜨지 않는다
        for key in ("SystemRoot", "COMSPEC", "WINDIR"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def _runner_without_a_venv(tmp_path: Path, script: str) -> Path:
    """.venv 가 없는 임시 저장소에 실행기와 훅 스크립트만 복사해 돌려준다.

    run_hook.sh 는 PATH 와 상관없이 `<저장소>/.venv/bin/python` 을 먼저 찾는다(그래야
    PATH 가 이상해도 훅이 산다). 그래서 이 저장소 안에서는 PATH 만 비워도
    "인터프리터가 하나도 없는 상태"가 만들어지지 않는다 — .venv 가 생긴 뒤로는 그렇다.
    아래 두 테스트가 보려는 상황은 갓 clone 해서 .venv 가 아직 없는 기계이므로,
    그 조건을 임시 폴더로 실제로 만든다. 훅 스크립트는 표준 라이브러리만 쓰기 때문에
    복사해도 동작이 같다.
    """
    hooks = tmp_path / "fresh-clone" / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(RUNNER, hooks / RUNNER.name)
    shutil.copy2(HOOKS / script, hooks / script)
    return hooks / RUNNER.name


def test_missing_interpreter_still_asks(tmp_path):
    """훅이 시작하지 못해도 통과시키지 않는다. 이것이 2026-09-29에 뚫린 구멍이다."""
    out = _decision(_run_hook("ask", "guard_critical.py",
                              payload={"tool_input": {"command": "ls"}},
                              env=_env_without_python(tmp_path),
                              runner=_runner_without_a_venv(tmp_path, "guard_critical.py")))
    assert out is not None, "hook failed open when no interpreter was available"
    assert out["permissionDecision"] == "ask"


def test_missing_interpreter_still_denies(tmp_path):
    out = _decision(_run_hook("deny", "guard_paths.py", ".claude/runs",
                              payload={"tool_input": {"file_path": ".claude/runs/ok.md"}},
                              env=_env_without_python(tmp_path),
                              runner=_runner_without_a_venv(tmp_path, "guard_paths.py")))
    assert out is not None, "guard_paths failed open when no interpreter was available"
    assert out["permissionDecision"] == "deny"


def test_crashing_hook_script_does_not_pass(tmp_path):
    """훅 스크립트가 0이 아닌 코드로 끝나면 그 출력을 믿지 않고 막는다."""
    boom = HOOKS / "_test_crashing_hook.py"
    boom.write_text("import sys\nsys.exit(3)\n", encoding="ascii")
    try:
        out = _decision(_run_hook("ask", boom.name, payload={}))
    finally:
        boom.unlink()
    assert out is not None and out["permissionDecision"] == "ask"


def test_unknown_hook_script_does_not_pass():
    out = _decision(_run_hook("ask", "no_such_hook.py", payload={}))
    assert out is not None and out["permissionDecision"] == "ask"


# ------------------------------------------------------------ 설정이 실행기를 가리키나

def test_settings_hook_goes_through_the_cross_platform_runner():
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    entries = [h for group in cfg["hooks"]["PreToolUse"] for h in group["hooks"]]
    assert entries, "no PreToolUse hooks configured"
    for hook in entries:
        assert "args" not in hook, (
            "exec form pins one interpreter name; use the shell form through run_hook.sh"
        )
        assert hook.get("shell") == "bash", "pin the shell so Windows does not fall back to PowerShell"
        assert RUNNER_CALL in hook["command"], hook["command"]


def _frontmatter(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} has no frontmatter"
    return text.split("---\n", 2)[1]


def test_agent_hooks_go_through_the_cross_platform_runner():
    checked = 0
    for agent in sorted(AGENTS.glob("*.md")):
        fm = _frontmatter(agent)
        for line in fm.splitlines():
            stripped = line.strip()
            if not stripped.startswith("command:"):
                continue
            checked += 1
            assert RUNNER_CALL in stripped, f"{agent.name}: {stripped}"
            assert " deny guard_paths.py " in stripped, f"{agent.name}: {stripped}"
        if "hooks:" in fm:
            assert "shell: bash" in fm, f"{agent.name} does not pin the hook shell"
    assert checked >= 5, f"expected the write-guarded agents to keep their hooks, found {checked}"


def test_no_bare_python_command_left_in_harness_config():
    """`command: python` / `command: python3` 로 되돌아가면 한쪽 OS에서 훅이 죽는다."""
    offenders = []
    for path in [SETTINGS, *sorted(AGENTS.glob("*.md"))]:
        for num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r'"?command"?\s*:\s*"?(python3?|py)"?\s*,?\s*$', line.strip()):
                offenders.append(f"{path.relative_to(REPO)}:{num}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


# ------------------------------------------------ 권한 규칙이 두 셸을 모두 덮나

# 같은 일을 하지만 셸마다 이름이 다른 명령. 아래 대칭 검사에서 제외하고 따로 확인한다.
SHELL_SPECIFIC = {"rm -rf *", "rm -r *", "Remove-Item *"}


def _rules_by_shell(entries: list[str]) -> dict[str, set[str]]:
    rule = re.compile(r"^(Bash|PowerShell)\((.*)\)$")
    out: dict[str, set[str]] = {"Bash": set(), "PowerShell": set()}
    for entry in entries:
        m = rule.match(entry)
        if m:
            out[m.group(1)].add(m.group(2))
    return out


@pytest.mark.parametrize("key", ["ask", "deny"])
def test_permission_rules_cover_both_shells(key):
    """맥에서만 · 윈도우에서만 막히는 규칙이 없어야 한다.

    윈도우 쪽 규칙 일부가 settings.local.json(git 제외)에만 있던 탓에, 맥에서는
    같은 명령이 확인 없이 실행됐다. 공유되는 이 파일 하나로 두 OS를 덮는지 본다.
    """
    perms = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]
    by_shell = _rules_by_shell(perms[key])
    bash = by_shell["Bash"] - SHELL_SPECIFIC
    powershell = by_shell["PowerShell"] - SHELL_SPECIFIC
    assert bash == powershell, (
        f"permissions.{key} differs between shells: "
        f"Bash-only={sorted(bash - powershell)} PowerShell-only={sorted(powershell - bash)}"
    )


def test_file_deletion_needs_approval_in_both_shells():
    perms = json.loads(SETTINGS.read_text(encoding="utf-8"))["permissions"]
    ask = _rules_by_shell(perms["ask"])
    assert any(r.startswith("rm ") for r in ask["Bash"]), "no rm rule for Bash"
    assert any(r.startswith("Remove-Item") for r in ask["PowerShell"]), "no Remove-Item rule for PowerShell"


def test_evidence_tool_still_refuses_guarded_commands(tmp_path):
    """evidence.py의 126 필터는 settings.json의 규칙을 읽는다. 규칙을 옮겨도 살아 있어야 한다."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    proc = subprocess.run(
        [sys.executable, str(REPO / ".claude" / "tools" / "evidence.py"),
         str(run_dir), "guarded", "git push --dry-run origin dev"],
        capture_output=True, text=True, encoding="utf-8", timeout=60, cwd=REPO,
    )
    assert proc.returncode == 126, proc.stdout + proc.stderr
    assert not (run_dir / "evidence").exists(), "a refused command must leave no evidence log"
