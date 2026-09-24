# tests

pytest. 1단계 완료 판정 테스트(docs/plan.md 6번)부터 시작한다.

## 실행 방법

저장소 루트에서 실행한다 (`pytest.ini`가 `testpaths = tests`를 지정한다).

- 전체: `.venv/Scripts/python -m pytest -q` (CI에서는 `python -m pytest -q --junitxml=...`)
- 단위만 (통합 제외): `.venv/Scripts/python -m pytest -q -m "not integration"`
- 통합만: `.venv/Scripts/python -m pytest -q -m integration`

`-m "not integration"`을 **기본 `addopts`에 넣지 않는다.** 옵션 없이 실행하면 통합 테스트도 함께 돈다.

## `integration` 마커 규칙

- 실제 PostgreSQL · Redis · OPA(`docker compose`)가 필요한 테스트에 `@pytest.mark.integration`을 붙인다.
- 서비스가 꺼져 있으면 **실패한다.** `skip`으로 바꾸지 않는다 (fail-closed. `CLAUDE.md` 불변 원칙 1).
- `@pytest.mark.integration`은 `pytest.ini`의 `markers`에 등록돼 있다. 등록하지 않은 마커는 오타로 보고 오류로 처리한다 (`strict = true`).

## async 테스트

- `asyncio_mode = strict`다. `async def` 테스트에는 **반드시** `@pytest.mark.asyncio`를 붙인다. 표시가 없으면 실패한다 (skip이 아니다).

