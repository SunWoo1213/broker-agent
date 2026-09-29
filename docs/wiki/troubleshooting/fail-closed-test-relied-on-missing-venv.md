# 훅 fail-closed 테스트가 `.venv`가 없던 덕에 우연히 통과하고 있었음

> 요약
> - 한 줄 해결: "인터프리터 없음" 테스트는 PATH만 비우지 말고, `.venv`가 없는 임시 저장소(갓 clone한 상태)에 `run_hook.sh`와 훅 스크립트를 복사해 거기서 실행한다.
> - 원인: `run_hook.sh`는 PATH보다 먼저 `<저장소>/.venv/bin/python`을 찾는다. 이 저장소 안에서 PATH만 비우면 `.venv`가 생긴 뒤로는 인터프리터가 여전히 발견되므로, 테스트가 노리던 실패 조건 자체가 만들어지지 않는다.
> - 재발 방지: 테스트에 `_runner_without_a_venv()` 헬퍼를 두어 실패 조건을 환경에 기대지 않고 직접 만든다.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-29 | 하네스 | 해결 | 직접 발견 (맥 환경 준비 후 하네스 점검) | 원칙 1 (fail-closed), 원칙 7 (기준을 결과에 맞춰 바꾸지 않는다) |

## 증상

맥에 Python 3.13.7과 `.venv`를 만든 직후, 하네스 점검 명령
`sh .claude/tools/python.sh -m pytest -q tests/test_harness_hooks.py`에서 35개 중 2개가 실패했다.

```
    def test_missing_interpreter_still_denies(tmp_path):
        out = _decision(_run_hook("deny", "guard_paths.py", ".claude/runs",
                                  payload={"tool_input": {"file_path": ".claude/runs/ok.md"}},
                                  env=_env_without_python(tmp_path)))
>       assert out is not None, "guard_paths failed open when no interpreter was available"
E       AssertionError: guard_paths failed open when no interpreter was available
E       assert None is not None

tests/test_harness_hooks.py:177: AssertionError
=========================== short test summary info ============================
FAILED tests/test_harness_hooks.py::test_missing_interpreter_still_asks - Ass...
FAILED tests/test_harness_hooks.py::test_missing_interpreter_still_denies - A...
2 failed, 33 passed in 0.89s
```

실패 메시지("failed open")만 보면 훅이 뚫린 것처럼 읽히지만, **뚫린 것은 훅이 아니라 테스트의 전제**였다.

## 재현 방법

1. `.venv`가 없는 저장소에서 `tests/test_harness_hooks.py`를 돌린다 → 35개 통과.
2. 저장소 루트에 `.venv`를 만든다.
3. 같은 명령을 다시 돌린다 → 위 2개가 실패한다.

## 원인

1. 직접 원인: `_decision()`이 `None`을 돌려줬다. 즉 훅이 아무 판정도 내지 않았고, 그것은 훅이 정상적으로 실행돼 "막을 이유 없음"으로 끝났다는 뜻이다. 테스트가 넘긴 입력(`ls`, `.claude/runs/ok.md`)은 원래 막히지 않는 입력이다.
2. 왜 실행됐나? → `_env_without_python()`은 `PATH`를 빈 폴더로 바꿔 인터프리터를 못 찾게 만드는 방식인데, `run_hook.sh`의 `find_python()`은 **PATH를 보기 전에** `$repo_root/.venv/bin/python`(윈도우는 `.venv/Scripts/python.exe`)을 먼저 확인한다(`.claude/hooks/run_hook.sh` `find_python`). 절대 경로라서 PATH와 무관하게 찾힌다.
3. 근본 원인: 이 순서는 훅을 살리기 위한 **의도된 설계**다(PATH가 이상해도 훅이 돌아야 한다 — [hooks-dead-on-macos.md](hooks-dead-on-macos.md)). 문제는 테스트가 실패 조건을 **직접 만들지 않고 "이 기계에 `.venv`가 없다"는 환경 상태에 기대고 있었다**는 점이다. 테스트를 쓴 시점(2026-09-29, 맥 이전 직후)에는 `.venv`가 아직 없어서 통과했고, 그래서 통과가 우연이라는 사실이 드러나지 않았다.

이 테스트가 확인하려던 상황은 정확히 **갓 clone해서 `.venv`가 아직 없는 기계**다. 그 조건을 임시 폴더로 만들어야 했다.

## 해결

`tests/test_harness_hooks.py`에 헬퍼를 추가하고, 두 테스트가 그 실행기를 쓰게 했다.

```python
def _runner_without_a_venv(tmp_path: Path, script: str) -> Path:
    hooks = tmp_path / "fresh-clone" / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    shutil.copy2(RUNNER, hooks / RUNNER.name)
    shutil.copy2(HOOKS / script, hooks / script)
    return hooks / RUNNER.name
```

`run_hook.sh`는 `$0`에서 자기 위치를 구해 `repo_root`를 정하므로, 복사된 실행기의 `repo_root`는 임시 폴더가 되고 그곳에는 `.venv`가 없다. `_run_hook()`에는 `runner` 인자를 더해 이 실행기를 가리키게 했다. 훅 스크립트 두 개(`guard_critical.py`, `guard_paths.py`)는 표준 라이브러리만 쓰므로(`json`·`re`·`os`·`sys`) 복사해도 동작이 같다.

**`run_hook.sh`와 훅 본체는 고치지 않았다.** 동작이 옳았기 때문이다.

## 검증

```
$ sh .claude/tools/python.sh -m pytest -q tests/test_harness_hooks.py
...................................                                      [100%]
35 passed in 0.83s

$ sh .claude/tools/python.sh -m pytest -q
................................................                         [100%]
48 passed in 4.29s
```

테스트와 별개로, 빈 환경(`env -i`)·빈 PATH에서 실행기를 손으로 돌려 판정 JSON이 실제로 나오는지 확인했다.

```
$ echo '{"tool_input":{"file_path":".claude/runs/ok.md"}}' \
    | env -i PATH=/tmp/fc-check /bin/sh fc-check/.claude/hooks/run_hook.sh deny guard_paths.py .claude/runs
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[하네스] 실행 가능한 python 을 찾지 못해 훅을 돌리지 못했습니다. 통과시키지 않고 막습니다 (fail-closed). .claude/hooks/run_hook.sh 참고."}}
```

즉 훅의 fail-closed는 처음부터 정상이었고, 이제 테스트도 그 사실을 환경과 무관하게 확인한다.

## 재발 방지

- 추가한 테스트: 새 테스트를 늘리지 않고 기존 2개가 **실패 조건을 스스로 만들도록** 고쳤다(`_runner_without_a_venv`). 이제 `.venv`가 있든 없든 같은 결과가 나온다.
- 규칙: 안전장치(fail-closed) 테스트는 "이 기계에 무엇이 없다"는 환경 상태를 조건으로 삼지 않는다. 없어야 하는 것을 테스트가 직접 만들어야, 환경이 바뀌었을 때 조용히 무력해지지 않는다. 이것은 [ci-test-spec-quantifier-weakening.md](ci-test-spec-quantifier-weakening.md)와 같은 계열의 문제다 — **테스트가 통과한다는 사실만으로는 테스트가 무엇을 확인했는지 알 수 없다.**

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- [hooks-dead-on-macos.md](hooks-dead-on-macos.md) — 이 테스트가 생겨난 원래 사건(훅이 맥에서 전부 죽어 fail-open)
- [ci-test-spec-quantifier-weakening.md](ci-test-spec-quantifier-weakening.md) — 테스트가 의도한 것을 실제로 확인하지 못한 같은 계열의 문제
- `.claude/hooks/run_hook.sh` `find_python` — `.venv`를 먼저 찾는 순서의 근거
