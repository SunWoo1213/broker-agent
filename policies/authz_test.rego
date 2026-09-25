package broker.authz_test

import data.broker.authz

# 테스트 공통 준비 (01-plan.r2.md "먼저 쓸 테스트")

fixed_now_ns := time.parse_rfc3339_ns("2026-09-25T00:00:00Z")

decide(inp) := d if {
	d := authz.decision with input as inp with time.now_ns as fixed_now_ns
}

base_expense := {
	"agent": "demo-agent",
	"user": "emp-001",
	"action": {"name": "expense.create", "risk": "low"},
	"delegation": {
		"scopes": ["expense.create", "expense.list", "mail.send", "customer.lookup"],
		"per_tx_limit": 500000,
		"expires_at": "2099-12-31T23:59:59Z",
	},
	"args": {"amount": 180000, "description": "client dinner"},
}

base_mail := {
	"agent": "demo-agent",
	"user": "emp-001",
	"action": {"name": "mail.send", "risk": "low"},
	"delegation": {
		"scopes": ["expense.create", "expense.list", "mail.send", "customer.lookup"],
		"per_tx_limit": 500000,
		"expires_at": "2099-12-31T23:59:59Z",
	},
	"args": {"to": ["kim@example.com"], "subject": "s", "body": "b"},
}

base_lookup := {
	"agent": "demo-agent",
	"user": "emp-001",
	"action": {"name": "customer.lookup", "risk": "low"},
	"delegation": {
		"scopes": ["expense.create", "expense.list", "mail.send", "customer.lookup"],
		"per_tx_limit": 500000,
		"expires_at": "2099-12-31T23:59:59Z",
	},
	"args": {"customer_id": "c-1"},
}

missing_field_paths := {
	"agent": ["agent"],
	"user": ["user"],
	"action": ["action"],
	"action_name": ["action", "name"],
	"action_risk": ["action", "risk"],
	"delegation": ["delegation"],
	"delegation_scopes": ["delegation", "scopes"],
	"delegation_per_tx_limit": ["delegation", "per_tx_limit"],
	"delegation_expires_at": ["delegation", "expires_at"],
	"args": ["args"],
}

# A. 입력 계약 -- fail-closed (23)

test_default_deny if {
	authz.decision.result == "deny" with input as {}
}

test_no_input_denied if {
	d := authz.decision with time.now_ns as fixed_now_ns
	d == {"result": "deny", "reason": "invalid_input"}
}

test_non_object_input_denied if {
	every v in [[], "x", null, 1, true] {
		d := decide(v)
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_missing_agent_denied if {
	inp := json.remove(base_expense, [missing_field_paths.agent])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_user_denied if {
	inp := json.remove(base_expense, [missing_field_paths.user])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_action_denied if {
	inp := json.remove(base_expense, [missing_field_paths.action])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_action_name_denied if {
	inp := json.remove(base_expense, [missing_field_paths.action_name])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_action_risk_denied if {
	inp := json.remove(base_expense, [missing_field_paths.action_risk])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_delegation_denied if {
	inp := json.remove(base_expense, [missing_field_paths.delegation])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_delegation_scopes_denied if {
	inp := json.remove(base_expense, [missing_field_paths.delegation_scopes])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_delegation_per_tx_limit_denied if {
	inp := json.remove(base_expense, [missing_field_paths.delegation_per_tx_limit])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_delegation_expires_at_denied if {
	inp := json.remove(base_expense, [missing_field_paths.delegation_expires_at])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_missing_args_denied if {
	inp := json.remove(base_expense, [missing_field_paths.args])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_bad_type_agent_denied if {
	every v in [1, "", null, ["demo-agent"]] {
		d := decide(object.union(base_expense, {"agent": v}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_user_denied if {
	every v in [1, "", null] {
		d := decide(object.union(base_expense, {"user": v}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_action_denied if {
	every v in ["expense.create", [], null] {
		d := decide(object.union(base_expense, {"action": v}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_action_name_denied if {
	every v in [1, "", null] {
		d := decide(object.union(base_expense, {"action": {"name": v}}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_action_risk_denied if {
	every v in ["critical", "LOW", "", 1, null] {
		d := decide(object.union(base_expense, {"action": {"risk": v}}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_delegation_denied if {
	every v in [[], "x", null] {
		d := decide(object.union(base_expense, {"delegation": v}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_delegation_scopes_denied if {
	every v in ["expense.create", [1], {"expense.create": true}, null] {
		d := decide(object.union(base_expense, {"delegation": {"scopes": v}}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_delegation_per_tx_limit_denied if {
	every v in ["500000", 500000.5, -1, null, true] {
		d := decide(object.union(base_expense, {"delegation": {"per_tx_limit": v}}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_delegation_expires_at_denied if {
	every v in [1, "not-a-date", "2026-13-01T00:00:00Z", "2026-09-26", null] {
		d := decide(object.union(base_expense, {"delegation": {"expires_at": v}}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

test_bad_type_args_denied if {
	every v in [[], "x", null] {
		d := decide(object.union(base_expense, {"args": v}))
		d == {"result": "deny", "reason": "invalid_input"}
	}
}

# B. 거부 규칙 (9)

test_action_not_in_scope_denied if {
	inp := object.union(base_lookup, {"delegation": {"scopes": ["expense.create"]}})
	d := decide(inp)
	d == {"result": "deny", "reason": "action_not_in_scope"}
}

test_empty_scopes_denied if {
	inp := object.union(base_expense, {"delegation": {"scopes": []}})
	d := decide(inp)
	d == {"result": "deny", "reason": "action_not_in_scope"}
}

test_scope_requires_exact_match if {
	every scopes in [["expense"], ["expense.create "], ["EXPENSE.CREATE"], ["expense.*"], ["*"]] {
		inp := object.union(base_expense, {"delegation": {"scopes": scopes}})
		d := decide(inp)
		d == {"result": "deny", "reason": "action_not_in_scope"}
	}
}

test_delegation_expired_denied if {
	every exp in ["2026-09-25T00:00:00Z", "2026-09-24T23:59:59Z", "2026-09-25T09:00:00+09:00"] {
		inp := object.union(base_lookup, {"delegation": {"expires_at": exp}})
		d := decide(inp)
		d == {"result": "deny", "reason": "delegation_expired"}
	}
}

test_expense_over_per_tx_limit_denied if {
	inp := object.union(base_expense, {"delegation": {"per_tx_limit": 500000}, "args": {"amount": 500001}})
	d := decide(inp)
	d == {"result": "deny", "reason": "per_tx_limit_exceeded"}
}

test_expense_zero_limit_denies_any_amount if {
	inp := object.union(base_expense, {"delegation": {"per_tx_limit": 0}, "args": {"amount": 1}})
	d := decide(inp)
	d == {"result": "deny", "reason": "per_tx_limit_exceeded"}
}

test_expense_invalid_amount_denied if {
	d0 := decide(json.remove(base_expense, [["args", "amount"]]))
	d0 == {"result": "deny", "reason": "invalid_args"}

	every v in ["180000", 180000.5, 0, -1, true, null] {
		d := decide(object.union(base_expense, {"args": {"amount": v}}))
		d == {"result": "deny", "reason": "invalid_args"}
	}
}

test_mail_invalid_recipients_denied if {
	d0 := decide(json.remove(base_mail, [["args", "to"]]))
	d0 == {"result": "deny", "reason": "invalid_args"}

	every v in ["kim@example.com", [], [1], ["kim"], ["a@b@example.com"], ["@example.com"], ["kim@"]] {
		d := decide(object.union(base_mail, {"args": {"to": v}}))
		d == {"result": "deny", "reason": "invalid_args"}
	}
}

test_mail_unknown_field_denied if {
	d1 := decide(object.union(base_mail, {"args": {"cc": ["x@partner.example.net"]}}))
	d1 == {"result": "deny", "reason": "invalid_args"}

	d2 := decide(object.union(base_mail, {"args": {"bcc": ["x@partner.example.net"]}}))
	d2 == {"result": "deny", "reason": "invalid_args"}

	d3 := decide(object.union(base_mail, {"args": {"reply_to": "x@partner.example.net"}}))
	d3 == {"result": "deny", "reason": "invalid_args"}
}

test_mail_subject_body_required_denied if {
	d0 := decide(json.remove(base_mail, [["args", "subject"]]))
	d0 == {"result": "deny", "reason": "invalid_args"}

	d1 := decide(json.remove(base_mail, [["args", "body"]]))
	d1 == {"result": "deny", "reason": "invalid_args"}

	d2 := decide(object.union(base_mail, {"args": {"subject": 1}}))
	d2 == {"result": "deny", "reason": "invalid_args"}

	d3 := decide(object.union(base_mail, {"args": {"body": null}}))
	d3 == {"result": "deny", "reason": "invalid_args"}

	d4 := decide(object.union(base_mail, {"args": {"subject": ["s"]}}))
	d4 == {"result": "deny", "reason": "invalid_args"}

	d5 := decide(object.union(base_mail, {"args": {"body": {"x": 1}}}))
	d5 == {"result": "deny", "reason": "invalid_args"}
}

# C. 승인 경로 -- 1단계는 거부 (6)

test_high_risk_denied_stage1 if {
	inp := object.union(base_lookup, {"action": {"risk": "high"}})
	d := decide(inp)
	d == {"result": "deny", "reason": "approval_required_high_risk"}
}

test_medium_risk_denied_stage1 if {
	inp := object.union(base_lookup, {"action": {"risk": "medium"}})
	d := decide(inp)
	d == {"result": "deny", "reason": "approval_required_medium_risk"}
}

test_mail_external_recipient_denied_stage1 if {
	inp := object.union(base_mail, {"args": {"to": ["x@partner.example.net"]}})
	d := decide(inp)
	d == {"result": "deny", "reason": "approval_required_external_recipient"}
}

test_mail_one_external_among_internal_denied if {
	inp := object.union(base_mail, {"args": {"to": ["a@example.com", "b@example.com", "x@partner.example.net"]}})
	d := decide(inp)
	d == {"result": "deny", "reason": "approval_required_external_recipient"}
}

test_mail_lookalike_domain_is_external if {
	every to in [["x@example.com.evil.net"], ["x@sub.example.com"], ["x@notexample.com"], ["x@example.co"]] {
		inp := object.union(base_mail, {"args": {"to": to}})
		d := decide(inp)
		d == {"result": "deny", "reason": "approval_required_external_recipient"}
	}
}

test_stage1_never_returns_require_approval if {
	authz.approval_result == "deny"

	d1 := decide(object.union(base_lookup, {"action": {"risk": "high"}}))
	d1.result == "deny"

	d2 := decide(object.union(base_lookup, {"action": {"risk": "medium"}}))
	d2.result == "deny"

	d3 := decide(object.union(base_mail, {"args": {"to": ["x@partner.example.net"]}}))
	d3.result == "deny"
}

# D. 우선순위 · 기본값 (5)

test_invalid_input_beats_other_reasons if {
	inp0 := object.union(base_expense, {
		"action": {"risk": "high"},
		"delegation": {"scopes": [], "per_tx_limit": 500000},
		"args": {"amount": 999999999},
	})
	inp := json.remove(inp0, [["delegation", "expires_at"]])
	d := decide(inp)
	d == {"result": "deny", "reason": "invalid_input"}
}

test_out_of_scope_beats_approval if {
	inp := object.union(base_lookup, {"action": {"risk": "high"}, "delegation": {"scopes": []}})
	d := decide(inp)
	d == {"result": "deny", "reason": "action_not_in_scope"}
}

test_over_limit_beats_approval if {
	inp := object.union(base_expense, {"action": {"risk": "high"}, "args": {"amount": 500001}})
	d := decide(inp)
	d == {"result": "deny", "reason": "per_tx_limit_exceeded"}
}

test_expired_beats_approval if {
	inp := object.union(base_lookup, {"action": {"risk": "high"}, "delegation": {"expires_at": "2026-09-24T00:00:00Z"}})
	d := decide(inp)
	d == {"result": "deny", "reason": "delegation_expired"}
}

test_default_is_deny_when_no_rule_matches if {
	d := authz.decision with input as base_lookup
		with time.now_ns as fixed_now_ns
		with data.broker.authz.allow_ok as false
	d == {"result": "deny", "reason": "no_matching_rule"}
}

# E. 안전선 -- 결과만 확인 (3)

test_over_limit_never_allowed if {
	every amt in [500001, 1000000, 1000000000000] {
		inp := object.union(base_expense, {"delegation": {"per_tx_limit": 500000}, "args": {"amount": amt}})
		d := decide(inp)
		d.result == "deny"
	}
}

test_external_mail_never_allowed if {
	every to in [
		["x@partner.example.net"],
		["a@example.com", "x@partner.example.net"],
		["X@PARTNER.EXAMPLE.NET"],
		["a@example.com", "b@example.com", "x@partner.example.net"],
	] {
		inp := object.union(base_mail, {"args": {"to": to}})
		d := decide(inp)
		d.result == "deny"
	}
}

test_out_of_scope_never_allowed if {
	every scopes in [["expense.create"], [], ["customer"]] {
		inp := object.union(base_lookup, {"delegation": {"scopes": scopes}})
		d := decide(inp)
		d.result == "deny"
	}
}

# F. 출력 형식 (1)

decision_shape_ok(d) if {
	object.keys(d) == {"result", "reason"}
	d.result in {"allow", "deny", "require_approval"}
	is_string(d.reason)
	d.reason != ""
}

test_decision_shape if {
	d1 := authz.decision with time.now_ns as fixed_now_ns
	decision_shape_ok(d1)

	d2 := decide(base_lookup)
	decision_shape_ok(d2)

	d3 := decide(object.union(base_lookup, {"action": {"risk": "high"}}))
	decision_shape_ok(d3)

	d4 := decide(object.union(base_expense, {"args": {"amount": 500001}}))
	decision_shape_ok(d4)

	d5 := decide(object.union(base_lookup, {"agent": 1}))
	decision_shape_ok(d5)
}

# G. 허용 -- 마지막에 쓴다 (6)

test_low_risk_in_scope_allowed if {
	d := decide(base_lookup)
	d == {"result": "allow", "reason": "low_risk_in_scope"}
}

test_expense_at_limit_allowed if {
	inp := object.union(base_expense, {"delegation": {"per_tx_limit": 500000}, "args": {"amount": 500000}})
	d := decide(inp)
	d == {"result": "allow", "reason": "low_risk_in_scope"}
}

test_expense_demo_180000_allowed if {
	d := decide(base_expense)
	d == {"result": "allow", "reason": "low_risk_in_scope"}
}

test_mail_internal_recipients_allowed if {
	inp := object.union(base_mail, {"args": {"to": ["kim@example.com", "LEE@EXAMPLE.COM"]}})
	d := decide(inp)
	d == {"result": "allow", "reason": "low_risk_in_scope"}
}

test_not_expired_boundary_allowed if {
	inp := object.union(base_lookup, {"delegation": {"expires_at": "2026-09-25T00:00:00Z"}})
	d := authz.decision with input as inp with time.now_ns as (fixed_now_ns - 1)
	d == {"result": "allow", "reason": "low_risk_in_scope"}
}

test_extra_top_level_field_ignored if {
	d1 := decide(object.union(base_lookup, {"trace_id": "t-1"}))
	d1 == {"result": "allow", "reason": "low_risk_in_scope"}

	d2 := decide(object.union(base_lookup, {"action": {"risk": "high"}, "approved": true, "approval_id": "a-1"}))
	d2 == {"result": "deny", "reason": "approval_required_high_risk"}
}
