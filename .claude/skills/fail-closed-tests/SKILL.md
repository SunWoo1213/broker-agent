---
name: fail-closed-tests
description: 외부 의존성(OPA · PostgreSQL · Redis · 도구 서버)이 멈추거나 느리거나 이상한 응답을 줄 때 브로커가 거부하는지 확인하는 pytest 작성법. 외부 호출이 들어간 코드를 구현할 때 사용한다.
---

# fail-closed 테스트 작성법

## 언제

외부 의존성을 호출하는 코드를 새로 쓰거나 바꿀 때마다 아래 네 가지 경우의 테스트를 **구현보다 먼저** 쓴다.

| 경우 | 흉내 내는 방법 | 기대 |
|---|---|---|
| 연결 불가 | 닫힌 포트로 주소 지정, 또는 클라이언트가 `ConnectionError`를 던지게 함 | `deny`, reason에 의존성 이름 |
| 타임아웃 | 응답을 설정 타임아웃보다 늦게 주는 가짜 서버 | `deny`, 전체 응답 시간 ≤ 타임아웃 + 여유 |
| 이상한 응답 | 빈 본문, 필드 누락, 알 수 없는 `result` 값, 잘못된 JSON | `deny` |
| 부분 실패 | 판단은 allow인데 outbox 쓰기 실패 | 도구 호출 없음, 트랜잭션 롤백 |

## 규칙

- 단위 테스트는 가짜 객체(테스트 더블)로 빠르게, 통합 테스트는 `docker compose stop <서비스>`로 실제 중단을 재현한다. 통합 테스트는 `@pytest.mark.integration`으로 구분한다.
- assert는 결과(`deny`)와 이유(`reason`)를 **둘 다** 확인한다. 결과만 보면 다른 이유로 거부돼도 통과해 버린다.
- "도구가 호출되지 않았다"를 확인한다. 가짜 도구의 호출 횟수가 0인지 본다.
- 테스트 이름에 의존성과 상황을 넣는다: `test_opa_timeout_denies_and_skips_tool`

## 안전장치를 검증하는 테스트

가드(삭제 방지, 권한 검사, 실행 차단)가 실제로 발동하는지 확인하는 테스트는 일반 테스트와 다른 위험이 있다.
변이 절차는 **그 가드를 제거하는 변이를 반드시 포함**하므로, 가드가 없는 상태로 테스트 본문이 끝까지 실행되는
순간이 언젠가 반드시 온다. 그때 무엇이 파괴되는지는 테스트의 입력이 결정한다.

- **가드를 제거한 상태로 실행돼도 실제 자원에 피해가 없는 입력을 쓴다.** 입력이 "보호 대상 그 자체"(개발용
  DB, 실서비스 주소, 사용자 파일)면 변이 실행 때 실제로 파괴된다. 보호 대상과 **같은 이름 규칙**을 쓰되
  닿을 수 없게 만든다 — 닫힌 포트, 존재하지 않는 데이터베이스 · 파일 이름. 이름 규칙을 지켜야 가드의
  패턴 일치를 진짜로 검사하고, 닿을 수 없어야 통과했을 때 피해가 없다.
- **실패 조건을 환경 상태에 기대지 않고 테스트가 직접 만든다.** "이 기계에는 인터프리터가 없다", "이 서비스는
  안 떠 있다" 같은 전제에 기대면, 환경이 바뀌는 순간 테스트가 **조용히 무력해진다**(여전히 통과하지만 아무것도
  검사하지 않는다). 빈 `PATH`를 넘기거나 임시 폴더를 가리키는 식으로 조건을 테스트 안에서 구성한다.

근거 사건 둘:

- 작업 C의 변이 U12(`.claude/runs/20260929-data-model/evidence/69-mut-ac-red.log`) — 가드를 지우는 변이를
  적용하자 개발용 DB의 스키마가 **실제로 삭제**됐다. 테스트 입력이 실제 개발용 DB였다.
- `docs/wiki/troubleshooting/fail-closed-test-relied-on-missing-venv.md` — `.venv`가 생기자 훅 안전장치
  테스트 2개가 무력해졌다. 실패 조건이 "이 기계에 venv가 없다"였다.

## 예시 골격

```python
async def test_opa_unreachable_denies(gateway, fake_tool):
    gateway.policy_client.base_url = "http://127.0.0.1:1"  # 닫힌 포트
    result = await gateway.handle(call("expense.create", amount=10_000))
    assert result.decision == "deny"
    assert result.reason == "policy_engine_unreachable"
    assert fake_tool.calls == 0
```
