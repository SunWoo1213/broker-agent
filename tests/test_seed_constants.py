"""단위: 시드 상수 F-D4 · F-D5 (U16-U21). 서비스 불필요."""

from __future__ import annotations

import re

from control.db.seed import AGENT, DELEGATIONS, TOOL_ACTIONS

ACTION_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
VALID_RISKS = {"low", "medium", "high"}

FD5_MAIL_SEND_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["to", "subject", "body"],
    "additionalProperties": False,
}


def test_seed_action_names_are_dotted_and_risks_valid():
    assert len(TOOL_ACTIONS) == 4
    for action in TOOL_ACTIONS:
        assert ACTION_NAME_RE.match(action["name"]), action["name"]
        assert action["risk"] in VALID_RISKS, action["name"]


def test_seed_emails_are_example_com():
    for delegation in DELEGATIONS:
        assert delegation["user_id"].endswith("@example.com"), delegation["user_id"]


def test_seed_mail_send_args_schema_matches_fd5():
    mail_send = next(a for a in TOOL_ACTIONS if a["name"] == "mail.send")
    assert mail_send["args_schema"] == FD5_MAIL_SEND_SCHEMA


def test_seed_scopes_are_subset_of_action_names():
    action_names = {a["name"] for a in TOOL_ACTIONS}
    for delegation in DELEGATIONS:
        for scope in delegation["scopes"]:
            assert scope in action_names, scope


def test_seed_expense_create_risk_is_low():
    expense_create = next(a for a in TOOL_ACTIONS if a["name"] == "expense.create")
    assert expense_create["risk"] == "low"


def test_seed_agent_is_suspended():
    assert AGENT["status"] == "suspended"
