package broker.authz

# 기본값은 거부다 (D1 fail-closed). 규칙은 docs/plan.md 4번에서 하나씩 추가한다.
default decision := {"result": "deny", "reason": "no_matching_rule"}
