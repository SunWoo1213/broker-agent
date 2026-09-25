package broker.authz

# 입력 · 출력 계약: docs/decisions.md D18.
# 입력  {agent, user, action:{name, risk}, delegation:{scopes, per_tx_limit, expires_at}, args}
# 출력  {result: "allow" | "deny" | "require_approval", reason}
# 1단계에서는 승인이 필요한 요청도 "deny"로 낸다(approval_result). 2단계 8번에서 교체한다.

# 기본값은 거부다 (D1 fail-closed). 글자 그대로 유지한다.
default decision := {"result": "deny", "reason": "no_matching_rule"}

# 2단계(docs/plan.md 8번)에서 "require_approval"로 바꾼다. 1단계에는 승인 흐름이 없으므로 거부.
approval_result := "deny"

expense_create := "expense.create"

mail_send := "mail.send"

internal_mail_domains := {"example.com"}

# 판단: 거부(1-5) > 승인 경로(6-8) > 허용(9) > 기본값. else 체인으로 우선순위를 명시한다.
decision := {"result": "deny", "reason": r} if {
	r := deny_reason
} else := {"result": approval_result, "reason": r} if {
	r := approval_reason
} else := {"result": "allow", "reason": "low_risk_in_scope"} if {
	allow_ok
}

deny_reason := "invalid_input" if {
	not valid_input
} else := "invalid_args" if {
	not valid_args
} else := "action_not_in_scope" if {
	not in_scope
} else := "delegation_expired" if {
	expired
} else := "per_tx_limit_exceeded" if {
	over_per_tx_limit
}

approval_reason := "approval_required_high_risk" if {
	input.action.risk == "high"
} else := "approval_required_external_recipient" if {
	input.action.name == mail_send
	has_external_recipient
} else := "approval_required_medium_risk" if {
	input.action.risk == "medium"
}

# 허용은 양성 조건의 AND만 쓴다. 오타 · undefined는 허용이 아니라 기본 거부로 떨어진다.
allow_ok if {
	valid_input
	valid_args
	in_scope
	not_expired
	within_per_tx_limit
	recipients_ok
	input.action.risk == "low"
}

# 입력 계약 (D18 + 계획 세부). 알 수 없는 최상위 필드는 무시한다(K8).
valid_input if {
	is_object(input)
	is_string(input.agent)
	input.agent != ""
	is_string(input.user)
	input.user != ""
	is_object(input.action)
	is_string(input.action.name)
	input.action.name != ""
	input.action.risk in {"low", "medium", "high"}
	is_object(input.delegation)
	is_array(input.delegation.scopes)
	every s in input.delegation.scopes {
		is_string(s)
	}
	is_number(input.delegation.per_tx_limit)
	input.delegation.per_tx_limit == round(input.delegation.per_tx_limit)
	input.delegation.per_tx_limit >= 0
	is_string(input.delegation.expires_at)
	expires_ns
	is_object(input.args)
}

# 작업별 인자 검사. 액션마다 독립된(OR로 합쳐지는) 규칙 블록.
valid_args if {
	input.action.name == expense_create
	is_number(input.args.amount)
	input.args.amount == round(input.args.amount)
	input.args.amount >= 1
}

valid_args if {
	input.action.name == mail_send
	is_object(input.args)
	count(object.keys(input.args) - {"to", "subject", "body"}) == 0
	is_array(input.args.to)
	count(input.args.to) >= 1
	every r in input.args.to {
		is_string(r)
		recipient_format_ok(r)
	}
	is_string(input.args.subject)
	is_string(input.args.body)
}

valid_args if {
	input.action.name != expense_create
	input.action.name != mail_send
	is_object(input.args)
}

recipient_format_ok(r) if {
	parts := split(r, "@")
	count(parts) == 2
	parts[0] != ""
	parts[1] != ""
}

in_scope if {
	some s in input.delegation.scopes
	s == input.action.name
}

# 만료: 파싱 실패 · 문자열이 아니면 expires_ns가 undefined -> expired · not_expired 모두 undefined -> 기본 거부.
expires_ns := time.parse_rfc3339_ns(input.delegation.expires_at) if {
	is_string(input.delegation.expires_at)
}

expired if {
	time.now_ns() >= expires_ns
}

not_expired if {
	time.now_ns() < expires_ns
}

over_per_tx_limit if {
	input.action.name == expense_create
	input.args.amount > input.delegation.per_tx_limit
}

# expense.create가 아니면 참, 맞으면 amount <= per_tx_limit.
within_per_tx_limit if {
	input.action.name != expense_create
}

within_per_tx_limit if {
	input.action.name == expense_create
	input.args.amount <= input.delegation.per_tx_limit
}

# mail.send가 아니면 참, 맞으면 every 수신자가 사내(양성 조건, has_external_recipient를 부정하지 않는다).
recipients_ok if {
	input.action.name != mail_send
}

recipients_ok if {
	input.action.name == mail_send
	is_array(input.args.to)
	every r in input.args.to {
		internal_recipient(r)
	}
}

has_external_recipient if {
	some r in input.args.to
	not internal_recipient(r)
}

# 사내 판정: `@` 뒤 조각을 lower()한 값이 internal_mail_domains에 정확히 있을 때만 참.
internal_recipient(r) if {
	is_string(r)
	parts := split(r, "@")
	count(parts) == 2
	internal_mail_domains[lower(parts[1])]
}
