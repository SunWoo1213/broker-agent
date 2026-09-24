# 호스트 PostgreSQL 포트가 다른 프로젝트 컨테이너와 충돌함 (5433)

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 환경 | 해결 | 사용자가 계획 승인 전 직접 알림 | 원칙 7 (재현성 — 환경 충돌 없이 기동 가능해야 함) |

## 증상

`docker-compose.yml`의 PostgreSQL 호스트 포트 기본값이 `5433`이었는데, 사용자가 "포트가 다른 프로젝트에서 사용 중"이라고 계획 승인 전에 알렸다. 실제로 5433은 다른 프로젝트의 `capstone2-postgres-1` 컨테이너가 쓰고 있었고, 5432는 `finance_postgres`가 쓰고 있었다.

## 재현 방법

1. 이 저장소의 `docker-compose.yml` 기본 포트(`POSTGRES_PORT:-5433`)로 `docker compose up`을 시도
2. 같은 호스트에 `capstone2-postgres-1`(5433), `finance_postgres`(5432)가 이미 떠 있으면 포트 바인딩이 충돌

## 원인

1. 직접 원인: 로컬 개발 환경에 이 저장소 외에 PostgreSQL을 쓰는 프로젝트 컨테이너 두 개가 이미 5432 · 5433을 점유하고 있었다.
2. 왜? → `docker-compose.yml` 작성 시 기본 포트를 PostgreSQL 표준(5432)에서 한 칸 옮긴 5433으로만 잡았고, 로컬 머신에 떠 있는 다른 프로젝트와의 충돌 가능성을 확인하지 않았다.
3. 근본 원인: 포트 기본값을 정할 때 "이 저장소만" 기준으로 정했고, 개발자의 로컬 환경(여러 프로젝트가 동시에 떠 있을 수 있음)을 계획에 반영하지 않았다.

## 해결

- 사용자 결정으로 호스트 포트 기본값을 `5433` → `5434`로 변경.
- `docker-compose.yml:13` `"${POSTGRES_PORT:-5433}:5432"` → `"${POSTGRES_PORT:-5434}:5432"`, 같은 줄 주석을 "5432 · 5433은 다른 프로젝트가 쓰므로 5434" 취지로 교체.
- 계획(`01-plan.r2.md`)의 "하지 않는다"에 "다른 프로젝트 컨테이너(`capstone2-postgres-1`, `finance_postgres` 등) 중지 · 삭제"를 명시해, 충돌을 포트 이동으로만 풀고 다른 컨테이너를 건드리지 않도록 범위를 제한했다.
- 완료 조건 AC13을 신설해 (1) 파일 텍스트에 `POSTGRES_PORT:-5434`가 1건이고 `POSTGRES_PORT:-5433`이 0건, (2) `docker compose port`로 확인한 실제 매핑이 postgres 5434 · redis 6380 · opa 8181, (3) 호스트 5434에 SSLRequest 바이트를 보내 PostgreSQL 응답(`b'N'`/`b'S'`)을 받는지 세 겹으로 검증하게 했다.

## 검증

- `03-build-notes.md`: `grep -c 'POSTGRES_PORT:-5434' docker-compose.yml` → `1`, `grep -c 'POSTGRES_PORT:-5433'` → `0`. `docker compose port postgres 5432` → `0.0.0.0:5434`. SSLRequest 응답 `b'N'`.
- `05-test-report.md` AC13: 같은 세 검사 모두 PASS.
- `04-code-review.md` A3, AC12: `docker ps --filter name=capstone2-postgres-1` → `Up`, `--filter name=finance_postgres`도 작업 시작 시점에는 `Up` — 다른 컨테이너를 건드리지 않았음을 확인 (이후 `finance_postgres`가 `Exited`가 된 것은 사용자가 직접 중지한 별개의 사건, 아래 관련 문서 참고).

## 재발 방지

- 계획 단계에서 "다른 프로젝트 컨테이너를 멈추거나 지우지 않는다"를 선행 조건 · 범위 양쪽에 명시하는 패턴을 유지한다.
- 포트 같은 로컬 환경 값은 계획에 기본값만 적지 말고, 실행 전제(③ 시작 시 `Get-NetTCPConnection`으로 LISTEN 확인) 단계를 넣어 충돌을 조기에 잡는다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [개요](../work-items/20260924-dev-env/index.md) · [검증 기록](../work-items/20260924-dev-env/verification.md)
