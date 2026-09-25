# 계획 밖에 넣은 더 엄격한 규칙에 거부 테스트가 하나도 없음

> 요약
> - 한 줄 해결: 계획에 없는 규칙(더 엄격한 검사 포함)을 구현에 넣을 때는 그 규칙을 거부로 떨어뜨리는 테스트도 같이 쓴다. 이번에는 계약(decisions.md)으로 승격하고 거부 테스트 1개 + 변이 2종(v·w)을 추가해 해결했다.
> - 원인: 계획(01-plan.r2.md)이 `mail.send`의 허용 키 집합(`to`·`subject`·`body`)만 정하고 각 키의 필수 여부·타입은 정하지 않았다. 구현(③)이 `subject`·`body`를 문자열로 필수화하는 규칙을 스스로 추가했는데, "계획의 테스트 목록만 따른다"는 태도로 그 규칙의 거부 테스트를 쓰지 않았다.
> - 재발 방지: `agents/broker-builder.md`·`skills/code-review-invariants/SKILL.md`에 "diff에 들어간 정책 규칙마다 거부 테스트가 하나 이상 있어야 한다(A4)"는 체크 항목 추가 제안(H4, 사용자 결정 대기).

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-25 | 설계 / 구현 | 해결 | ④ 구현 검증 1차(사이클1) 지적 2 | 원칙 1 (fail-closed) |

## 증상

`policies/authz.rego:103-104`에 `is_string(input.args.subject)` · `is_string(input.args.body)`가 있어 `mail.send` 요청의 `subject`·`body`가 문자열이 아니거나 없으면 거부된다. 그런데 `policies/authz_test.rego`에서 `subject`·`body`가 나오는 곳은 `base_mail` 고정값(`subject: "s", body: "b"`) 한 곳뿐이었다. **이 거부 규칙을 시험하는 테스트가 하나도 없었다.**

```
grep -n "subject\|body" policies/authz_test.rego
34:...    "args": {"to": ["kim@example.com"], "subject": "s", "body": "b"}}
```

## 재현 방법

1. `policies/authz.rego:103-104`의 두 `is_string` 검사 중 하나를 지운다.
2. `docker compose run --rm opa test /policies -v`를 실행한다.
3. 53개 테스트가 전부 PASS로 남는다 — 이 규칙이 지워졌는데도 CI가 알아채지 못한다.

## 원인

1. 직접 원인: `authz_test.rego`에 `subject`·`body`가 없거나 타입이 틀린 경우를 다루는 테스트가 없었다.
2. 왜? → ③(구현)이 계획에 없는 규칙(더 엄격한 검사)을 정책에 추가하면서, 계획의 테스트 목록(01-plan.r2.md의 53개)만 그대로 따라 썼다. 계획에 없는 규칙은 계획의 테스트 목록에도 없으니 테스트가 안 생겼다.
3. 왜? → 계획(01-plan.r2.md 97행, D18 상세)이 `mail.send`의 허용 키 집합은 정했지만 각 키의 **필수 여부·타입**은 정하지 않았다. 입력 계약 절은 최상위 필드만 필드 단위로 정했고, 작업별 인자는 산문 한 줄뿐이었다 — 계획에 빈칸이 있으면 구현자가 채운다.
4. 근본 원인: "규칙 하나당 최소 허용 한 개 + 거부 한 개"(`rego-policy` 스킬)라는 원칙이 **테스트 작성** 규칙인데, 구현자가 이를 "계획이 정한 테스트만 옮겨 쓴다"는 태도로 좁게 해석했다. `code-review-invariants`에도 "diff에 들어간 규칙마다 거부 테스트가 있는가"를 확인하는 체크 항목이 없어, ④가 이를 검토자의 주의력으로만 잡았다(04-code-review.md 지적 2).

## 해결

거부 쪽으로 닫히는 방향(A안)을 사용자(K10)가 승인했다.

1. **D18 상세를 계약으로 보강**: "`mail.send`의 인자 키는 `to`·`subject`·`body`만 허용하고 **셋 다 필수**다. `subject`·`body`는 문자열(빈 문자열 허용)"을 `docs/decisions.md`에 추가.
2. **거부 테스트 1개 추가**: `test_mail_subject_body_required_denied` — `subject` 없음/`body` 없음/`subject: 1`/`body: null`/`subject: ["s"]`/`body: {"x": 1}` 각각 `deny/invalid_args`(완전 비교).
3. **변이 2종 추가**: v(`is_string(body)` 제거) → FAIL 정확히 `{새 테스트}`, w(`is_string(subject)` 제거) → 동일.
4. F-D5(모의 메일 도구 스키마, 후속 작업 E)를 `required: [to, subject, body]`로 갱신.

```rego
# policies/authz.rego (일부)
valid_args if {
	input.action.name == mail_send
	...
	is_string(input.args.subject)   # 이 줄이 지워지면 v/w가 잡는다
	is_string(input.args.body)
}
```

## 검증

- 변이 v·w의 red 로그(230·232)에서 새 테스트만 정확히 FAIL(`FAIL: 1/54`)함을 확인. green(231·233)에서 정책 해시가 기준선(`e2acae27…`)으로 복원됨을 확인.
- ④(사이클2) 검토자가 scratchpad 사본에서 `is_string`을 타입 검사 대신 "존재만 확인"하는 약화(변이 v·w와 다른 방식)로 탐침해도 같은 테스트가 잡음을 확인(로그 249, `FAIL: 1/54`).

## 재발 방지

- `agents/broker-builder.md` "하지 말 것"(제안, H4): "계획에 없는 규칙(더 엄격한 검사 포함)을 넣으면 03 '계획에 없던 변경'에 적고, 그 규칙의 거부 테스트를 같이 쓴다. 계획의 테스트 목록에 없다는 이유로 테스트 없이 두지 않는다."
- `skills/code-review-invariants/SKILL.md`(제안, H4): "A4 | diff에 들어간 정책 규칙·검사마다 그것이 거부로 떨어지는 테스트가 하나 이상 있다. 규칙 = 판단 결과를 바꿀 수 있는 조건 한 줄(헬퍼 내부의 중간 단계는 세지 않는다). 없으면 REVISE."

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [개요](../work-items/20260925-rego-policy/index.md) · [검증 기록](../work-items/20260925-rego-policy/verification.md)
