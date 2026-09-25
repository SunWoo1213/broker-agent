# CI 회귀 테스트가 계획의 "모든 · 하나다" 조건을 구현에서 놓침

> 요약
> - 한 줄 해결: 계획한 검증 문장의 "모든"·"하나다"·"정확히" 같은 수량·전칭 표현마다, 그 조건을 깨는 변이(변이 표)를 반드시 하나 이상 짝짓는다. T11 · T8을 블록 전체 비교 · job별 순회로 강화해 해결했다(F1 잔여분은 미해결로 남음).
> - 원인: 계획의 변이 표(a–e)가 설정 줄 다섯 개만 다뤘고, T8("모든 job에 timeout")·T11("`contents: read` 하나다")·T10(명령 리터럴 일치)의 수량 조건을 깨는 변이가 없었다. 그래서 구현이 조건을 줄여도(다음 줄 하나만 봄, 개수만 셈) red 증거 없이 그대로 검증을 통과했다.
> - 재발 방지: `agents/planner.md`에 H1(변이 표는 검증 문장마다 수량·경계값 변이를 둔다)·H2(같은 조건을 checks와 tests에서 다른 강도로 검사하지 않는다)를, `agents/broker-builder.md`에 H3(수량 표현을 그대로 assert)을 추가 제안(사용자 승인 대기). `JOB_HEADER_RE`가 `_`로 시작하는 job id를 놓치는 잔여 결함은 **미해결** — 후속 항목 F1으로 이관.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 테스트 | 해결(주요 2건) + 미해결(F1, 경계값 1건) | ④ 구현 검증 1차 REVISE | 원칙 1 (fail-closed), 원칙 2 (자격 증명 비노출), 원칙 7 (재현성) |

## 증상

`④ 구현 검증` 1차에서 reviewer가 임시 폴더에 `ci.yml` 변형본을 두고 테스트 함수를 직접 호출하는 탐침을 했다.

- T11(`test_ci_workflow_has_no_secrets_and_read_only_token`): `permissions:` 아래에 `pull-requests: write`를 추가해도 **통과해버림**. 계획은 "최상위 `permissions:` 아래가 `contents: read` **하나다**"였는데 구현은 "다음 한 줄만" 확인했다.
- T8(`test_ci_workflow_does_not_swallow_failures`): timeout이 없는 세 번째 job을 추가해도 **통과해버림**. 계획은 "**모든** job에 `timeout-minutes:`"였는데 구현은 파일 전체의 timeout 줄 개수(2)만 고정 목록 길이와 비교했다.

r2 검증(④ 2차)을 통과한 뒤에도, 참고 지적으로 하나가 남았다: `JOB_HEADER_RE = r"^  ([a-zA-Z][\w-]*):\s*$"`가 `_`로 시작하는 job id(GitHub 문서상 허용)를 job 헤더로 인식하지 못해, `_helper:` 같은 job은 T8의 timeout 검사 대상에서 빠진다.

## 재현 방법

1. `tests/test_ci_workflow.py`의 1차 구현 상태에서
2. `.github/workflows/ci.yml` 사본에 `permissions:` 아래 `pull-requests: write`를 추가하거나, timeout 없는 job을 추가하고
3. T11 · T8 함수를 직접 호출하면 실패해야 할 상황인데 통과한다.

## 원인

1. 직접 원인: `tests/test_ci_workflow.py`의 T11이 `permissions:` 다음 한 줄만 비교했고, T8이 timeout 줄 개수만 셌다(수량·전칭 조건을 부분 조건으로 줄여 구현).
2. 왜? → 계획(`01-plan.r3.md`)의 변이 표 a–e는 `pytest.ini` 설정 줄 · `ci.yml` 실행 스텝 등 다섯 곳만 다뤘고, T8·T11·T10이 담고 있는 "모든"·"하나다"·"글자 그대로" 조건을 깨는 변이가 하나도 없었다. 그래서 ③ 구현이 조건을 줄여 짜도 자기 점검(변이 확인)에서 잡히지 않았다.
3. 왜? → 같은 조건을 검사하는 두 층(로컬 채점 스크립트 `checks/ac8_workflow_structure.py`는 YAML로 완전 일치 비교, CI 안에서 도는 `tests/test_ci_workflow.py`는 PyYAML 없이 텍스트로만 비교하도록 계획에서 지정)의 검사 강도가 달랐다. 더 강한 쪽(ac8)은 CI에서 돌지 않으므로, CI 회귀 방지라는 T8·T11의 목적(계획 65줄)에는 구멍이 남았다.
4. 근본 원인: 계획 단계에서 "먼저 쓸 테스트"의 검증 문장에 있는 수량·전칭 표현을 변이 표로 전부 덮지 않았고, 같은 조건을 검사 강도가 다른 두 곳(채점 스크립트/저장소 테스트)에 나눠 지정하면서 그 차이를 계획에 명시하지 않았다.

## 해결

- **T11** (`tests/test_ci_workflow.py:94-107`): `permissions:` 줄보다 깊게 들여쓰인 연속 줄을 전부 모아 `== ["contents: read"]`로 비교하도록 강화. 빈 줄을 만나면 건너뛰고, 들여쓰기가 얕아지면 블록이 끝난 것으로 처리.
- **T8** (`tests/test_ci_workflow.py:32-42, 60-65`): `_job_blocks` 헬퍼로 `jobs:` 섹션의 2칸 들여쓰기 job 헤더마다 블록을 잘라, job마다 `timeout-minutes:` 줄이 있는지 확인. 없는 job이 있으면 이름을 지목해 실패.
- **변이 f·g 증거 추가**: f(`permissions:`에 `pull-requests: write` 추가 → T11 red → 되돌림 → green), g(timeout 없는 `smoke` job 추가 → T8 red → 되돌림 → green). `03-build-notes.r2.md`.
- **T10 red 증거 보강(선택 지적)**: 변이 h(OPA 0건 방지 grep을 `[1-9]…`→`[0-9]…`로 약화 → T10 red → 되돌림 → green)를 추가해, 계획 변이 표에 없던 T10도 실제로 명령 변경을 잡는지 확인.
- **미해결로 남긴 것**: `JOB_HEADER_RE`의 첫 글자 클래스가 `[a-zA-Z]`라서 `_`로 시작하는 job id를 놓친다. ⑥은 이 결함을 "이번 사이클에서 수정하지 않는다"고 판정했다 — 영향 범위가 T8의 job별 timeout 검사 하나뿐이고(`if:`·`continue-on-error`·`permissions`·`secrets.` 검사는 파일 전체 텍스트 기준이라 영향 없음), 로컬 채점(`ac8_workflow_structure.py:25`, `sorted(jobs) == ["opa-test", "pytest"]`)이 job 집합 전체를 비교해 새 job이 생기면 어차피 BAD가 나기 때문이다(다만 ac8은 CI에서 돌지 않으므로 CI 안의 회귀 방지에는 구멍이 남는다). GitHub의 job 기본 타임아웃 상한(360분)이 있어 "실패를 통과로 바꾸는" 경로는 아니라고 판단해 원칙 1 위반으로 분류하지 않았다.

## 검증

- ④ r2에서 탐침 5종(T11: 두 번째 권한 추가·빈 줄 뒤 추가·`contents: write`·job 수준 permissions·원본, T8: 끝에 추가·중간 삽입·기존 job timeout 제거·job 이름 변경·원본) 전부 기대대로 동작함을 확인. 1차에서 통과해버렸던 두 탐침이 이제 실패한다.
- 변이 f·g·h의 red 로그·xml이 의도한 테스트 하나만, 원인을 메시지에 찍으며 실패했고, green에서 `ci.yml` 해시가 baseline과 동일하게 복원됨을 확인(`04-code-review.r2.md` D2).
- `--verify` 32개(1차 21개 + r2 8개 + 리뷰 로그 3개) 전부 "일치".

## 재발 방지

- `.claude/agents/planner.md` "① 계획 모드" 절에 **H1** 추가(오케스트레이터가 사용자에게 제안, 아직 파일 미수정): "변이 표는 '먼저 쓸 테스트'의 검증 문장마다 그 문장을 깨는 변이를 하나 이상 둔다. '모든·하나·정확히·없다' 같은 수량·전칭 표현이 있으면 '하나 더 추가'와 '경계값'(예: 이름 규칙의 첫 글자) 변이를 둔다."
- `.claude/agents/planner.md` "하지 말 것"에 **H2** 추가(제안): "같은 조건을 채점 스크립트(`checks/`)와 저장소 테스트(`tests/`)에 두면서 강도를 다르게 지정하기. 저장소 테스트가 더 약해야 하면 그 이유와, 약한 부분을 메우는 변이를 계획에 적는다."
- `.claude/agents/broker-builder.md` "작업 순서" 1번 아래에 **H3** 추가(제안): "계획 테스트 문장의 수량 표현('모든', '하나', '정확히')을 그대로 assert한다. 개수 비교·첫 줄 비교·고정 목록 순회로 줄이지 않는다."
- `.claude/skills/code-review-invariants/SKILL.md` "D. 증거" 표에 **H7** 추가(제안): "계획의 테스트 검증 문장 중 수량·전칭 표현이 있는 것마다, 그 조건을 깨는 변형을 임시 사본으로 만들어 테스트 함수를 직접 호출해 본다(프로젝트 파일은 바꾸지 않음). 통과해 버리면 REVISE" — 이번에 ④가 실제로 한 탐침 방식을 절차로 만드는 것.
- **F1(후속 항목, 미반영)**: `JOB_HEADER_RE` 첫 글자 클래스를 `[a-zA-Z]` → `[A-Za-z_]`로 확대, "헤더로 잡은 job 집합 == `jobs:` 아래 2칸 들여쓰기 키 전체"를 T8에 추가, 변이 i(`_helper:` job에 timeout 없이 추가 → red → 되돌림 → green) 작성. 다음에 `tests/test_ci_workflow.py`를 건드리는 항목이나 이 작업의 개선 사이클 2(U2 실패 시)에서 처리하기로 함.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|
| 2026-09-25 | 4. 정책 (Rego) (작업 D) | 계획(`01-plan.r2.md`)이 기대값 표기를 "완전히 같음"(전칭 조건, 46개 테스트에 걸침)으로 정했으나 구현(③)은 `d.result == X; d.reason == Y`라는 계획에 없는 3번째 형태로 썼다. 이 형태는 출력에 키가 더 있어도 통과해, 허용 분기 키 추가 변이(u)만 한 곳(G1)에서 이 문제를 드러냈고 거부·승인 분기(44개)는 같은 결함을 안은 채 통과할 뻔했다. ④ 구현 검증 1차 REVISE로 46개 전부를 완전 비교(`d == {"result": X, "reason": Y}`)로 강화해 해결. 근본 원인은 이번에도 "계획의 변이 표가 전칭 조건을 깨는 변이를 일부 분기에서만 뒀다"는 같은 유형(사이클1 ⑥ 발견사항 (a), H1·H2·H3 제안). 상세: [work-items/20260925-rego-policy](../work-items/20260925-rego-policy/verification.md#④-구현-검증-사이클-1) |

## 관련

- 작업 페이지: [개요](../work-items/20260924-pytest-ci/index.md) · [검증 기록](../work-items/20260924-pytest-ci/verification.md) · [테스트 기록](../work-items/20260924-pytest-ci/testing.md)
- 재발: [4. 정책 (Rego) (작업 D)](../work-items/20260925-rego-policy/index.md)
