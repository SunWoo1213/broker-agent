# 훅 설정의 `command: python` 때문에 맥에서 훅이 전부 죽음 (fail-open)

> 요약
> - 한 줄 해결: 훅 설정에서 인터프리터 이름을 직접 부르지 말고, OS에 맞는 python을 찾아 주는 `.claude/hooks/run_hook.sh`를 거친다. 인터프리터를 못 찾으면 실행기가 직접 `ask` · `deny`를 낸다.
> - 원인: 하네스가 윈도우에서 만들어져 훅 설정이 `command: python`이었는데, 맥에는 `python`이라는 이름의 실행 파일이 없다(있는 것은 `python3`). 훅 프로세스가 뜨지 못하면 Claude Code는 도구 호출을 그대로 진행한다.
> - 재발 방지: `tests/test_harness_hooks.py`(35개)가 실제 훅을 서브프로세스로 돌려 "이 OS에서 막히는가"를 확인한다. CI와 로컬 모두에서 돈다.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-29 | 하네스 | 해결 | 맥 환경으로 옮기며 직접 발견 | 원칙 1 (fail-closed) |

## 증상

맥에서 세션을 열고, 승인 훅에 반드시 걸려야 하는 문자열이 든 명령을 실행했다.

```
$ echo "probe: git push origin dev"
probe: git push origin dev
```

`guard_critical.py`의 패턴 `\bgit\b[^;&|\n]*?\s(push)\b`에 걸리므로 **승인 창이 떠야 하는데 뜨지 않고 그대로 실행됐다.** 훅이 "허용"을 낸 것인지 훅이 죽은 것인지 밖에서는 구분되지 않는다 — 둘 다 똑같이 조용히 통과한다.

같은 설정을 쓰는 agent 6종의 경로 제한 훅(`guard_paths.py`)도 함께 죽어 있었다. 이쪽이 더 위험하다. 검증 담당 agent(reviewer · test-verifier)는 `.claude/runs/` 밖에 쓰지 못하게 되어 있는데, 그 제한이 통째로 사라진 상태였다.

확인한 원인은 단순했다.

```
$ which python
python not found
$ which python3
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
```

## 재현 방법

1. 맥(또는 `python`이라는 이름이 PATH에 없는 리눅스)에서 이 저장소를 연다.
2. `.claude/settings.json`의 PreToolUse 훅을 `{"type":"command","command":"python","args":["${CLAUDE_PROJECT_DIR}/.claude/hooks/guard_critical.py"]}`로 둔다.
3. `git push`가 들어간 명령을 실행한다 → 승인 창이 뜨지 않는다.

## 원인

1. 직접 원인: 훅 설정이 `command: python`이었고, 맥에는 그 이름의 실행 파일이 없다. `args`가 있으면 Claude Code는 셸을 거치지 않고 실행 파일을 직접 띄우므로(exec form), 이름이 PATH에 없으면 프로세스가 시작조차 하지 못한다.
2. 왜 통과됐나? → Claude Code는 훅이 오류로 끝나면 차단 신호로 보지 않고 도구 호출을 계속 진행한다. [hook-cp949-fail-open.md](hook-cp949-fail-open.md)와 완전히 같은 성질의 fail-open이다.
3. 두 번째 방어선이 왜 못 막았나? → `permissions.ask`의 `Bash(git push *)`는 명령이 **그 앞부분으로 시작하는지**를 본다. `echo "... git push ..."`처럼 다른 명령의 인자 안에 들어 있는 형태는 규칙에 걸리지 않는다. 훅은 명령 문자열 전체를 보므로 둘의 범위가 다르다. 그리고 `guard_paths.py`가 하는 경로 제한은 `permissions`로 표현되어 있지 않아 애초에 두 번째 방어선이 없었다.
4. 근본 원인: 하네스가 **한 OS에서만 만들어지고, 살아 있는지 확인하는 수단이 사람의 관찰뿐이었다.** 훅이 도는지 아닌지를 판정하는 테스트가 없었기 때문에, 환경이 바뀌자 아무 신호 없이 안전장치 전체가 꺼졌다. 이것은 "지키는 대상과 같은 기준으로 지키는 도구를 설계한다"는 교훈([subagent-permission-bypass.md](subagent-permission-bypass.md) 근본 원인)이 하네스의 또 다른 층(실행 환경)에서 재발한 것이다.

## 해결

### 1. 인터프리터를 찾아 주는 실행기 (`.claude/hooks/run_hook.sh`)

훅 설정은 이제 셸 형식으로 이 실행기를 부른다. Claude Code의 셸 형식은 맥 · 리눅스에서 `sh -c`, 윈도우에서 Git Bash로 돌아가므로 한 문자열이 두 OS에서 그대로 쓰인다. `shell: bash`를 명시해 윈도우에서 PowerShell로 떨어지지 않게 고정했다.

```json
{
  "type": "command",
  "shell": "bash",
  "command": "sh \"$CLAUDE_PROJECT_DIR/.claude/hooks/run_hook.sh\" ask guard_critical.py",
  "timeout": 10
}
```

실행기는 `.venv/bin/python` → `.venv/Scripts/python.exe` → `python3` → `python` → `py` 순서로 후보를 찾고, 이름만 있고 실제로는 돌지 않는 후보(윈도우 Microsoft Store의 `python3` 스텁)는 `-c ''`를 실제로 실행해 걸러낸다.

가장 중요한 부분은 **실패했을 때 조용히 사라지지 않는다**는 것이다. 첫 인자가 실패 시 판정이다.

```sh
py=$(find_python) || {
    emit "[하네스] 실행 가능한 python 을 찾지 못해 훅을 돌리지 못했습니다. 통과시키지 않고 막습니다 (fail-closed)."
    exit 0
}
out=$("$py" "$script" "$@")
code=$?
if [ "$code" -ne 0 ]; then
    emit "[하네스] 훅 스크립트가 비정상 종료했습니다 (exit $code). 통과시키지 않고 막습니다 (fail-closed)."
    exit 0
fi
```

`dirname` 같은 외부 명령에도 기대지 않는다(`${0%/*}` 사용). PATH가 비어 있어도 "인터프리터를 못 찾았다"는 정확한 사유로 막을 수 있어야 하기 때문이다.

### 2. 명령 원문을 한 벌로 (`.claude/tools/python.sh`)

같은 문제가 문서 · 완료 조건(AC) · 증거 로그에도 있었다. `.venv/Scripts/python -m pytest -q`는 맥에서 그대로 실행되지 않는다. 같은 탐색 순서를 가진 실행기를 두고 `sh .claude/tools/python.sh -m pytest -q` 한 형태로 통일했다. 증거 로그(`evidence.py`)에 남는 명령 원문이 두 OS에서 같아진다.

### 3. 두 번째 방어선을 공유되는 파일로

윈도우 쪽 ask · deny 규칙 일부가 `.claude/settings.local.json`에만 있었는데, 이 파일은 `.gitignore` 대상이라 맥에는 오지 않았다. `rm -rf` · `Remove-Item` · `.env.*` 등을 커밋되는 `.claude/settings.json`으로 옮겨 두 OS가 같은 규칙을 쓰게 했다. `evidence.py`의 126 필터도 이 파일을 읽으므로 함께 복구된다.

### 4. 줄바꿈 고정 (`.gitattributes`)

`* text=auto eol=lf`. 윈도우에서 `core.autocrlf=true`로 받으면 `.sh` 실행기가 CRLF가 되어 실행되지 않고, 증거 로그의 sha256도 OS마다 달라진다.

## 검증

전부 실제로 실행해 확인했다.

- `run_hook.sh`에 표준 입력으로 훅 페이로드를 넣어 9가지 경로 확인: 위험 명령 → `ask`, 평범한 명령 → 출력 없음, 경로 밖 쓰기 → `deny`, 경로 안 쓰기 → 출력 없음, 깨진 JSON → `ask`, 없는 스크립트 → `ask`, 인터프리터 없음(PATH 비움) → `ask` · `deny`, 스크립트 비정상 종료(exit 3) → `ask`.
- 실제 Claude Code 세션(`claude -p`, 저장소 루트)에서 `echo 'git push origin dev'`를 요청 → **차단됨**. 고치기 전 같은 명령은 그대로 실행됐다.
- `pytest -q` 48개 전부 통과(기존 13개 + 새 `tests/test_harness_hooks.py` 35개).

탐침 3건으로 새 테스트가 실제로 회귀를 잡는지 확인했다(원본은 사본에서 `cp`로 복원).

| 깬 것 | 실패한 테스트 |
|---|---|
| `settings.json` 훅을 예전 `command: python` + `args` 형태로 되돌림 | `test_settings_hook_goes_through_the_cross_platform_runner`, `test_no_bare_python_command_left_in_harness_config` |
| `run_hook.sh`가 인터프리터를 못 찾을 때 조용히 `exit 0` | `test_missing_interpreter_still_asks`, `test_missing_interpreter_still_denies` |
| `planner.md` 훅을 `command: python3`으로 바꿈 | `test_agent_hooks_go_through_the_cross_platform_runner`, `test_no_bare_python_command_left_in_harness_config` |

복원 후 48개 전부 다시 통과.

## 재발 방지

- **`tests/test_harness_hooks.py` (새 파일, 35개).** 목을 쓰지 않고 실제 `run_hook.sh`를 서브프로세스로 돌려 판정 JSON을 본다. 확인하는 것: 위험 명령 14종이 `ask`로 가는가, 평범한 명령은 방해받지 않는가, 경로 제한이 `deny`를 내는가, **인터프리터가 없을 때도 판정이 나오는가**, 설정과 agent 6종이 실행기를 거치는가, `command: python` 형태로 되돌아가지 않았는가, ask · deny 규칙이 Bash · PowerShell 양쪽을 덮는가, `evidence.py`의 126 필터가 살아 있는가.
- 이 테스트는 어느 OS에서 돌리든 그 OS의 하네스를 검사한다. 환경을 또 옮길 때 `pytest -q` 한 번이 점검 절차가 된다.
- 교훈: **안전장치는 "설정에 적혀 있다"가 아니라 "이 환경에서 실제로 막는다"로 확인해야 한다.** 훅처럼 실패가 곧 통과인 장치는 살아 있는지 자체를 테스트로 고정해 둔다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 같은 계열(훅 fail-open): [hook-cp949-fail-open.md](hook-cp949-fail-open.md) — 그쪽은 훅이 예외로 죽은 경우, 이쪽은 훅이 시작조차 못 한 경우다.
- 같은 계열(하네스에 원칙 1 미적용): [subagent-permission-bypass.md](subagent-permission-bypass.md)
- 윈도우 전용 경로 문제: [msys-pathconv-windows.md](msys-pathconv-windows.md)
