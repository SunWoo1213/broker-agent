---
name: rego-policy
description: policies/ 아래 OPA Rego 정책과 opa test 단위 테스트를 작성하는 규칙. 정책 규칙을 추가 · 변경할 때 사용한다.
---

# Rego 정책 작성 규칙

## 형식

- 패키지: `broker.authz`. 결과는 `decision := {"result": "allow" | "deny" | "require_approval", "reason": "<snake_case>"}`
- `default decision := {"result": "deny", "reason": "no_matching_rule"}`는 **절대 바꾸지 않는다**
- 규칙이 겹칠 때: `deny` > `require_approval` > `allow` 우선순위를 명시적으로 구현한다 (Rego의 "완전 규칙 충돌" 오류에 기대지 않는다)
- 2단계 전까지 `require_approval`은 `deny`로 처리한다 (`docs/plan.md` 4번)

## 테스트

- 규칙 하나당 최소 **허용 한 개 + 거부 한 개** 테스트. 경계값(건당 한도와 같은 금액, 1원 초과)도 넣는다
- 입력 필드가 빠진 경우 → `deny`인지 확인하는 테스트를 넣는다
- 실행: `opa test policies -v` (로컬 opa가 없으면 `docker compose run --rm opa test /policies -v`)

## 예시

```rego
test_expense_over_per_call_limit_denied if {
	d := authz.decision with input as {"action": "expense.create", "args": {"amount": 500001}, "delegation": {"per_call_limit": 500000, "scopes": ["expense.create"]}}
	d.result == "deny"
	d.reason == "per_call_limit_exceeded"
}
```
