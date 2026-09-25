# 에이전트 권한 브로커 — AI 에이전트의 도구 호출을 허용 · 거부 · 승인으로 통제하는 검문소

> 🚧 진행 중 (2026.09 ~)

AI 에이전트가 사람 대신 사내 시스템을 호출할 때 반드시 거쳐 가는 브로커입니다. 에이전트는 실제 API 키를 가지지 않고, 모든 도구 호출을 브로커에 요청합니다. 브로커는 요청마다 **허용 / 거부 / 사람 승인 필요** 중 하나로 판단하고, 판단 근거를 위변조를 드러내는 감사 로그로 남깁니다.

## 왜 만드나

기업이 에이전트 도입을 망설이는 가장 큰 이유는 "에이전트에게 권한을 어디까지 줘도 되나"입니다. 프롬프트 주입에 당한 에이전트가 권한 밖의 데이터를 읽거나, 한도를 쪼개서 우회하거나, 승인받은 뒤 인자를 바꾸는 일을 **에이전트 바깥의 코드**로 막는 것이 이 프로젝트의 목표입니다.

## 핵심 기능

- 사용자 → 에이전트 **권한 위임** (범위 · 건당 / 일일 한도 · 기한, 즉시 취소)
- **정책 판단** (OPA): 허용 / 거부 / 승인 필요 + 이유
- **사람 승인**: 인자 해시에 묶여, 승인 후 인자를 바꾸면 실행되지 않음
- **임시 토큰**: 작업 하나 · 5분짜리. 에이전트는 진짜 키를 보지 못함
- **누적 한도**: 예약 → 확정 / 해제로 동시 요청에도 초과 없음
- **감사 로그**: 아웃박스 + 해시 체인

## 진행 상황

1단계(브로커를 거치지 않으면 도구를 호출할 수 없는 최소 형태)를 진행 중입니다. 현재 위치와 다음 할 일은 [1단계 계획서](docs/stage1-plan.md) 2장 · 4장에 있습니다.

| 작업 | 내용 | 상태 |
|---|---|---|
| A | 개발 환경 — 패키지 · 이미지 버전 고정, Docker Compose(PostgreSQL · Redis · OPA) | 완료 |
| B | pytest 설정 · GitHub Actions CI | 완료 |
| D | OPA 정책 — 입력 · 출력 계약(D18), 규칙별 `opa test` | 완료 (CI 원격 확인 대기) |
| C · E ~ L | 데이터 모델, 모의 도구, 게이트웨이, 데모 에이전트, 1단계 완료 판정 | 대기 |

## 정책 개요 (`policies/authz.rego`)

- 입력 `{agent, user, action: {name, risk}, delegation: {scopes, per_tx_limit, expires_at}, args}` → 출력 `{result, reason}` (키는 정확히 두 개)
- 기본값은 거부(`no_matching_rule`). 입력이 없거나 필드가 빠지거나 타입이 틀리면 거부(`invalid_input`)
- 이유 코드 우선순위: `invalid_input` > `invalid_args` > `action_not_in_scope` > `delegation_expired` > `per_tx_limit_exceeded` > `approval_required_*` > `low_risk_in_scope`(허용)
- 1단계에서는 승인이 필요한 요청(위험도 높음 · 중간, 사내 밖 수신자 메일)도 거부합니다. 2단계에서 `require_approval`로 바꿉니다
- 계약 원문: [설계 결정 D18](docs/decisions.md)

## 문서

- [아키텍처](docs/architecture.md)
- [설계 결정](docs/decisions.md)
- [진행 계획](docs/plan.md)
- [1단계 계획 · 현재 상태](docs/stage1-plan.md)
- [개발 위키 (작업 기록 · 문제 해결)](docs/wiki/Home.md)

## 로컬 실행 (현재)

```bash
cp env.example .env
docker compose up -d          # PostgreSQL · Redis · OPA
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements-dev.txt
```

## 테스트 실행

```bash
docker compose run --rm opa test /policies -v   # 정책 단위 테스트 (작업 D 기준 54개)
python -m pytest -q                              # pytest (작업 D 기준 13개). Windows venv: .venv/Scripts/python -m pytest -q
```

Windows Git Bash에서는 첫 명령 앞에 `MSYS_NO_PATHCONV=1`을 붙입니다(컨테이너 안 경로 `/policies`가 바뀌지 않게). CI(`.github/workflows/ci.yml`)가 main 푸시 · PR마다 같은 두 명령을 실행합니다(pytest는 junit xml 옵션만 추가).
