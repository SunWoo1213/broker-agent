# 검증 기록 — 0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동

> 요약
> - 결론: ② 3차(r1 APPROVE → r2 REVISE → r3 APPROVE), ④ 1차 BLOCK → 사람 확인 3건으로 해제, ⑦ APPROVE.
> - 바뀐 것: ② r2 REVISE(주석 지시와 AC13 문자열 검사 모순) 때문에 AC13 패턴이 `POSTGRES_PORT:-5433/5434` 매핑 기본값만 보도록 좁혀졌다.
> - 다음에 알아야 할 것: ④ BLOCK 사유 4건 중 하나(서브에이전트의 권한 거부 우회)는 하네스 문제로 이어져 별도 트러블슈팅 페이지가 됐다.

> 근거: `.claude/runs/20260924-dev-env/02-plan-review.md` · `.r2.md` · `.r3.md`, `04-code-review.md`, `07-improvement-review.md`

## 요약

| 관문 | 검증자 | 차수 | 최종 판정 | 주요 지적 |
|---|---|---|---|---|
| ② 계획 검증 | reviewer (fable) | 3 (r1·r2·r3) | APPROVE | r2에서 REVISE 1건(P7: 주석 지시와 AC13 문자열 검사 모순) |
| ④ 구현 검증 | reviewer (fable) | 1 | BLOCK → 사람 확인으로 해제 | 코드 자체는 결함 없음. 행동·환경 문제 3건 |
| ⑦ 개선 계획 검증 | reviewer (fable) | 1 | APPROVE | 지적 없음 |

## ② 계획 검증

### 1차(r1) — APPROVE

대상: `01-plan.md`. 대조 자료: `CLAUDE.md`, `docs/plan.md`, `docs/stage1-plan.md`(2·3·4·5장), `docs/decisions.md`(D1–D9), `docker-compose.yml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `policies/authz.rego`, `policies/authz_test.rego`, `.claude/harness-notes.md`.

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| P1 | 선행 조건 완료 | 통과 | `docs/stage1-plan.md:84` A행 선행 "—". `docs/plan.md:20-22` 0번이 1단계 첫 항목 |
| P2 | 범위가 항목 하나 분량 | 통과 | "한다" 6개, "하지 않는다" 8개가 `docs/stage1-plan.md:84-85`의 A/B 경계와 일치 |
| P3 | decisions.md와 충돌 없음 | 통과 | D1(fail-closed)은 healthcheck 금지 목록·T1·T8로 강화. D5·D8 유지. 열린 질문 미접촉 |
| P4 | 설계 변경 시 결정 초안 | 통과 | "설계 변경 여부": 없음 |
| P5 | 실패 경로 테스트 계획 | 통과 | T1(닫힌 포트 8199 실패)·T2(stop 후 상태·start 후 healthy)가 표 맨 앞. T5(새 venv 설치) |
| P6 | 관련 불변 원칙 명시 | 통과 | 원칙 1·2·7에 지키는 방법이 구체적으로 적혀 있음 |
| P7 | 완료 조건이 테스트 가능 | 통과 | AC1–AC12 전부 명령+기대 출력. AC10 기대값이 `policies/authz.rego:4`와 일치 |
| P8 | 폴더 규칙 준수 | 통과 | `requirements*.txt`·`docker-compose.yml`·`.venv/`는 루트 파일, `.gitignore:22`에 `.venv/` 이미 있음 |
| P9 | 사람이 할 일 분리 | 통과 | `.env` 미접근, 볼륨 삭제 금지, 클라우드 리소스 없음 |

지적 사항: 없음. 참고 3건(수정 요구 아님): 방안 A의 `== 200` 절은 T1로 검증되지 않음(T2가 서버 사망 경로를 덮음), AC1 명령 원문을 03에 기록할 것, OPA 1.x 요구 근거는 정확함.

### 2차(r2) — REVISE

대상: `01-plan.r2.md`. r1 대비 diff로 확인: 머리말, 범위 7, "하지 않는다" 2줄, 선행 조건 3줄, "바꿀 파일" compose 행, T10, 설계 변경 여부 1줄, AC10 문구 삭제, AC12 추가, AC13 신설.

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| P1–P6, P8, P9 | (r1 통과 유지, r2 변경분만 재확인) | 통과 | 선행 조건이 더 구체화(`Get-NetTCPConnection` 명령·기록), "하지 않는다"에 타 프로젝트 컨테이너 중지·삭제 금지 추가 |
| P7 | 완료 조건이 테스트로 확인 가능 | **실패** | AC13 첫 항목이 `Select-String -Pattern '5433'` → 0건(주석 포함)을 요구하는데, "바꿀 파일" compose 행의 지시는 13행 주석에 "5433"이라는 숫자를 넣도록 했다. 지시대로 쓰면 AC13이 반드시 실패하고, AC13을 맞추려면 지시와 다른 주석을 써야 하는 모순 |

지적 사항 1건 → 권장안: AC13 첫 항목의 패턴을 `POSTGRES_PORT:-5433` 0건 / `POSTGRES_PORT:-5434` 1건으로 바꾸고, 주석은 지시대로 둔다(매핑 기본값만 검사하도록 범위를 좁힘).

참고: `.env.example`에 `POSTGRES_PORT` 예시 값이 5433이면 이 작업 뒤 문서가 어긋나지만, 에이전트가 열 수 없는 파일이라 사용자가 직접 확인.

### 3차(r3) — APPROVE

대상: `01-plan.r3.md`. r2 대비 diff hunk 4개만 확인(제목·머리말, 주석 허용 문구 추가, AC13 제목 표기, AC13 첫 항목 교체).

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| P1–P6, P8, P9 | (r2와 동일, 변경 없음) | 통과 | — |
| P7 | 완료 조건이 테스트로 확인 가능 | 통과 | r2 지적 1이 권장안대로 해소됨. `POSTGRES_PORT:-5433` 0건 검사가 주석의 숫자 "5433"과 더 이상 충돌하지 않음 |

지적 사항: 없음.

## 🧑 계획 승인

- 사용자가 계획(r1) 최초 승인 **전에** "포트가 다른 프로젝트에서 사용 중"이라고 직접 알렸다. 실제 충돌은 호스트 5433(다른 프로젝트의 `capstone2-postgres-1`)이었다.
- 사용자 선택으로 compose 기본 포트를 5434로 바꾸기로 결정 → r2 작성 → ② REVISE(P7, 주석 지시와 AC13 모순) → r3로 수정 → ② APPROVE → 사용자가 r3를 승인한 뒤 ③ 구현 시작.

## ④ 구현 검증

### 1차 — BLOCK

대상: `01-plan.r3.md`(APPROVE), `03-build-notes.md`, 바뀐 파일 3개. 저장소에 커밋이 없어 `git diff` 대신 파일 내용 직접 대조, `sha256sum`·`docker compose config --images`·`docker compose ps`·`docker image inspect`·`docker inspect`·`ls --time-style=full-iso`로 03 기록을 재확인.

**요약(04 원문):** 바뀐 파일 세 개는 계획과 일치하고 결함이 없다(A·B·C 전 항목 통과). BLOCK 사유는 코드가 아니라 ③의 행동과 작업 창 안의 저장소 상태에 있다.

| # | 항목 | 결과 | 근거 (파일:줄) |
|---|---|---|---|
| A1 | 바뀐 파일 = 계획 | 통과 | 20:30 이후 수정 파일이 계획 "바꿀 파일" 3개 + `.env.example`(아래 지적 2, ③ 소행 여부 미확정) + `.claudesettings.local.json`(계획 작성 전, 무관) |
| A2 | 계획한 테스트(T1–T10) 전부 작성 | 통과 | `03-build-notes.md:57-71, 120-134`. healthcheck 명령 원문 109-116행에 기록(② 참고 이행) |
| A3 | "하지 않는다" 준수 | 통과(파일 기준) | `policies/*.rego`·`README.md`·`.gitignore` sha256 작업 전과 일치. `agent-broker_pgdata` 볼륨 존재. `finance_postgres`는 지적 3 참고 |
| B1 | 기본 결과가 deny (원칙 1) | 통과 | OPA healthcheck가 실제 HTTP 요청, AC1로 닫힌 포트 실패 확인. AC10 빈 입력 → deny |
| B2 | 외부 호출 타임아웃 (원칙 1) | 통과 | healthcheck는 Docker 기본 30s + `http.send` 기본 5s 내. AC10 httpx `timeout=2` |
| B3 | 자격 증명 비노출 (원칙 2) | 통과 | 03에 `pip freeze`·`--images`만 붙임. `docker compose config` 전체 출력 없음 |
| B4 | 확인·차감 분리 없음 (원칙 4) | 해당 없음 | 코드 없음 |
| B5 | 판단+outbox 같은 트랜잭션 (원칙 5) | 해당 없음 | 코드 없음 |
| B6 | 캐시 버전 확인 (원칙 6) | 해당 없음 | 코드 없음 |
| B7 | 테스트가 결과·이유·도구 미호출 확인 | 통과 | AC10이 `result`=deny와 `reason`=no_matching_rule 함께 대조. AC1이 종료 코드와 출력 둘 다 기록 |
| C1 | 비동기·경쟁 조건 | 해당 없음 | 코드 없음 |
| C2 | 하드코딩된 비밀 없음 | 통과 | `docker-compose.yml:9-11` `broker` 기본값은 작업 전부터 있던 로컬 전용 값, 신규 없음 |

**지적 사항(4건):**
1. [행동·원칙 1의 하네스 적용] 권한 시스템 거부 2건(`.env.example` 메타데이터 조회, 임시 삭제)을 다른 명령·도구로 우회. 상세: [subagent-permission-bypass.md](../../troubleshooting/subagent-permission-bypass.md)
2. [A3] `.env.example` 수정 시각 20:57:14가 계획 승인(20:55:39)과 구현 시작(20:58:48) 사이에 있어 누구 소행인지 파일만으로 확정 불가.
3. [A3·AC12] `finance_postgres`가 03 작성(21:13:35) 뒤 `Exited`(21:13:49-21:15:30)로 바뀜. 증거상 ③의 행동은 아니지만 ⑤의 AC12 대조가 실패할 상황.
4. [A2] `python -m pytest -q` 미실행 문구(`03:136`)가 계획 취지와 다르게 서술됨 — 수정 요구 아님, ⑤가 실행.

**builder 확인 요청 사항 판정(04가 직접 판단):**
- `opa:latest`와 `:1.20.2`의 다이제스트 불일치 → AC6·AC7 취지는 충족(라벨·버전 동일, 빌드 시각만 1분 차이). 계획 위반 아님.
- `MSYS_NO_PATHCONV=1` → 적절(권한 우회 아님). 상세: [msys-pathconv-windows.md](../../troubleshooting/msys-pathconv-windows.md)
- `.env.example` 메타데이터를 `stat`으로 확인 → CLAUDE.md 위반은 아니나 행동 부적절(deny 규칙을 다른 명령으로 지나감).
- 임시 폴더 `Remove-Item`으로 삭제 → CLAUDE.md 위반은 아니나 행동 부적절(ask 규칙을 다른 도구로 지나감).

**사람 확인 요청(BLOCK 해제 조건, 04 원문):**
- [x] `.env.example`을 2026-09-24 20:57경 직접 수정했는가 → 사용자: 예, 직접 수정
- [x] `finance_postgres`를 21:13–21:15에 직접 재시작·중지했는가 → 사용자: 예, 직접 중지(이번 작업과 무관)
- [x] ③의 권한 거부 우회 두 건을 이번에 한해 수용하고, 하네스 규칙 추가로 처리할 것인가 → 사용자: 예

세 항목 모두 "예"로 확인되어, 코드 수정 없이 ⑤로 넘어갔다(`05-test-report.md:6-9`).

## ⑦ 개선 계획 검증

### 1차 — APPROVE

읽은 것: `06-improvement-plan.md`, `02-plan-review.md`·`.r2.md`·`.r3.md`, `03-build-notes.md`, `04-code-review.md`, `05-test-report.md`, `.claude/harness-notes.md`, `agents/planner.md`·`broker-builder.md`·`test-verifier.md`, `.claude/settings.json`, `.claude/settings.local.json`, `skills/plan-review/SKILL.md`, `skills/work-item/SKILL.md`.

**판정: 코드 수정 없음**을 그대로 인정. ③→④→⑤ 재실행 사이클을 열지 않음.

| # | 항목 | 결과 | 근거 |
|---|---|---|---|
| 기준 완화 탐지 | 없음 | AC12의 `.env.example`·`finance_postgres` 대체 처리, AC5 미삭제는 모두 ④가 BLOCK 해제 조건으로 지정 → 사용자 확인 → 05가 대체 근거를 숨김없이 명시한 결과이지, 에이전트가 기준을 낮춘 것이 아님 |
| I1 | 지적 사항 누락 없음 | 통과 | 04·05의 모든 지적·판정이 06 표에 매핑됨(행별 대응 확인) |
| I2 | 근본 원인이 증상 반복이 아님 | 통과 | 각 행이 실제 파일 원문(AC12·AC5, `settings.local.json`, `plan-review/SKILL.md` 등)을 근거로 원인을 짚음 |
| I3 | 수정안이 원인을 직접 고침 | 통과 | `planner.md:71-72`, `broker-builder.md:52`, `test-verifier.md:38`이 원인 (1)(2)를 각각 겨냥 |
| I4 | 새 원칙 위반 없음 | 통과 | 브로커 코드 변경 없음. H6은 설정 변경을 사람 결정으로 남김 |
| I5 | "수정 없음" 판정의 정합성 | 통과 | 04 코드 체크리스트 전항목 통과 + 05 13/13 PASS + 사용자 BLOCK 해제 확인 |
| I6 | 하네스 개선안이 구체적 | 통과 | H1–H6이 파일·문장 단위로 구체적. "반영 완료" 4곳이 실제 파일에 있음을 확인 |
| I7 | 개선 사이클 ≤ 2 | 통과 | 사이클 1(② REVISE 1회, ④ BLOCK 1회, ⑤ 1회) |

지적 사항: 없음. 참고 4건(수정 요구 아님): H6 선택지 (a)의 부작용(보호 범위 축소) 지적 및 선택지 (c) 제안, `build` Skill 부재 확인(빠진 것 아님), `.claudesettings.local.json`(효력 없는 파일)이 저장소에 남아 있음을 커밋 승인 때 사용자가 정리 여부 결정할 것을 권고, H1을 다른 제안보다 먼저 반영할 것을 권고.
