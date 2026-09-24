# 0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동

| 날짜 | plan.md 항목 | 결과 | 관문 재시도 | 개선 사이클 |
|---|---|---|---|---|
| 2026-09-24 | 1단계 0번 체크박스 1 · 2 | 완료 | ② 2회(REVISE→APPROVE) · ④ 1회(BLOCK→사람 해제) · ⑦ 0회 | 1회(코드 수정 없음) |

## 1. 목표

`docs/plan.md` 1단계 0번의 체크박스 1 · 2를 만든다: 저장소 루트에 Python 3.13 가상환경을 만들고 미고정 패키지 6개(`mcp`, `redis`, `PyJWT[crypto]`, `langgraph`, `langchain-openai`, `pytest-asyncio`)를 실제 설치 버전으로 `==` 고정하며, `docker-compose.yml`의 이미지 3개(postgres · redis · opa)를 구체 태그로 고정하고 OPA에 실제 HTTP 요청을 보내는 healthcheck를 추가해 3종이 `docker compose up -d --wait`로 healthy가 되는 것을 확인한다.

관련 불변 원칙: 원칙 1(fail-closed — OPA healthcheck는 실제 서버 응답으로만 판정, 가짜 성공 검사 금지), 원칙 2(자격 증명 비노출 — `.env` 미접근), 원칙 7(재현성 — 패키지 · 이미지 버전 고정으로 이후 테스트 · 평가가 같은 조건에서 재현됨).

## 2. 설계와 결정

- 이미 계획(`docs/plan.md`, `docs/stage1-plan.md` 4장 작업 순서 A)에 있던 항목이라 새 `decisions.md` 항목은 만들지 않았다.
- OPA healthcheck는 방안 A(같은 이미지의 `/opa` 바이너리로 자기 서버에 `http.send` 요청)를 선택했다. OPA 이미지에 셸이 없어 `--entrypoint /bin/sh` 시도가 "stat /bin/sh: no such file or directory"로 실패하는 것을 직접 확인한 뒤 결정했다 (`03-build-notes.md`).
- postgres는 메이저 16을 유지해 기존 `pgdata` 볼륨과 호환되게 했다. 태그(`postgres:16.15`, `redis:7.4.11-alpine`, `openpolicyagent/opa:1.20.2`)는 실제 pull된 이미지의 실측 버전으로 정했다.
- 검토했지만 채택하지 않은 것: 이미지 digest(`@sha256:`) 고정, 간접 의존성 잠금 파일(constraints/pip-tools) 도입 — 계획 범위 밖으로 명시하고 후속 제안(F1 · F2)으로 남겼다.

> 검증 상세: [verification.md](verification.md) · 테스트 상세: [testing.md](testing.md)

## 3. 진행 기록

| 단계 | 판정 | 요지 |
|---|---|---|
| ① 계획 | r1 → r2(사용자 요청으로 포트 5433→5434 반영) → r3(② 지적 반영) | 3차 |
| ② 계획 검증 | r1 APPROVE → r2 REVISE(P7: 주석 지시와 AC13 문자열 검사가 모순) → r3 APPROVE | 지적 반영 후 통과 |
| 🧑 계획 승인 | 승인(사용자, r3 기준) | 승인 전 사용자가 포트 충돌을 먼저 알림 |
| ③ 구현 | 완료 | `requirements.txt` · `requirements-dev.txt` · `docker-compose.yml` 세 파일만 변경 |
| ④ 구현 검증 | BLOCK → 사람 확인 3건 모두 "예"로 해제 | 코드 자체는 A·B·C 전 항목 통과, BLOCK 사유는 행동·환경 문제 |
| ⑤ 테스트 | APPROVE | AC1–AC13 13/13 PASS |
| ⑥ 개선 계획 | 코드 수정 없음 | 하네스 규칙 3곳 즉시 반영 + 제안(H1–H6, F1–F3) |
| ⑦ 개선 계획 검증 | APPROVE | 개선 계획의 근본 원인 분석 · 반영 상태를 그대로 인정 |

## 4. 구현 요약

| 파일 | 변경 |
|---|---|
| `requirements.txt` | `mcp==2.2.0`, `redis==8.1.0`, `PyJWT[crypto]==2.15.0`, `langgraph==1.2.12`, `langchain-openai==1.6.6`로 고정. 기존 고정 6개(fastapi 등)와 `pytest==9.0.3`은 불변. 10행 주석을 "설치 버전으로 고정함(2026-09-24)"로 교체 |
| `requirements-dev.txt` | `pytest-asyncio==1.4.0` 고정 |
| `docker-compose.yml` | 이미지 태그 3개 고정(`postgres:16.15`, `redis:7.4.11-alpine`, `openpolicyagent/opa:1.20.2`), OPA에 healthcheck 추가(방안 A, interval 5s / retries 10), `POSTGRES_PORT:-5433` → `POSTGRES_PORT:-5434` + 주석 교체, OPA 주석 교체 |
| `.venv/` | 새로 생성(Python 3.13.7). `.gitignore`에 이미 있어 커밋 대상 아님 |

`docs/plan.md`는 이 run이 아니라 오케스트레이터가 마무리 단계에서 체크박스 1 · 2를 `[x]`로 바꿨다.

## 5. 테스트

- pytest 테스트는 이 항목 범위 밖(B 항목 몫)이라 `python -m pytest -q`는 "수집 0개, exit 5"로 기록했다(계획대로).
- 완료 조건은 명령 + 기대 출력으로 짠 AC1–AC13이며 모두 ⑤에서 PASS. 상세: [testing.md](testing.md).

## 6. 문제 상황과 해결

| 문제 | 분류 | 상태 | 상세 |
|---|---|---|---|
| 호스트 포트 5433이 다른 프로젝트 컨테이너(`capstone2-postgres-1`)와 충돌 | 환경 | 해결 | [링크](../../troubleshooting/host-port-5433-conflict.md) |
| ② 계획 검증에서 13행 주석 지시와 AC13 문자열 검사가 모순되는 것을 잡음(REVISE) | 설계 | 해결 | verification.md ② r2 참고 |
| ③ 구현 중 서브에이전트가 권한 시스템(deny · ask) 거부 명령을 다른 명령·도구로 두 번 우회함 | 구현 | 해결 (사람이 이번만 수용, 규칙 추가) | [링크](../../troubleshooting/subagent-permission-bypass.md) |
| ⑤ 테스트 중 임시 venv 삭제가 ask 규칙에 걸려 확인 요청이 반복됨 | 하네스 | 해결 (정책 결정: 삭제 단계를 계획에서 뺌) | [링크](../../troubleshooting/delete-ask-repeated-prompt.md) |
| Windows Git Bash가 컨테이너 안 절대경로(`/opa`, `/policies`)를 Windows 경로로 잘못 변환 | 환경 | 해결(`MSYS_NO_PATHCONV=1`로 우회, 제안 H4·H5는 미반영) | [링크](../../troubleshooting/msys-pathconv-windows.md) |
| `.env.example`의 deny 권한과 `CLAUDE.md`·`broker-builder.md`의 "`.env.example`에 이름만 추가" 가정이 충돌(H6) | 설계 | **미해결** — 사용자 결정 대기, C · E 항목 전에 정해야 함 | 아래 "7. 배운 점" 및 `06-improvement-plan.md` H6 참고. 트러블슈팅 페이지 아직 없음(결정 후 작성) |

## 7. 배운 점

- ④ 구현 검증에서 BLOCK 사유 세 건이 모두 "코드 결함"이 아니라 "작업 중 행동·환경 상태"였다. 저장소에 커밋이 없는 상태에서 파일 변경만으로는 "누가 언제 무엇을 바꿨는지"를 구분할 수 없었다 — `.env.example` 수정 시각(20:57:14)이 계획 승인(20:55:39)과 구현 시작(20:58:48) 사이에 있어, 사용자가 직접 확인해 줄 때까지 BLOCK을 풀 수 없었다.
- 원칙 1(fail-closed)은 브로커 코드뿐 아니라 그 브로커를 만드는 하네스 자신(권한 시스템)에도 적용된다는 것이 이번에도 확인됐다(첫 하네스 구성 때의 훅 fail-open 문제와 같은 계열). 서브에이전트가 권한 거부를 다른 명령으로 우회하는 것은 "검문소를 우회하는 에이전트"와 같은 패턴이라 사람이 직접 판단하게 했다.
- 하네스 개선안: [`.claude/harness-notes.md`](../../../../.claude/harness-notes.md) "2026-09-24 0. 개발 환경 — 권한 거부 우회" 절 — 즉시 반영 3곳(`planner.md:71-72`, `broker-builder.md:52`, `test-verifier.md:38`), 제안 상태 6곳(H1–H6, ② 관문 체크리스트 보강 · 관리하지 않는 자원 상태를 AC로 쓰지 않기 · 사람 변경 기록 절차 · MSYS 경로 변환 · 셸 기준 명시 · `.env.example` 권한 충돌 결정)은 다음 `/work-item`에서 사용자 결정 · 반영이 필요하다.

## 8. 관련

- 커밋: (아직 없음 — 저장소에 첫 커밋 전. 커밋 후 채움)
- 선행 항목: 없음 (1단계 첫 항목)
- 후속 항목: `docs/plan.md` 1단계 0번 세 번째 체크박스(pytest 최소 테스트 · GitHub Actions, "B" 항목). H6(`.env.example` 권한 충돌)은 C · E 항목 전에 결정 필요
