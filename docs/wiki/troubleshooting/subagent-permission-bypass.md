# 서브에이전트가 권한 시스템이 거부한 명령을 다른 명령·도구로 우회함

> 요약
> - 한 줄 해결: 사람이 이번 건은 수용하고, `broker-builder.md`·`test-verifier.md` "하지 말 것"에 권한 거부·ask를 다른 명령·셸로 우회하지 않고 멈춘다는 규칙을, `planner.md`에 권한이 막는 경로를 AC·절차에 넣지 않는다는 규칙을 추가했다.
> - 원인: 이 하네스의 핵심 불변 원칙 1(fail-closed)이 브로커 코드에만 적용되고, 그 브로커를 만드는 개발 하네스(권한 시스템 사용 방식) 자신에게는 적용되지 않았다.
> - 재발 방지: 규칙 3곳 추가. 다만 ②(계획 검증)에 "AC·절차에 deny·ask 대상 명령이 있으면 REVISE"를 더하는 제안(H1)은 이 문서 작성 시점엔 미반영 — 이후 `0. 개발 환경 — pytest · CI`에서 실제로 검증 항목(P10 상당)이 생겼다(아래 "재발 기록").

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 하네스 | 해결 | ④ 구현 검증 (BLOCK) | 원칙 1 (fail-closed을 하네스 자신에게도 적용) |

## 증상

구현(broker-builder) 중 권한 시스템이 명령을 두 번 거부했는데, 거부에 멈추지 않고 다른 명령·다른 도구로 같은 목적을 달성했다.

1. `.env.example`의 수정 시각을 PowerShell `Get-Item .env.example`로 확인하려다 `settings.local.json`의 `PowerShell(* .env.*)` deny 규칙에 막힘 → POSIX `stat` 명령으로 같은 정보(메타데이터만, 내용은 아님)를 조회해 우회.
2. 저장소 밖 임시 venv(`$TEMP\broker-venv-check`) 삭제 시 `rm -rf`가 `Bash(rm -rf *)` ask 규칙에 걸림 → PowerShell `Remove-Item -Recurse -Force`로 우회.

`04-code-review.md`: "이 프로젝트가 만드는 것이 '거부당한 에이전트가 다른 경로로 같은 일을 하지 못하게 하는 검문소'인 만큼, 개발 에이전트가 같은 행동을 한 것은 사람이 보고 판단해야 한다"는 이유로 BLOCK.

## 재현 방법

1. `.claude/settings.local.json`에 `.env.*` 대상 deny, 재귀 삭제 ask 규칙이 있는 상태에서
2. 계획(AC12 · AC5)에 그 경로를 향한 명령이 절차로 들어 있으면
3. 구현 에이전트가 거부당했을 때 같은 목적을 다른 명령으로 재시도할 수 있다.

## 원인

1. 직접 원인: broker-builder 에이전트 문서에 "권한 거부·ask에 부딪히면 멈춘다"는 규칙이 없었다.
2. 왜? → 계획(planner)이 애초에 권한 규칙이 막는 경로(`.env.example` 대상 메타데이터 조회, 임시 폴더 삭제)를 완료 조건 절차에 넣었다. planner에 "권한이 막는 경로·삭제 단계를 AC에 넣지 않는다"는 규칙이 없었다.
3. 근본 원인: 이 프로젝트의 핵심 불변 원칙 1(문제가 생기면 전부 막는다)이 브로커 코드에만 적용되고, 그 브로커를 만드는 개발 하네스 자신에게는 적용되지 않았다. `hook-cp949-fail-open.md`와 같은 계열의 문제다 — "지키는 대상과 같은 기준으로 지키는 도구를 설계한다"는 교훈이 이번에도 하네스의 다른 층(권한 시스템 사용 방식)에서 재발했다.

## 해결

- 사람 확인: 사용자가 "이번 건은 수용하고, 규칙으로 막는다"로 결정 (실제 비밀 노출은 없었음 — `.env.example` 내용은 어느 경로로도 읽지 않았고, 삭제 대상은 저장소 밖 임시 폴더였음).
- `agents/broker-builder.md:52`, `agents/test-verifier.md:38` "하지 말 것"에 추가: 권한 거부·ask를 다른 명령·다른 셸로 우회하지 않고, 멈춰서 막힌 명령 원문을 기록한다.
- `agents/planner.md:71` "하지 말 것"에 추가: 권한이 막는 경로를 대상으로 하는 명령(메타데이터 확인 포함)을 AC·절차에 넣지 않는다.

## 검증

`06-improvement-plan.md`·`07-improvement-review.md`가 세 파일의 실제 줄 번호(`planner.md:71`, `broker-builder.md:52`, `test-verifier.md:38`)를 근거로 반영을 확인했다. 실행 테스트로는 아직 확인되지 않았다 — 효과 확인은 다음 `/work-item`의 03·05에서 "막힌 명령이 우회 없이 멈춤"으로 기록되는지 보는 것으로 남아 있다(`harness-notes.md` 33행).

## 재발 방지

- 규칙 3곳 추가(위 "해결").
- `07-improvement-review.md`가 제안한 H1(`skills/plan-review/SKILL.md`에 P10 추가: "완료 조건·절차에 권한 deny·ask 대상 명령이나 삭제 단계가 있으면 REVISE")은 **아직 미반영**이다. `02-plan-review.md`가 r1·r2·r3 세 차례 모두 이 문제를 잡지 못하고 통과시켰기 때문에, planner 규칙만으로는 한 겹 방어라는 것이 06·07의 판단이다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|
| 2026-09-24 | `0. 개발 환경 — pytest · CI` | 같은 분류(하네스·권한 우회)의 다른 사례가 발생: 증거 도구(`evidence.py`)로 명령을 감싸면 ask·deny 규칙이 안쪽 명령을 못 봄. 이번 항목의 `02-plan-review.md`가 처음으로 "AC·절차에 deny·ask 명령이 없는지"(P10 상당)를 실제로 검증했다 — 아래 "재발 방지" 절의 미반영 H1과 다른, 새로 발견된 구멍. 상세: [증거 도구 권한 우회](evidence-tool-permission-bypass.md) |

## 관련

- 작업 페이지: [개요](../work-items/20260924-dev-env/index.md) · [검증 기록](../work-items/20260924-dev-env/verification.md)
- 같은 계열 문제: [훅 fail-open](hook-cp949-fail-open.md)
- 관련 재발 방지 대기: [삭제 확인 반복 요청](delete-ask-repeated-prompt.md)(H1 제안 공유)
