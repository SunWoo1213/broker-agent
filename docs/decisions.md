# 설계 결정 기록

> 설계를 바꾸는 결정은 코드보다 먼저 여기에 적는다. 형식: 결정 / 이유 / 검증 방법 / 상태.

| ID | 결정 | 이유 | 검증 | 상태 |
|---|---|---|---|---|
| D1 | 문제가 생기면 전부 막음 (fail-closed) | 보안 시스템에서 "연결 실패 = 허용"은 우회 경로가 됨. 가용성은 캐시 · 다중 인스턴스로 보완 | OPA · DB · Redis 강제 종료 중 요청이 모두 거부되는지 | 확정 |
| D2 | 누적 한도는 예약 → 확정 / 해제 | 확인과 차감을 나누면 동시 요청이 함께 통과함 | 한도 직전 동시 요청 20개 → 초과 0건 | 확정 |
| D3 | 승인을 인자 해시에 묶음 | 승인 뒤 인자를 바꾸는 공격 차단 | 승인 후 금액 변경 시나리오 | 확정 |
| D4 | 에이전트는 실제 자격 증명을 보지 않음. 작업 하나 · 5분짜리 토큰 | 프롬프트 주입에 당해도 키 유출 없음 | 만료 토큰 · 다른 작업에 토큰 재사용 | 확정 |
| D5 | 정책은 코드가 아닌 데이터(OPA Rego) | 배포 없이 정책 변경, 변경 이력 보존 | `opa test` 단위 테스트 | 확정 |
| D6 | 캐시하되 취소는 즉시 (위임 버전 + Pub/Sub) | 매번 DB 조회는 느리고, 캐시만 믿으면 취소가 늦음 | 취소 → 차단까지 걸린 시간 | 확정 |
| D7 | 감사 로그는 아웃박스 + 해시 체인 | 동기 기록은 느리고, 단순 비동기는 유실 가능 | 워커 강제 종료 후 유실 0건, 체인 변조 탐지 | 확정 |
| D8 | 언어는 Python 하나로 통일 | 에이전트 생태계 · 기존 경험. 게이트웨이 지연이 목표(p95 20ms)를 못 맞추면 재검토 | 5단계 부하 테스트 | 잠정 |
| D9 | K8s 대신 ECS Fargate | 신입 한 프로젝트에서 AWS와 K8s를 둘 다 깊게 하기 어려움. 트래커 공고에서 AWS 요구가 더 많음 | — | 확정 |
| D18 | OPA 입력 · 출력 계약과 역할 분담. 게이트웨이 ②가 DB로 위임(존재 · 범위 · 만료 · 취소)을 먼저 확인하고, OPA(`data.broker.authz.decision`)는 입력 형식 · 범위 · 만료(②와 이중 방어) · 건당 한도 · 위험도를 판단한다. 입력 `{agent, user, action:{name, risk}, delegation:{scopes, per_tx_limit, expires_at}, args}`, 출력 `{result: allow \| deny \| require_approval, reason}`. 입력이 없거나 필드가 빠지거나 타입이 틀리면 OPA가 `deny`(`invalid_input`). 1단계에서는 승인이 필요한 요청도 정책이 `deny`(`approval_required_*`)를 낸다(상수 `approval_result` 하나, 2단계 8번에서 교체). 게이트웨이는 응답 형식 오류 · 알 수 없는 result · 타임아웃(200ms) · 연결 실패 · (1단계) `require_approval`을 모두 거부로 처리 | 위임 상태의 원본은 DB라 게이트웨이가 확인하고, 정책(D5)은 위험 판단에 집중한다. 입력 계약을 정책 안에서 다시 검사해 게이트웨이 버그가 허용으로 새지 않게 한다(D1). 1단계에는 승인 흐름이 없으므로 정책이 직접 거부해 게이트웨이 해석과 무관하게 막는다 | `opa test` 54개(필드 누락 · 타입 오류 · 경계값 · 우선순위 · 1단계 승인 경로 거부) + 변이 25종(작업 D). 게이트웨이 쪽은 작업 I(3-d) | 확정 |

### D18 상세 — OPA 입력 · 출력 계약 (1단계)

- 입력 타입: `agent` · `user` · `action.name`은 빈 문자열이 아닌 문자열. `action.risk`는 `low` · `medium` · `high`(영문 소문자). `delegation.scopes`는 문자열 배열이고 `action.name`과 정확히 같은 원소가 있어야 범위 안. `delegation.per_tx_limit`은 0 이상 정수(원, 한도 없는 위임은 0). `delegation.expires_at`은 시간대가 있는 RFC 3339 문자열. `args`는 객체. 알 수 없는 최상위 필드는 무시한다(유일한 관대한 쪽 결정. 정책이 읽는 필드가 고정돼 있어 모르는 필드로 허용이 생기지 않음을 테스트로 확인).
- 작업별 인자: `expense.create`의 `args.amount`는 1 이상 정수(원). `mail.send`의 인자 키는 `to` · `subject` · `body`만 허용하고 셋 다 필수다. `to`는 1개 이상인 이메일 문자열 배열, `subject` · `body`는 문자열(빈 문자열 허용). 사내 도메인은 정책 상수(`example.com`)이고 정확히 같은 도메인만 사내다. 수신자 중 하나라도 사내가 아니면 승인 경로. (2026-09-25 보강 — 작업 D 개선 사이클 2, K10)
- 이유 코드와 우선순위: `invalid_input` > `invalid_args` > `action_not_in_scope` > `delegation_expired` > `per_tx_limit_exceeded` > `approval_required_high_risk` > `approval_required_external_recipient` > `approval_required_medium_risk` > `low_risk_in_scope`(allow). 아무 규칙도 맞지 않으면 기본값 `no_matching_rule`(deny).
- 1단계: 승인 경로의 result는 `deny`. 2단계 8번에서 `approval_result`를 `require_approval`로 바꾸면 기대값이 바뀌는 테스트는 정확히 8개다(작업 D 변이 m의 red 증거): `test_high_risk_denied_stage1`, `test_medium_risk_denied_stage1`, `test_mail_external_recipient_denied_stage1`, `test_mail_one_external_among_internal_denied`, `test_mail_lookalike_domain_is_external`, `test_stage1_never_returns_require_approval`, `test_external_mail_never_allowed`, `test_extra_top_level_field_ignored`.

## 열린 질문

- [ ] 정책 엔진: OPA 사이드카(HTTP) vs Cedar(라이브러리 내장) — 지연 측정 후 확정
- [ ] 승인 대기 중 에이전트 재개 방식: 에이전트가 승인 ID로 재호출(현재안) vs 브로커가 콜백
- [ ] 브로커 다중 인스턴스에서 감사 체인 순서 보장 방법 (워커 1개 직렬 처리로 시작)
- [ ] (2단계 전) D10 인자 해시 정규화 규칙 · D11 토큰 서명 방식(ES256 + JWKS, `jti` 1회용)
- [ ] (3단계 전) D12 한도 기준 저장소와 Redis 복구 방식 · D13 OPA와 한도 차감의 역할 분담
- [ ] (5단계 전) D14 NAT Gateway 대신 VPC 엔드포인트 사용 여부
