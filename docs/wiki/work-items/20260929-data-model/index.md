# 1. 데이터 모델 (1차) — 작업 C

> 요약
> - 결론: 완료. `agents` · `tools` · `tool_actions` · `delegations` 테이블 4개 + Alembic 마이그레이션 1개 + 고정 시드를 만들고, 단위 70 · 통합 27(계획 46 + 지적 반영 3) = 97 테스트, 변이 37종 전부 기대 집합과 정확히 일치.
> - 바뀐 것: `control/db/`(모델 · 세션 · 이벤트루프 · 시드 · 마이그레이션), `alembic.ini`, `tests/`(신규 7파일), `.github/workflows/ci.yml`에 `pytest-integration` job 추가, `docs/decisions.md` D21 확정.
> - 다음에 알아야 할 것: 개발용 `broker` DB의 `public` 스키마가 작업 중 1회 재생성됐다(현재 비어 있음, 원인은 수정됨). 증거 로그 2건에 개발용 DB 비밀번호가 평문으로 남아 있다(운영 값 아님, 마스킹 개선은 미반영). AC10(원격 CI)은 이 기록 시점까지 커밋 · 푸시 전이라 미확인.

| 날짜 | plan.md 항목 | 결과 | 관문 재시도 | 개선 사이클 |
|---|---|---|---|---|
| 2026-09-29 | 1단계 4장 순서 C, `docs/plan.md` "### 1. 데이터 모델 (1차)" | 완료 | ② 1회(REVISE→APPROVE) · ④ 1회(REVISE→APPROVE) · ⑦ 1회(REVISE→APPROVE, 문서 정정만) | 1회(코드 수정 없음) |

## 1. 목표

게이트웨이 · 정책이 참조할 1차 데이터 모델을 만든다: 에이전트, 도구, 도구가 제공하는 작업(위험도 ·
JSON Schema 포함), 사람의 위임(범위 · 한도 · 만료). 이 테이블들의 값이 D18이 정한 OPA 입력 계약
`{agent, user, action:{name, risk}, delegation:{scopes, per_tx_limit, expires_at}, args}`의
출처가 되므로, 정책이 `invalid_input`으로 막아야 할 값을 **DB 제약으로 먼저** 막는 이중 방어를 노린다.

관련 불변 원칙: 1(fail-closed 기본값 · 연결 실패 시 거부) · 2(자격 증명 비노출 · 공개키만 시드) ·
5(감사 테이블은 아직 안 만듦, 테이블 집합을 정확히 4개로 고정) · 7(재현 가능, 시드는 고정 상수,
변이 37종을 실행 전에 손 추적).

## 2. 설계와 결정

- **배치:** 모델 · 마이그레이션 · 시드는 `control/db/`(컨트롤 플레인)에 둔다. 게이트웨이는 이후
  작업(F 이후)에서 이 모델을 읽기 전용으로 import한다.
- **제약 형태:** `tool_actions.risk` · `agents.status`는 네이티브 ENUM이 아니라 `TEXT + CHECK` —
  값 추가 · 제거가 Alembic에서 단순하고, `risk` 문자열이 그대로 OPA 입력으로 나가 변환 계층이 필요 없다.
  작업 이름은 점 표기 CHECK + UNIQUE. 위임 범위(`delegations.scopes`)는 `TEXT[]`이고 `tool_actions`로의
  FK를 **두지 않는다** — 오타 난 범위 문자열은 어떤 작업 이름과도 같지 않아 이미 닫히는 방향이고,
  D18 입력의 `scopes` 배열과 모양이 같다.
- **기본값은 전부 닫히는 쪽:** `agents.status` = `suspended`, `per_tx_limit` · `daily_limit` = `0`,
  `scopes` = `{}`.
- **D18 문구 해석:** "한도 없는 위임은 0"은 금액 인자가 없는 작업만 가진 위임(예: `mail.send`)을
  가리키고, `expense.create`에서 0은 모든 금액을 `per_tx_limit_exceeded`로 막는다는 뜻이다
  (`policies/authz_test.rego:246-250`이 이미 이 방향으로 고정돼 있었다). 값 · 규칙을 바꾼 게 아니라
  애매한 문구에 해석만 붙였다.
- **시드(고정, 재현 가능):** 에이전트 1개(`agent-expense-01`, RFC 8032 **공개** 테스트 벡터 공개키,
  `status = suspended`), 도구 3개, 작업 4개(`expense.create` low · `expense.list` low ·
  `mail.send` **medium** · `customer.lookup` high), 위임 2개(`alice@example.com` per_tx_limit 200000,
  `bob@example.com` per_tx_limit 0), 만료 `2027-12-31T23:59:59+09:00`.
  - 시드 에이전트를 `suspended`로 둔 이유: 시드 공개키는 누구나 아는 공개 테스트 벡터라, 이 상태로
    `active`면 "아무나 서명할 수 있는 에이전트"가 활성으로 남는다(원칙 1 · 2).
  - `mail.send`를 `medium`으로 둔 이유: 정책의 허용 조건이 `risk == "low"`라, 메일 전송이 수신자와
    무관하게 항상 승인 경로(1단계에서는 거부)를 거치게 하기 위함.
- **검토했지만 버린 대안:** (a) `scopes`를 조인 테이블 + FK로 — D18 입력 모양과 어긋나고 쿼리가 늘어난다.
  (b) 네이티브 ENUM — 값 추가 시 마이그레이션이 복잡하다. (c) 시드 에이전트를 `active`로 — 공개된
  테스트 키로 활성 에이전트를 만들게 된다.
- **decisions.md에 추가한 항목:** D21(`docs/decisions.md:22`, 상세 `:31-37`). 계획 승인 직후 ·
  구현(③) 시작 전에 메인 세션이 반영했다(작업 D의 교훈 H8 — 승인된 결정을 "마무리"로 미루지 않는다).

> 검증 상세: [verification.md](verification.md) · 테스트 상세: [testing.md](testing.md)

## 3. 진행 기록

| 단계 | 판정 | 요지 |
|---|---|---|
| ② 계획 검증 | 1차 REVISE(지적 11건) → 2차 APPROVE | 변이 표 내부 모순(I19 ↔ k, I16/I15 형태 미지정), 짝 없는 변이 4개, 강제력 약한 변이 2개, 삭제 단계(변이 r 되돌림), AC6가 `docs/decisions.md`를 BAD로 분류, AC4 문구 불일치, `python` 맨 이름, CI 회귀 문자열 미명시, 타임아웃 동작 테스트 없음 — 전부 반영 |
| ④ 구현 검증 | 1차 REVISE(지적 4 + 권고 3) → 2차 APPROVE | U12가 개발용 `broker` DB를 실제로 지움(가장 중요), 거부 테스트 없는 제약 3개, 구현 전 red 증거 부재 + 어느 변이에서도 red 없던 테스트 3개, 03 문서 정정 3건 — 전부 반영 |
| ⑤ 테스트 | APPROVE | 단위 70 · 통합 27 = 97 통과, 변이 37/37 exact 일치, flaky 3회 반복 동일, `--verify` 134/134 일치 |
| ⑥ 개선사항 계획 | 판정 "코드 수정 없음" | 발견 11건을 근본 원인별로 정리, 코드 사이클 불필요, 하네스 개선안 H1–H7 · 후속 F-C1–F-C5 제안 |
| ⑦ 개선 계획 검증 | 1차 REVISE(⑥ 문서 정정 5건, 코드 사이클 불필요) → 2차 APPROVE | "원칙 7 때문에 못 고친다"는 거짓 이분법, P14가 사건 하나만 잡음, F-C2 시점 미고정, F-C5 검증 방법 미비, 표 6의 사실 오류 — 전부 정정. 이 정정은 개선 사이클 횟수에 더하지 않았다 |

## 4. 구현 요약

| 파일 | 변경 |
|---|---|
| `alembic.ini` | 신규. `script_location = control/db/migrations`, `sqlalchemy.url` 비움 |
| `control/__init__.py` · `control/db/__init__.py` | 신규(빈 파일), 패키지화 |
| `control/db/models.py` | 신규. 테이블 4개 + CHECK/FK/UNIQUE/INDEX |
| `control/db/session.py` | 신규. `get_database_url` · `redact_url` · `_validate_driver` · `_connect_args` · `create_engine[_from_env]` · `db_ping` |
| `control/db/eventloop.py` | 신규. D20 Windows Selector 판단 |
| `control/db/seed.py` | 신규. 고정 시드 상수 + `seed_all()`(멱등, 커밋 안 함) + `main()` |
| `control/db/migrations/env.py` · `script.py.mako` · `versions/0001_initial_schema.py` | 신규. URL: config main option → `DATABASE_URL` → 예외(fail-closed) |
| `tests/conftest.py` | 신규. `event_loop_policy` 픽스처, 테스트 DB 준비 · 세션 픽스처 |
| `tests/dbsupport.py` | 신규. 테스트 전용 동기 도우미(`ensure_database` · `reset_schema` · `upgrade_head` 등) |
| `tests/test_db_config.py` · `test_db_models.py` · `test_seed_constants.py` | 신규. 단위 U1–U22 |
| `tests/test_db_schema.py` · `test_seed_data.py` | 신규. 통합 I1–I24 + 지적 반영 I25–I27 |
| `tests/test_ci_workflow.py` | `REQUIRED_JOBS`에 `pytest-integration` 추가, 문자열 · `persist_count` 갱신, U22 추가 |
| `.github/workflows/ci.yml` | `pytest` job을 `-m "not integration"`으로, `pytest-integration` job(ubuntu 전용 + postgres 서비스) 추가 |
| `requirements.txt` | `greenlet==3.5.6` 추가(SQLAlchemy asyncio 필수) |
| `docs/decisions.md` | D21 추가(사람이 승인, 메인 세션이 ③ 전에 반영) |

## 5. 테스트

- 단위 70 passed, 통합 27 passed(계획 24 + ④ 지적으로 추가된 I25–I27), 전체 97 passed, 변이 37종 전부
  기대 FAIL 집합과 정확히 일치, flaky 없음(3회 반복 동일 결과).
- 완료 조건 대조 상세는 [testing.md](testing.md) 참고.

## 6. 문제 상황과 해결

| 문제 | 분류 | 상태 | 상세 |
|---|---|---|---|
| U12(가드 검증 테스트)가 실제 개발용 `broker` DB에 `DROP SCHEMA public CASCADE`를 실행 | 테스트 | 해결(코드) · 규칙 승격은 제안 단계 | [링크](../../troubleshooting/guard-test-destroyed-the-resource-it-guards.md) |
| pytest 긴 트레이스백이 증거 로그에 DB 비밀번호를 평문으로 남김 | 하네스 | 미해결(제안 단계) | [링크](../../troubleshooting/pytest-traceback-leaked-db-password-into-evidence-log.md) |
| U3(드라이버 검사 테스트)가 `_validate_driver()`가 아니라 SQLAlchemy 부수 효과로 통과하고 있었음(변이 `ai`로 발견) | 테스트 | 해결 | `_validate_driver()`를 직접 호출하도록 재작성. `03-build-notes.md` "계획에 없던 변경" 3번. 별도 위키 페이지는 만들지 않음 |
| "구현 전 전부 red" 증거가 구조적으로 불가능했음(`tests/conftest.py`가 모듈 최상단에서 `control.db`를 import해 컬렉션 자체가 죽음, `04-build-tests-red.log` exit 4 무효) | 테스트 | 미해결(구조적 원인은 다음 작업으로 이관, F-C용 하네스 개선안 H3 제안) | 대신 어느 변이에서도 red가 없던 테스트 3개(I4 · I23 · U9)에 채점 밖 `review-*` 라벨로 임시 red/green 증거를 남겨 대응. `03-build-notes.r2.md` 지적 3 |
| ⑥이 "원칙 7 때문에 검사를 못 늘린다"는 거짓 이분법을 논거로 썼다가 ⑦ 지적으로 정정됨 | 하네스(절차) | 해결(문서 정정) | 정정된 결론: 원칙 7은 "기대값 · 채점 기준을 결과에 맞춰 바꾸지 말라"는 것이지 "새 증거를 만들지 말라"가 아니다. 채점 밖 `review-*` 라벨로 증거를 남기는 제3의 길이 있었고, ④ 2회차가 I4·I23·U9에 실제로 이 방식을 썼다. `06-improvement-plan.r2.md` r2 반영 1 |

## 7. 배운 점

- 안전장치를 검증하는 테스트는 "가드가 없을 때 이 입력이 실제로 무엇을 하는가"까지 고려해야 한다.
  변이 절차가 가드 제거를 반드시 포함하므로, 입력이 보호 대상 그 자체면 언젠가 반드시 실제로 파괴된다.
- "원칙 7(재현 가능성)" 은 검사를 늘리지 못하게 막는 원칙이 아니라, 결과를 본 뒤 기대값 · 채점 기준을
  그 결과에 맞춰 고치지 말라는 원칙이다. 계획 밖에서 필요해진 증거는 채점 대상이 아닌 라벨(`review-*`)로
  남길 수 있다.
- 계획에 없던 더 엄격한 테스트를 구현 중 추가할 때는(이번 작업의 I25–I27), 그 사실과 변이 짝 유무를
  구현 검증에서 표로 드러내야 한다(하네스 개선안 H6이 이를 규칙으로 제안).
- 하네스 개선안: H1–H7, 후속 F-C1–F-C5. `.claude/harness-notes.md`의
  `2026-09-29 1. 데이터 모델 (1차) (작업 C)` 절 참고. **전부 제안 상태이며 사용자 승인 뒤 반영된다.**

## 8. 관련

- 커밋: (미기록 — 이 위키 기록 시점에는 아직 커밋 전)
- 선행: `0. 개발 환경`(가상환경 · 버전 고정 · compose 기동, pytest · CI), `4. 정책 (Rego)`(작업 D, D18 입력 계약)
- 후속: F-C1(변이 짝 없는 제약 3개, 다음 `control/db/models.py` 변경 작업) · F-C2(테스트 도우미 타임아웃,
  작업 H, 늦어도 작업 L 전) · F-C3(`redact_url` 폴백 정규식, 작업 F/G) · F-C4(pytest-asyncio deprecation,
  다음 `tests/conftest.py` 변경 작업) · F-C5(`.env` 접근 경로 보강, 사용자만 반영)
