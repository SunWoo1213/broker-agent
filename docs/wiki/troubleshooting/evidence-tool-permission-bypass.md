# 증거 도구(evidence.py)로 명령을 감싸면 ask · deny 권한 규칙을 비껴감

> 요약
> - 한 줄 해결: `evidence.py`가 실행 전에 `.claude/settings*.json`의 Bash · PowerShell ask · deny 규칙 조각을 명령 문자열 전체에서 단어 단위로 찾아, 걸리면 실행하지 않고 종료 코드 126으로 거부하게 만들었다.
> - 원인: Claude Code의 권한 규칙은 명령의 **앞부분**만 보고 매칭한다. `evidence.py <run> <라벨> "curl ..."`처럼 실제 명령을 문자열 인자로 감싸면, 권한 시스템이 보는 것은 `evidence.py ...`뿐이라 안쪽의 `curl`이 규칙을 비껴간다.
> - 재발 방지: evidence.py 자체에 126 필터를 추가(fail-closed). ask 대상 명령(`git push`, `curl`)은 도구로 감싸지 말고 직접 실행해 사람 확인을 받은 뒤, 그 출력만 `evidence.py … "cat <파일>"`로 기록하는 절차를 계획(`01-plan.r3.md`)·`test-gate` Skill에 명시.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 하네스 | 해결 | ① 계획 작성 중 planner 자체 발견 (r1→r2 작업 도중) | 원칙 1 (fail-closed을 증거 도구 자신에게도 적용) |

## 증상

`0. 개발 환경 — pytest · CI` 작업의 r2 계획 작성 중, "모든 AC를 evidence.py로 실행해 흔적을 남긴다"는 사용자 지시를 반영하다가, evidence.py로 감싼 명령은 `.claude/settings.json` · `settings.local.json`의 Bash ask/deny 규칙(`curl`, `git push`, `docker run` 등)을 통과해 버린다는 사실이 드러났다. 예:

```
.venv/Scripts/python .claude/tools/evidence.py <run> u2-check 'curl -s "https://api.github.com/..."'
```

이 명령은 evidence.py라는 허용된 실행 파일 호출로만 보이기 때문에 ask 창이 뜨지 않고 바로 실행된다.

## 재현 방법

1. `.claude/settings.local.json`에 `Bash(curl *)` 같은 ask 규칙이 있는 상태에서
2. `evidence.py <run> <라벨> "curl ..."`처럼 도구의 명령 인자 안에 그 패턴을 넣으면
3. 권한 시스템은 `evidence.py`만 보고 통과시키고, 안쪽 `curl`은 확인 없이 실행된다.

## 원인

1. 직접 원인: `evidence.py`가 명령 문자열을 그대로 `bash -lc`에 넘겨 실행하면서, 자신을 감싸는 도구가 권한 규칙의 매칭 대상에서 빠진다는 것을 고려하지 않았다.
2. 왜? → Claude Code의 권한 규칙은 명령 전체를 파싱하지 않고 앞부분(호출된 실행 파일 · 첫 인자)만 본다. 새로 만든 도구(evidence.py)를 규칙 목록에 등록하지 않았으므로, "이 도구를 통해 실행되는 모든 것을 규칙 검사 대상으로 삼는다"는 장치가 애초에 없었다.
3. 근본 원인: 증거를 남기는 도구를 설계할 때 "무엇을 기록할 것인가"만 설계하고 "권한 시스템과 같은 fail-closed 기준으로 스스로도 막을 것인가"를 계획 초안(r1)에 넣지 않았다. `subagent-permission-bypass.md`(다른 작업에서 발견)와 같은 계열 — 이 프로젝트가 만드는 것 자체가 "거부당한 요청이 다른 경로로 같은 일을 하지 못하게 하는 검문소"인데, 그 검문소를 만드는 하네스의 새 도구가 같은 종류의 구멍을 또 만들었다.

## 해결

- `.claude/tools/evidence.py`에 권한 필터를 추가했다. `.claude/settings*.json`의 Bash · PowerShell ask · deny 규칙 조각(`curl`, `wget`, `dd`, `del`, `gh`, `rm`, `rm -r`, `docker run`, `docker rm`, `git push`, `git commit`, `git remote`, `git restore`, `git clean`, `.env`, `.env.` 등, 총 54개)을 명령 문자열 어디에든 **단어 경계 패턴**(`(?<![\w-])조각(?![\w-])`, 대소문자 무시)으로 대조한다. 하나라도 걸리면 실행하지 않고 종료 코드 **126**으로 끝낸다. 이때 로그는 남지 않는다(사전 거부이므로).
- 설정 파일을 읽지 못해도 거부한다(fail-closed).
- ask 대상 명령이 꼭 필요한 곳(U1의 `git push`, U2의 `curl` GET 3건)은 evidence.py로 감싸지 않는다. 직접 실행해 ask 창(=사람 확인)을 거친 뒤, 출력을 `evidence/raw-<라벨>.txt`로 저장하고 `evidence.py <run> <라벨> "cat <그 파일>"`로만 기록한다. `curl`을 python · httpx 같은 다른 도구로 바꿔 ask를 피하지 않는다.
- 계획 단계(r3)에서 이 계획의 evidence.py 명령 36개(③ 자기 점검 + AC0–AC14 + U1–U3)를 `evidence.blocked_by()` 함수에 실제로 넣어 전부 `None`(통과)임을, 대조군 4개(`git push`, `curl`, `git remote -v`, `docker run`)는 전부 126 거부 대상임을 사전에 확인했다(`02-plan-review.md` P11 보강).

```python
# .claude/tools/evidence.py 발췌 개념 — 실제 구현은 정규식 조각 54개를 순회
def blocked_by(command: str) -> str | None:
    for rule in load_ask_deny_rule_fragments():
        if re.search(rf"(?<![\w-]){re.escape(rule)}(?![\w-])", command, re.I):
            return rule
    return None
```

## 검증

- 계획(②) 단계: `blocked_by()`를 계획의 evidence.py 명령 36개 + 대조군 4개에 대해 실제로 호출해 확인(실행은 안 함). `02-plan-review.md` "P11 보강" 절.
- 구현(③④⑤) 단계: 03·03.r2·05 전 과정에서 126 거부 0건("126 거부: 없음"), 즉 계획된 명령은 전부 필터를 통과하고 대조군에 해당하는 명령(U1 push, U2 curl)은 계획대로 도구 밖에서 직접 실행됐다.
- `checks/ac13_forbidden_commands.py`가 evidence.py 로그(`u1-`·`u2-`·`u3-` 제외)에서 금지 명령이 없는지 한 번 더 확인(두 번째 겹). ④·⑤ 모두 `0 bad`.

## 재발 방지

- `.claude/tools/evidence.py`에 126 필터 코드 추가(위 "해결").
- `test-gate` Skill(또는 관련 절차)에 "ask 대상 명령은 증거 도구로 감싸지 않고 직접 실행 → 출력 파일 → `cat`으로 기록" 절차 명시(`harness-notes.md` 64–67행).
- 계획 검증(②) 체크리스트에 "AC · 절차에 deny · ask 명령이 없는지" 항목(P10 상당)이 반영되어, 이번 작업에서 실제로 이 필터의 유효성을 사전 검증하는 근거가 됐다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|
| 2026-09-24 | `0. 개발 환경 — pytest · CI` | 이 문제를 처음 발견하고 해결. `subagent-permission-bypass.md`가 제안했던 "완료 조건·절차에 권한 deny·ask 대상 명령이 있으면 REVISE"(P10 상당)가 이번 `02-plan-review.md`에서 실제로 적용된 사례이기도 하다 |

## 관련

- 작업 페이지: [개요](../work-items/20260924-pytest-ci/index.md) · [검증 기록](../work-items/20260924-pytest-ci/verification.md) · [테스트 기록](../work-items/20260924-pytest-ci/testing.md)
- 같은 계열 문제: [서브에이전트의 권한 우회](subagent-permission-bypass.md)(에이전트가 거부된 명령을 다른 명령으로 재시도한 사례 — 이번 문제는 도구 설계 자체의 구멍이라는 점이 다르다)
