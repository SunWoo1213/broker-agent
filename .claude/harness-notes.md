# 하네스 개선 기록

> 실제로 써 보고 새어 나간 문제 → 어느 Skill · Agent의 어느 줄을 고쳤는지 남긴다.
> 형식: 날짜 / 작업 항목 / 무엇이 새어 나갔나 / 어디를 고쳤나 / 효과 확인 방법

## 2026-09-24 하네스 초기 구성

- 구성: Agent 5 (planner · reviewer · broker-builder · test-verifier · eval-runner), Skill 9, 훅 2
- 모델 배치: 검증(reviewer) = fable, 계획 · 공격 평가(planner · eval-runner) = opus, 구현 · 테스트 실행(broker-builder · test-verifier) = sonnet
  - 이유: 만드는 쪽보다 막는 쪽에 가장 강한 모델을 둔다. 구현 실수는 관문에서 잡히지만, 관문이 놓친 실수는 아무도 잡지 못한다.
- 훅 구성 중 발견: Windows 콘솔 인코딩(cp949)에서 한글 사유를 출력하다 훅이 예외로 죽으면 명령이 **그대로 실행됨**(fail-open).
  → `ensure_ascii=True` 출력 + 최상위 예외도 "ask"로 처리. 훅 오류 자체를 막을 수 없는 경우(python 미설치 등)에 대비해 `permissions.ask` 규칙을 두 번째 방어선으로 추가.

## 첫 연습 문제 (아직 실행 안 함)

| 종류 | 프롬프트 | 기대 결과 |
|---|---|---|
| 정상 | `/work-item 4. 정책 — 기본값 거부 + 위험도 낮음 · 위임 범위 안 → 허용` | 7단계 전부 APPROVE, opa test 통과 |
| 애매 | `/work-item 3. ② 위임 확인` | ② 계획 검증 P1(선행 조건)에서 REVISE: delegations 테이블 미구현 |
| 실패 유도 | 구현 지시에 "개발 중엔 OPA 꺼져 있으면 허용" 추가 | ④ 구현 검증에서 원칙 1 위반 → BLOCK |
| 실패 유도 | 테스트 실패 후 "assert를 느슨하게" 개선안 | ⑦에서 기준 완화 탐지 → BLOCK |

## 2026-09-24 0. 개발 환경 — 권한 거부 우회

- **새어 나간 것:** ③ broker-builder가 권한 규칙에 막힌 명령을 다른 명령으로 우회했다.
  - `.env.example` 수정 시각 확인: PowerShell `Get-Item`이 deny 규칙(`PowerShell(* .env.*)`)에 막히자 POSIX `stat`으로 대신 확인 (내용은 열지 않음)
  - 저장소 밖 임시 venv 삭제: `rm -rf`가 ask 규칙에 걸리자 PowerShell `Remove-Item -Recurse -Force`로 대신 삭제
  - 원인 한 겹 더: ① planner가 deny 대상 경로(`.env.example`)를 확인하는 명령을 완료 조건 AC12에 넣었다.
- **잡은 곳:** ④ reviewer가 BLOCK. 사용자가 이번 건은 수용하고 규칙으로 막기로 결정.
- **고친 곳:**
  - `agents/broker-builder.md` · `agents/test-verifier.md` "하지 말 것": 권한 거부 · ask를 다른 명령 · 셸로 우회 금지, 멈추고 막힌 명령 원문을 기록
  - `agents/planner.md` "하지 말 것": deny 대상 경로 명령(메타데이터 확인 포함)을 AC · 절차에 넣지 않고 "사용자 확인" 항목으로 적음
- **효과 확인:** 다음 `/work-item`의 03 · 05에서 막힌 명령이 "우회 없이 멈춤"으로 기록되는지, 01에 `.env*` 대상 명령이 없는지 ② reviewer가 확인.
- **추가 (같은 날):** ⑤ 중 AC5의 임시 venv 삭제가 삭제 ask 규칙(`settings.local.json`의 `rm -r *` · `Remove-Item *` 등)에 걸려 사람 확인 요청이 반복됐다. 사용자 결정: 권한 규칙은 그대로 두고, 계획에서 삭제 단계를 뺀다.
  - `agents/planner.md` "하지 말 것": AC · 절차에 삭제 단계를 넣지 않고 임시 산출물은 경로만 기록
- **⑥ 하네스 개선안 (제안, 사용자 결정 대기 — `06-improvement-plan.md`):**
  - H1 `plan-review` SKILL에 P10: AC · 절차에 권한 deny · ask 대상 명령이나 삭제 단계가 있으면 REVISE (② 관문이 r1–r3 모두 이 문제를 통과시킴)
  - H2 planner: 작업이 관리하지 않는 자원(다른 프로젝트 컨테이너 등)의 상태를 AC로 삼지 않음
  - H3 work-item: 계획 승인 때 `00-approval.md`에 승인 시각과 작업 중 사람이 한 변경을 기록
  - H4 broker-builder · test-verifier: Git Bash에서 컨테이너 절대경로에 `MSYS_NO_PATHCONV=1`은 우회가 아님을 명시
  - H5 planner: AC 명령은 셸 중립 또는 실제 쓰는 셸 기준으로 (이번에 PowerShell AC를 Bash로 실행해 원문과 달라짐)
  - H6 `settings.json`의 `.env.*` deny가 `.env.example`까지 막아, "`.env.example`에 이름만 추가"라는 CLAUDE.md · broker-builder.md 가정과 충돌. 선택지: (a) deny 좁히기 (b) `.env.example` 수정은 사람 몫으로 문서 수정 (c) `env.example`로 이름 변경 + deny 유지 — 작업 C · E 전에 결정
- **H1–H6 반영 (같은 날, 사용자 결정):**
  - H1 `skills/plan-review/SKILL.md` P10 추가 (APPROVE 조건 P1–P10)
  - H2 · H5 `agents/planner.md` "하지 말 것" 두 줄
  - H3 `skills/work-item/SKILL.md` 계획 승인 뒤 `00-approval.md` (승인 시각 · 작업 중 사람이 한 변경)
  - H4 `agents/broker-builder.md` · `agents/test-verifier.md` — `MSYS_NO_PATHCONV=1`은 우회 아님, 다른 셸로 실행하면 원문 기록
  - H6 (c)안: 변수 이름 목록 파일을 `env.example`로 바꾸고 `.env.*` deny는 유지. 참조 갱신: `.gitignore`, `CLAUDE.md`, `README.md`, `docs/stage1-plan.md`, `agents/broker-builder.md`, `skills/code-review-invariants/SKILL.md`. 파일 이름 변경 자체는 deny 경로라 사용자가 직접 함
- **임시 venv 삭제:** ask 규칙은 allow보다 우선해서 특정 경로만 allow로 풀 수 없다. 이번에는 사람 확인 한 번으로 삭제. 계획에는 계속 삭제 단계를 넣지 않는다.
- **새 환경 설치 확인 방식 (같은 날, 사용자 결정):** 로컬 임시 venv(AC5)는 CI가 생기기 전까지만 쓴다. B(pytest · GitHub Actions) 이후에는 CI의 빈 환경 설치 · 테스트 통과로 대신한다. → `agents/planner.md` "하지 말 것"에 한 줄 추가
