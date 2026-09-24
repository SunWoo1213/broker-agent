# 테스트 기록 — 0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동

> 근거: `.claude/runs/20260924-dev-env/01-plan.r3.md`(완료 조건), `03-build-notes.md`(구현 중 자기 점검), `05-test-report.md`(⑤ 실행). 숫자와 출력은 원문 그대로 옮겼다.

## 요약

| 회차 | 판정 | pytest (통과/실패/건너뜀) | opa test (PASS/FAIL) | flaky | 공격 평가 |
|---|---|---|---|---|---|
| 1 | APPROVE | 해당 없음 (수집 0개, exit 5 — 계획 취지대로) | PASS: 1/1 | 없음(신규 pytest 테스트 없음) | 해당 없음 |

이 작업에는 pytest 테스트를 추가하지 않는다(계획 100·106행: pytest 설정은 별도 "B" 항목 몫). 대신 완료 조건(AC1–AC13)을 명령 + 기대 출력으로 짜서 ③·⑤가 직접 실행해 확인했다.

## 테스트 설계

이번 작업에서 "테스트"로 삼은 것은 pytest 코드가 아니라 아래 명령 검사(T1–T10, 01-plan.r3.md "먼저 쓸 테스트")다.

| 테스트 | 종류 | 검증하는 것 | 완료 조건 | 관련 원칙 |
|---|---|---|---|---|
| T1 `opa_healthcheck_detects_unreachable` | 의존성 중단 | healthcheck 명령을 닫힌 포트(8199)로 바꿔 실행하면 종료 코드 ≠ 0 (가짜 성공 검사가 아님) | AC1 | 1 |
| T2 `opa_unhealthy_when_stopped` | 의존성 중단 | `docker compose stop opa` 뒤 상태가 healthy가 아니고, `start` 후 다시 healthy | AC2 | 1 |
| T3 `requirements_no_unpinned` | 단위(스크립트) | 두 requirements 파일에 `==` 없는 줄이 0개 | AC3 | 7 |
| T4 `requirements_pins_match_installed` | 단위(스크립트) | 고정 버전 = `.venv` 실제 설치 버전, `pip check` 무결 | AC4 | 7 |
| T5 `requirements_fresh_install` | 통합 | 저장소 밖 새 venv에서 고정 조합 설치가 처음부터 풀리지 않고 성공 | AC5 | 7 |
| T6 `compose_images_pinned` | 단위(스크립트) | `docker compose config --images`에 `latest`·메이저 전용 태그 없음 | AC6 | 7 |
| T7 `compose_three_healthy` | 통합 | `docker compose up -d --wait` 성공, 3종 healthy | AC8 | — |
| T8 `opa_default_deny_on_pinned_image` | 정책 | 고정 OPA에서 `opa test` PASS, 빈 입력 질의 결과가 deny | AC10 | 1 |
| T9 `imports_ok` | 단위(스크립트) | 고정 패키지 import 성공 | AC11 | — |
| T10 `host_ports_mapped` (r2 신설) | 통합 | 실제 호스트 매핑이 postgres 5434 · redis 6380 · opa 8181, 호스트 5434에서 postgres 응답 | AC13 | — |

## 회차 1 — APPROVE

### 환경

- 작업 트리: 저장소에 커밋 없음(`git log` → "does not have any commits yet"). `git status --porcelain`으로 변경 파일만 대조.
- 서비스 상태(⑤ 시작 시점): `docker compose ps` → `opa Up 17 minutes (healthy)`, `postgres Up 18 minutes (healthy)`, `redis Up 18 minutes (healthy)`(③ 완료 시점부터 이미 떠 있었음, `--wait`로 재확인만 함).
- 다른 프로젝트 컨테이너: `capstone2-postgres-1` → `Up 2 hours (healthy)`. `finance_postgres` → `Exited (0) 7분 전`(사용자가 직접 중지, 이번 작업과 무관으로 확인됨).
- 도구: Python 3.13.7(`.venv`), Docker Desktop `29.3.0`, Compose v5.1. OPA CLI 없음 — 컨테이너로만 실행.
- Git Bash에서 컨테이너 내부 절대경로(`/opa`, `/policies`) 인자에는 `MSYS_NO_PATHCONV=1` 사용(03과 동일 방식). 상세: [msys-pathconv-windows.md](../../troubleshooting/msys-pathconv-windows.md)

### 실행한 명령과 결과

```
$ python -m pytest -q
no tests ran in 0.04s   (종료 코드 5 — "해당 없음"으로 기록, 계획 106행 지시대로)
$ opa test policies -v   (실제로는 docker compose run --rm opa test /policies -v)
PASS: 1/1
```

### 불안정성 확인 (새 테스트 3회 반복)

해당 없음 — 이번 항목은 신규 pytest 테스트를 추가하지 않았다(표 없음). AC1·AC2(stop/start 절차)는 1회 실행에서 계획대로 재현됨(1회만 실행, 3회 반복 대상 아님).

### 의존성 중단 테스트

| 중단한 서비스 | 테스트 | 기대 | 결과 | 서비스 재기동 확인 |
|---|---|---|---|---|
| OPA healthcheck 대상 포트를 8199로 변경(설정만) | AC1 | 종료 코드 ≠ 0 | 종료 코드 1, 출력 `{}`. 포트 8181로 원상복구 실행 → 종료 코드 0, `value: true` | 해당 없음(원본 명령으로 재확인) |
| `docker compose stop opa` | AC2 | 상태가 healthy 아님, `start` 후 60초 내 healthy | `docker compose ps -a opa` → `Exited (0) Less than a second ago`. `start` 후 5초 만에 `Up 5 seconds (healthy)` | 확인(재기동 성공) |

### 완료 조건 대조

| AC | 내용 | 확인한 테스트 | 결과 |
|---|---|---|---|
| AC1 | healthcheck가 실패를 잡는다 | T1 | PASS — 8199 → 종료 1 / `{}`, 8181 → 종료 0 / `true` |
| AC2 | OPA 중단이 상태에 드러난다 | T2 | PASS — stop 후 `Exited`, start 후 5초 만에 healthy |
| AC3 | 미고정 패키지 0개 | T3 | PASS — `[]`, 종료 코드 0 |
| AC4 | 고정 = 설치 버전, `pip check` 무결 | T4 | PASS — 13개 `mismatches: []`, `No broken requirements found.` |
| AC5 | 새 환경 설치 성공 | T5 | PASS — `$TEMP\broker-venv-check-05`에서 설치·`pip check` 성공. **삭제는 시도하지 않음**(사용자 정책 결정, 경로만 기록). 상세: [delete-ask-repeated-prompt.md](../../troubleshooting/delete-ask-repeated-prompt.md) |
| AC6 | 이미지 태그 고정 | T6 | PASS — `redis:7.4.11-alpine`, `openpolicyagent/opa:1.20.2`, `postgres:16.15` 정확히 3줄 |
| AC7 | 태그 = 실행 중 버전 | — | PASS — postgres `16.15`, redis `v=7.4.11`, opa `Version: 1.20.2` 모두 태그와 일치 |
| AC8 | 3종 healthy | T7 | PASS — `up -d --wait` 종료 0, 세 서비스 모두 `(healthy)` |
| AC9 | 서비스 응답 | — | PASS — `pg_isready` → `accepting connections`, `redis-cli ping` → `PONG` |
| AC10 | 고정 OPA에서 정책 테스트·기본 거부 | T8 | PASS — `opa test` → `PASS: 1/1`. 빈 input → `{'result': {'reason': 'no_matching_rule', 'result': 'deny'}}` |
| AC11 | import | T9 | PASS — 13개 패키지 import `ok`, `python --version` → `3.13.7` |
| AC12 | 범위 준수 | — | PASS(부분 대체) — 해시 4개 일치, `.venv` ignore 확인, 볼륨 유지, `capstone2-postgres-1` Up 유지. `finance_postgres`는 "사용자가 직접 중지 — 작업과 무관"으로 기록, 실패로 치지 않음. `.env.example` 하위 항목은 실행하지 않고 "사용자 확인(20:57 직접 수정)으로 갈음" |
| AC13 | 호스트 포트 매핑 | T10 | PASS — 텍스트 검사(`:-5434` 1건, `:-5433` 0건), 실제 매핑(5434·6380·8181), SSLRequest 응답 `b'N'` 모두 통과 |

### 실패 상세

없음 — AC1–AC13 전부 PASS. (④ BLOCK은 이 회차 이전 관문에서 발생했고, 사람 확인으로 해제된 뒤 이 회차가 시작됐다. 상세: [verification.md](verification.md) ④ 절, [subagent-permission-bypass.md](../../troubleshooting/subagent-permission-bypass.md))

## 정리 필요 사항 (기록용, 실패 아님)

- `C:\Users\swsj1\AppData\Local\Temp\broker-venv-check-05` — AC5 확인용 임시 venv. 오케스트레이터 지시로 삭제하지 않음. 정리는 사용자가 직접 한다.
- compose 3종(`opa`, `postgres`, `redis`)은 healthy 상태로 계속 실행 중(사용자 검토 편의, `down`/`down -v` 실행하지 않음).
