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

## 예시 골격

```python
async def test_opa_unreachable_denies(gateway, fake_tool):
    gateway.policy_client.base_url = "http://127.0.0.1:1"  # 닫힌 포트
    result = await gateway.handle(call("expense.create", amount=10_000))
    assert result.decision == "deny"
    assert result.reason == "policy_engine_unreachable"
    assert fake_tool.calls == 0
```
