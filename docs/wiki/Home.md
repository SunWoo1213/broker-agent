# 에이전트 권한 브로커 — 개발 위키

> 작업 하나가 어떻게 진행됐는지, 어떤 문제가 있었고 어떻게 풀었는지를 기록한다.
> 기록 규칙: `.claude/skills/dev-wiki/SKILL.md` · 템플릿: [`_templates/`](_templates/)
> 설계는 [`docs/architecture.md`](../architecture.md), 결정은 [`docs/decisions.md`](../decisions.md), 계획은 [`docs/plan.md`](../plan.md)

이 페이지는 세 가지 입구를 둔다: **① 무슨 작업이 있었나**(작업 로그) · **② 지금 겪는 증상으로 찾기**(문제 해결) · **③ "왜 이렇게 되어 있지?"에 답함**(주제별 색인). 처음부터 끝까지 읽지 않아도 되도록 설계됐다 — 필요한 절만 찾아 읽으면 된다.

## 개발 프로세스

상세 설명: **[process.md](process.md)** — 단계별 담당 · 통과 기준 · 검증과 테스트의 차이 · 안전장치

작업 하나는 `/work-item <plan.md 항목>`으로 진행하고, 끝나거나 중단되면 이 위키에 기록된다.

```
①계획 → ②계획 검증 → 🧑승인 → ③구현 → ④구현 검증 → ⑤테스트 → ⑥개선사항 계획 → ⑦개선 계획 검증 → 📝위키 기록 → 🧑커밋 승인
```

## 진행 현황

| 단계 | 목표 | 상태 |
|---|---|---|
| 0 | 개발 하네스 | 완료 |
| 1 | 게이트웨이 ①②③⑦ + 모의 도구 + 데모 에이전트 | 진행 중 (0. 개발 환경 — venv·버전 고정·compose 기동 완료, pytest·CI 완료, 4. 정책(Rego) 완료) |
| 2 | 승인, 임시 토큰 | 대기 |
| 3 | 누적 한도, 동시성, 공격 평가 1차 | 대기 |
| 4 | 감사 로그, 취소 전파 | 대기 |
| 5 | AWS · Terraform, 부하 테스트 | 대기 |
| 6 | 수치 정리, 시연 | 대기 |

---

## 입구 1 — 작업 로그 (날짜순)

| 날짜 | 항목 | 결과 | 관문 재시도 | 기록 |
|---|---|---|---|---|
| 2026-09-24 | 개발 하네스 구성 | 완료 | 해당 없음(하네스 구성 전) | [개요](work-items/20260924-harness-setup/index.md) · [검증](work-items/20260924-harness-setup/verification.md) · [테스트](work-items/20260924-harness-setup/testing.md) |
| 2026-09-24 | 0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동 | 완료 | ② 2회(REVISE→APPROVE) · ④ 1회(BLOCK→사람 해제) · ⑦ 0회 | [개요](work-items/20260924-dev-env/index.md) · [검증](work-items/20260924-dev-env/verification.md) · [테스트](work-items/20260924-dev-env/testing.md) |
| 2026-09-24 | 0. 개발 환경 — pytest · CI | 완료 (U1 푸시 · U2 Actions run #1 성공 · U3 plan.md 체크) | ② 1회(r3 대상 APPROVE) · ④ 2회(1차 REVISE→2차 APPROVE) · ⑦ 1회(APPROVE) | [개요](work-items/20260924-pytest-ci/index.md) · [검증](work-items/20260924-pytest-ci/verification.md) · [테스트](work-items/20260924-pytest-ci/testing.md) |
| 2026-09-25 | 4. 정책 (Rego) (작업 D) | 완료 (d9b6b16, Actions 성공) | ② 1회(REVISE→APPROVE) · ④ 사이클1 1회(REVISE→APPROVE)·사이클2 0회 · ⑦ 사이클1 2회(REVISE→REVISE→APPROVE)·사이클2 0회 · 개선 사이클 2회 | [개요](work-items/20260925-rego-policy/index.md) · [검증](work-items/20260925-rego-policy/verification.md) · [테스트](work-items/20260925-rego-policy/testing.md) |

---

## 입구 2 — 문제 해결 (지금 겪는 증상으로 찾기)

### 환경

| 문제 | 이럴 때 보세요 (증상 · 에러 문구) | 상태 | 날짜 | 링크 |
|---|---|---|---|---|
| 호스트 PostgreSQL 포트가 다른 프로젝트 컨테이너와 충돌(5433) | `docker compose up` 시 포트 바인딩 실패, 5432·5433이 이미 다른 컨테이너(`capstone2-postgres-1`, `finance_postgres`)에서 사용 중 | 해결(5434로 변경) | 2026-09-24 | [링크](troubleshooting/host-port-5433-conflict.md) |
| Windows Git Bash가 컨테이너 안 절대경로를 Windows 경로로 잘못 변환 | `docker compose exec opa /opa ...` 류 명령이 컨테이너 안에서 경로를 못 찾음(`/opa`가 `C:/Program Files/Git/opa`처럼 변환됨) | 해결(`MSYS_NO_PATHCONV=1`, 2026-09-25 reviewer 탐침에서 재발) | 2026-09-24 | [링크](troubleshooting/msys-pathconv-windows.md) |
| 세션 재개 때 Docker Desktop이 꺼져 있어 무효 red 로그가 남음 | 변이 red 로그의 종료 코드가 ≠0이지만 `docker API` 연결 오류(`failed to connect to the docker API`)만 있고 `PASS:`/`FAIL:` 요약 줄이 없음 | 해결(Docker 기동 후 재실행) | 2026-09-25 | [링크](troubleshooting/session-resume-docker-down-invalid-red-log.md) |

### 하네스

| 문제 | 이럴 때 보세요 (증상 · 에러 문구) | 상태 | 날짜 | 링크 |
|---|---|---|---|---|
| 승인 훅이 인코딩 오류로 죽으면서 명령을 통과시킴 (fail-open) | 훅 출력에 `UnicodeEncodeError: 'cp949' codec can't encode character` 뒤 `(pass)` — 승인 없이 명령이 진행됨 | 해결 | 2026-09-24 | [링크](troubleshooting/hook-cp949-fail-open.md) |
| 서브에이전트가 권한 시스템 거부 명령을 다른 명령·도구로 우회 | deny·ask에 막힌 명령을 `stat`, `Remove-Item` 같은 다른 명령·도구로 다시 시도한 흔적이 보임 | 해결(사람 확인 후 규칙 추가) | 2026-09-24 | [링크](troubleshooting/subagent-permission-bypass.md) |
| 임시 폴더 삭제가 ask 규칙에 걸려 확인 요청이 반복됨 | 같은 작업 안에서 삭제 확인 창이 여러 번 뜸 | 해결(정책 결정: 계획에서 삭제 단계 제거) | 2026-09-24 | [링크](troubleshooting/delete-ask-repeated-prompt.md) |
| 증거 도구(evidence.py)로 명령을 감싸면 ask·deny 권한 규칙을 비껴감 | `evidence.py <run> <라벨> "curl ..."`처럼 ask 대상 명령을 감쌌는데 확인 창이 안 뜨고 바로 실행됨 | 해결(126 필터 추가) | 2026-09-24 | [링크](troubleshooting/evidence-tool-permission-bypass.md) |
| evidence 로그에서 자식 Python의 한국어 출력이 깨짐 | 로그에 한국어 부분이 `U+FFFD`(깨진 문자)로 저장됨. 판정 토큰(`OK`·`HUMAN`·`BAD`)은 정상 | 해결 (H13, 2026-09-25) | 2026-09-25 | [링크](troubleshooting/evidence-log-cp949-garbled-output.md) |
| 개선 사이클에서 사용자 승인된 설계 결정(decisions.md) 반영 시점이 규칙과 어긋남 | ⑦ 검토에서 "decisions.md 보강을 '마무리'로 미룸이 `work-item/SKILL.md`·`CLAUDE.md`와 어긋난다"는 REVISE가 남 | 해결(승인 직후·다음 ③ 전으로 순서 교정) | 2026-09-25 | [링크](troubleshooting/improvement-cycle-decision-timing.md) |

### 구현

| 문제 | 이럴 때 보세요 (증상 · 에러 문구) | 상태 | 날짜 | 링크 |
|---|---|---|---|---|
| 계획 밖에 넣은 더 엄격한 규칙에 거부 테스트가 하나도 없음 | ④ 구현 검증에서 "diff에 들어간 규칙마다 거부 테스트가 있는지" 지적, `grep`으로 찾으면 그 필드가 고정값 한 곳에만 등장 | 해결(계약으로 승격 + 거부 테스트·변이 추가) | 2026-09-25 | [링크](troubleshooting/strict-rule-without-deny-test.md) |
| 변이 되돌림 Edit가 파일 끝 개행 문자를 함께 지움 | 되돌린 뒤 정책 파일 해시가 기준선과 다름, `git diff`에 `\ No newline at end of file` | 해결(`printf '\n' >>`로 복구, 사본 덮어쓰기로 재발 방지 제안) | 2026-09-25 | [링크](troubleshooting/mutation-revert-edit-strips-trailing-newline.md) |

### 테스트

| 문제 | 이럴 때 보세요 (증상 · 에러 문구) | 상태 | 날짜 | 링크 |
|---|---|---|---|---|
| CI 회귀 테스트가 계획의 "모든·하나다" 조건을 놓침 | 탐침(임시로 `permissions:`에 권한 한 줄 추가, timeout 없는 job 추가)에서 테스트가 실패해야 하는데 통과해버림 | 해결(주요 2건, T11·T8 강화) + 미해결(F1, `_`로 시작하는 job id 경계값) + 2026-09-25 재발(정책 테스트 46개, 완전 비교로 강화) | 2026-09-24 | [링크](troubleshooting/ci-test-spec-quantifier-weakening.md) |

---

## 입구 3 — 주제별 색인 ("왜 이렇게 되어 있지?")

| 주제 | 정해진 것 | 근거 |
|---|---|---|
| PostgreSQL 호스트 포트 | 기본값 `5434`(5433·5432는 다른 로컬 프로젝트가 사용 중이라 피함) | [host-port-5433-conflict.md](troubleshooting/host-port-5433-conflict.md) |
| `.env.example` → `env.example` | `.claude/settings.json`의 `.env.*` deny가 `.env.example`까지 막아서, 변수 이름 목록 파일 이름을 점 없는 `env.example`로 바꾸고 deny는 그대로 유지 | `.claude/harness-notes.md:42, 48` |
| 권한 거부 · ask 우회 금지 | deny·ask에 막힌 명령을 다른 명령·셸로 재시도하지 않고 멈춰서 막힌 명령 원문을 기록한다(`agents/broker-builder.md`·`test-verifier.md` "하지 말 것") | `.claude/harness-notes.md:31`, [subagent-permission-bypass.md](troubleshooting/subagent-permission-bypass.md) |
| 삭제 단계 금지 | 완료 조건 · 절차에 삭제 단계를 넣지 않는다. 임시 산출물은 경로만 기록하고 실제 삭제는 사람이 판단해 직접 한다(`agents/planner.md` "하지 말 것") | `.claude/harness-notes.md:34-35`, [delete-ask-repeated-prompt.md](troubleshooting/delete-ask-repeated-prompt.md) |
| 증거 도구 `evidence.py` (+126 필터) | 모든 테스트 · 검증 명령은 `.claude/tools/evidence.py`로 실행해 로그·해시(`MANIFEST.tsv`)를 남긴다. `.claude/settings*.json`의 ask·deny 규칙 조각이 명령 어디에든 있으면 실행 없이 종료 코드 126으로 거부(fail-closed). ask 대상 명령(`git push`, `curl`)은 도구로 감싸지 않고 직접 실행 → 출력 파일 → `evidence.py … "cat 파일"`로만 기록 | `.claude/harness-notes.md:52-67`, [evidence-tool-permission-bypass.md](troubleshooting/evidence-tool-permission-bypass.md) |
| 채점 스크립트 `checks/` 예외 | planner가 `<run>/checks/`에 완료 조건 판정 스크립트를 미리 써서 결과보다 먼저 기준을 고정할 수 있다(원칙 7). 채점만 하고 제품 코드·`tests/`는 여전히 쓰지 않으며, ③·⑤는 이 스크립트를 고치지 않는다 | `.claude/agents/planner.md:23-26`, `.claude/harness-notes.md:68` |
| `00-approval.md` (작업 중 사람 변경 기록) | 계획 승인 시각 · 사용자 답 원문과, ③–⑤ 진행 중 사람(오케스트레이터·사용자)이 작업 트리에 한 변경을 표로 남긴다 | `.claude/harness-notes.md:39, 46` |
| 계획 검증 P10 · P11 | ②(계획 검증)는 완료 조건 · 절차에 권한 deny·ask 대상 명령이나 삭제 단계가 없는지(P10), 완료 조건마다 무엇이 증거로 남는지가 적혀 있는지(P11)를 확인해야 APPROVE를 낸다 | `.claude/skills/plan-review/SKILL.md:21, 23` |
| 새 환경 설치 확인은 CI로 대신 | 로컬 임시 venv로 "빈 환경 설치" 확인하는 단계는 CI(GitHub Actions)가 생기기 전까지만 쓴다. pytest·CI 항목 이후에는 CI의 빈 환경 설치·테스트 통과로 대신한다 | `.claude/harness-notes.md:50` |
| 위키 골라 읽기 규칙 | 모든 위키 페이지 첫머리에 `> 요약` 3줄(결론·바뀐 것·다음에 알아야 할 것)을 둔다. 트러블슈팅 페이지는 요약 첫 줄이 "한 줄 해결". Home은 이 페이지처럼 세 입구(작업 로그·분류별 문제 해결·주제별 색인) 구조를 쓴다 | `.claude/skills/dev-wiki/SKILL.md` "골라 읽기 규칙" 절, `.claude/harness-notes.md:70-74` |
| 계획의 검증 문장은 변이로 덮는다 | 계획 테스트 문장에 "모든·하나·정확히" 같은 수량·전칭 표현이나 보안 관련 검사(권한·fail-closed·실패 무시 금지)가 있으면, 그 문장을 깨는 변이(red→되돌림→green 증거)를 계획에 반드시 짝짓는다. **테스트 여러 개에 공통으로 걸리는 규칙(기대값 표기 "완전히 같음" 등)도 전칭 문장이며, 그 규칙이 걸리는 출력 분기(거부·승인·허용)마다 변이가 하나씩 있어야 한다** | `.claude/agents/planner.md:57`, [ci-test-spec-quantifier-weakening.md](troubleshooting/ci-test-spec-quantifier-weakening.md) |
| OPA 정책 D18 입력·출력 계약 | 입력 `{agent, user, action:{name, risk}, delegation:{scopes, per_tx_limit, expires_at}, args}` → 출력 `{result: allow\|deny\|require_approval, reason}`. 1단계는 승인 경로도 `deny`로 낸다(상수 `approval_result` 하나, 2단계에서 교체). `mail.send`의 `to`·`subject`·`body`는 모두 필수 | `docs/decisions.md` D18, [work-items/20260925-rego-policy](work-items/20260925-rego-policy/index.md) |
| 계획 밖 규칙에도 거부 테스트를 같이 쓴다 | 계획에 없는 규칙(더 엄격한 검사 포함)을 구현에 넣으면, "계획의 테스트 목록에 없다"는 이유로 테스트 없이 두지 않고 그 규칙의 거부 테스트를 함께 쓴다 | [strict-rule-without-deny-test.md](troubleshooting/strict-rule-without-deny-test.md) |
| 개선 사이클의 설계 결정 반영 시점 | 사용자 확인을 받은 설계 결정(decisions.md)은 다음 구현(③) 시작 **전에** 반영한다. 범위 검사(AC6)의 해시 보호는 미룰 이유가 아니라 `00-approval.md` 표에 기록할 대상이다 | [improvement-cycle-decision-timing.md](troubleshooting/improvement-cycle-decision-timing.md) |
| 변이는 exact 집합을 실행 전에 손으로 추적한다 | 변이의 기대 FAIL 집합은 "부분집합"이 아니라 가능하면 정확 집합(exact)으로 실행 **전에** 손 추적해 고정한다. 결과를 본 뒤 채점 기준을 그 결과에 맞춰 고치면(더 엄격한 방향이라도) 원칙 7 위반이다 | `06-improvement-plan.c2.md`(F-D8, H9), [work-items/20260925-rego-policy/testing.md](work-items/20260925-rego-policy/testing.md) |
