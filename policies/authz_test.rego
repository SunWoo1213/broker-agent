package broker.authz_test

import data.broker.authz

test_default_deny if {
	authz.decision.result == "deny" with input as {}
}
