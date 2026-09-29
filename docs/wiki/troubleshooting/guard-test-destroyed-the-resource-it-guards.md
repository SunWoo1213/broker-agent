# 가드를 검증하는 테스트가 가드를 뺀 순간 보호 대상을 실제로 부쉈다

> 요약
> - 한 줄 해결: 가드 검증 테스트의 입력을 보호 대상 그 자체가 아니라, 가드가 없어도 닿을 수 없는 주소(닫힌 포트 + 존재하지 않는 이름)로 바꾼다.
> - 원인: 변이 절차가 "가드를 제거한다"를 반드시 포함하므로, 가드를 검증하는 테스트의 입력이 실제 보호 대상이면 가드가 없는 순간 그 자원이 실제로 파괴된다.
> - 재발 방지: `skills/fail-closed-tests`에 "안전장치를 검증하는 테스트" 절, `skills/plan-review`에 P14를 추가하는 것을 하네스 개선안으로 제안(2026-09-29 시점 **제안 상태**, 사용자 승인 뒤 반영).

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-29 | 테스트 | 해결(코드) · 규칙 승격은 미반영(제안) | ③ 구현 중 변이 실행(`ac`) → ④ 구현 검증 지적 1 | 원칙 1 (fail-closed), 원칙 7 (기대값을 결과에 맞춰 바꾸지 않는다) |

## 증상

`1. 데이터 모델 (1차)` 작업(작업 C)의 변이 확인 절차에서, 변이 `ac`(`tests/dbsupport.py`의
`reset_schema()`가 쓰는 DB 이름 가드 제거)를 적용하고 명령 A를 실행했다.
기대는 `test_reset_refuses_non_test_database`(U12)가 red(가드 없음 → 거부 실패)가 되는 것이었는데,
그보다 먼저 **개발용 `broker` DB에 실제로 `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`이 실행됐다.**

```
69-mut-ac-red.log
FAILED tests/test_db_config.py::test_reset_refuses_non_test_database
... DID NOT RAISE <class 'ValueError'>
```

`DID NOT RAISE`는 "가드가 없어서 예외가 안 났다"는 뜻이고, 이 테스트의 입력이
`postgresql+psycopg://broker:broker@localhost:5434/broker`(실제 개발용 URL)였기 때문에
가드가 없는 상태에서 그대로 연결해 스키마를 지우고 다시 만들었다.

## 재현 방법

1. 안전장치를 검증하는 테스트를 쓰되, 입력으로 **보호 대상의 실제 주소**를 그대로 쓴다.
2. 계획대로 "가드를 제거하는 변이"를 실행한다(변이 절차는 이 단계를 반드시 포함한다).
3. 가드가 없으므로 테스트 코드가 실제 자원에 연결해 부수 효과를 낸다.

## 원인

1. 직접 원인: `tests/test_db_config.py:123-125`의 `test_reset_refuses_non_test_database`가
   개발용 `broker` DB의 실제 URL을 입력으로 썼다. 가드(`_require_test_db_name`, `tests/dbsupport.py:44-49`)가
   있을 때는 엔진 생성 **전에** `ValueError`로 끝나 이 입력이 위험하다는 사실이 드러나지 않는다.
2. 왜? → 변이 `ac`는 정확히 이 가드를 제거하는 변이다. 가드 검증 테스트는 "가드가 없을 때 이 테스트가
   무엇을 하는가"까지 항상 실제로 실행된다 — 변이 절차의 정의상 피할 수 없다.
3. 근본 원인: **테스트 입력이 보호 대상 그 자체였다.** 안전장치를 검증하는 테스트는 안전장치가 없는
   상태에서 실행돼도 피해가 없어야 하는데, 이 테스트는 그 조건을 만족하지 못했다.

같은 계열의 문제가 같은 날 오전에도 있었다: [fail-closed-test-relied-on-missing-venv.md](fail-closed-test-relied-on-missing-venv.md)는
실패 조건을 "이 기계에 `.venv`가 없다"는 환경 상태에 기댄 사건이고, [ci-test-spec-quantifier-weakening.md](ci-test-spec-quantifier-weakening.md)는
테스트가 "모든·하나" 같은 전칭 문장을 실제로는 강제하지 못한 사건이다. 세 건의 공통 줄기는
**테스트가 통과한다는 사실만으로는 그 테스트가 무엇을 확인했는지 알 수 없다**는 것이다.

## 해결

`tests/test_db_config.py`의 U12 입력을 닿을 수 없는 비테스트 URL로 바꿨다:
`postgresql+psycopg://broker:broker@127.0.0.1:1/broker_do_not_touch`
(루프백 호스트 + **닫힌 포트 1** + 존재하지 않고 테스트 접미사도 아닌 이름 `broker_do_not_touch`).

- 가드가 있으면: `make_url(url).database` = `broker_do_not_touch` → 접미사(`_test`/`_test_mig`)
  불일치 → **엔진 생성 전** `ValueError` → 테스트 통과(가드 있음 상태).
- 가드가 없으면(변이 `ac`): 엔진을 만들고 `engine.begin()`을 시도 → 포트 1은 닫혀 있어
  `sqlalchemy.exc.OperationalError`(`ValueError`의 하위 클래스가 아님) → `pytest.raises(ValueError)`가
  여전히 실패 → red. **어떤 경우에도 실제 DB에 연결이 성립하지 않는다.**

## 검증

- `92-mut-ac-red.log`(exit 1): `FAILED …test_reset_refuses_non_test_database`, 원인 줄
  `psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 1 failed: … Connection refused`.
  `ValueError`가 아니므로 여전히 red — 검증력 유지.
- `93-mut-ac-green.log`(exit 0): 되돌린 뒤 `70 passed`.
- 기대 FAIL 집합은 계획·`checks/check_ac.py` 모두 `{test_reset_refuses_non_test_database}` 하나 그대로다(변경 없음, 원칙 7).
- ③이 `broker`의 `public` 스키마에 직접 연결해 확인: `SELECT tablename FROM pg_tables WHERE schemaname='public'` → `[]`(비어 있음).
  1회 재생성된 사실은 사용자에게 AC11로 보고했고 사용자 답은 "그대로 두세요"(`00-approval.md`).
  **주의:** "드롭 직전에 비어 있었다"는 사후에 증명할 수 없다 — 이 사건 이후에 비어 있음을 확인한 것뿐이다.

## 재발 방지

- 코드: U12 입력 교체(위). 사본 방식으로 원본을 보존하고(`mutbak/`), 라벨 `mut-ac-red`/`mut-ac-green`을 재실행해
  같은 라벨의 마지막 로그가 채점에 쓰이도록 했다(H6).
- 규칙(제안, **미반영** — 사용자 승인 대기):
  - `skills/fail-closed-tests/SKILL.md`에 새 절 "안전장치를 검증하는 테스트": 가드를 제거한 상태로 실행돼도
    실제 자원에 피해가 없는 입력을 쓴다(보호 대상과 같은 이름 규칙이지만 닿을 수 없게).
  - `skills/plan-review/SKILL.md`에 P14: 변이 표에 "가드를 제거하는" 변이가 있으면, 그 가드를 검증하는
    테스트의 입력이 실제 보호 대상인지 ②가 확인하고, 실제 자원이면 REVISE.
  - 이 개선안은 `.claude/harness-notes.md`에 `2026-09-29 1. 데이터 모델 (1차) (작업 C)` 절로 기록됐고
    (H4 · H5), 아직 Skill 파일 자체는 고쳐지지 않았다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- [fail-closed-test-relied-on-missing-venv.md](fail-closed-test-relied-on-missing-venv.md) — 같은 날 오전, 실패 조건을 환경 상태에 기댄 사건
- [ci-test-spec-quantifier-weakening.md](ci-test-spec-quantifier-weakening.md) — 전칭 표현을 실제로 강제하지 못한 사건
- 작업 페이지: [work-items/20260929-data-model/index.md](../work-items/20260929-data-model/index.md)
