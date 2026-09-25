# 4. 정책 (Rego) — 작업 D

> 요약
> - 결론: 완료 (커밋 d9b6b16, GitHub Actions opa-test · pytest 성공). `opa test` 54개(계획 53 + 개선 사이클 2에서 1개 추가) · 정적 pytest 2개 · 변이 25종(a–y) 전부 통과, `evidence.py --verify` 268개 전부 "일치".
> - 바뀐 것: `policies/authz.rego`(D18 계약 정책 새로 작성) · `policies/authz_test.rego`(54개) · `tests/test_policy_static.py`(새 파일, S1·S2) · `docs/decisions.md`(D18 확정) · `docs/plan.md` · `docs/stage1-plan.md` · `README.md`.
> - 다음에 알아야 할 것: 변이 n·r·u의 초과 FAIL(관측값, F-D8에서 사전 추적 후 확정 예정), evidence 로그의 자식 Python 한국어 출력이 cp949로 깨지는 문제(2026-09-25 H13으로 해결, 그 전 로그는 깨진 채 보존), 하네스 개선안 H1–H14는 2026-09-25 전부 반영, 후속 F-D1–F-D8은 `docs/plan.md` 해당 작업 아래에 등록(F-D9 완료).

| 날짜 | plan.md 항목 | 결과 | 관문 재시도 | 개선 사이클 |
|---|---|---|---|---|
| 2026-09-25 | 1단계 4. 정책 (Rego) (작업 D) | 완료 | ② 1회(REVISE→APPROVE) · ④ 사이클1 1회(REVISE→APPROVE) · ⑤ 사이클1 0회(APPROVE) · ⑦ 사이클1 2회(REVISE→REVISE→APPROVE, r3에서 K10 A안 승인) · 사이클2: ④ 0회(APPROVE) · ⑤ 0회(APPROVE, AC0–AC9) · ⑦ 0회(APPROVE) | 2회 |

## 1. 목표

`docs/plan.md` 1단계 "4. 정책 (Rego)" 체크박스 5개(기본값 거부 / 위험도 낮음 + 위임 범위 안 → 허용 / `expense.create` 건당 한도 초과 → 거부 / 위험도 높음 → 승인 필요(1단계는 거부) / 규칙별 `opa test`)를 구현한다. 관련 불변 원칙: 1(fail-closed, 정책이 게이트웨이 오류와 무관하게 스스로 거부한다), 2(자격 증명 비노출 — 정책은 토큰을 다루지 않음), 4(누적 한도, 이 작업은 건당 한도만), 5(감사 로그, 이 작업 밖), 7(재현 가능한 채점 — 변이·개선 사이클에서 반복 확인).

## 2. 설계와 결정

- **입력·출력 계약 D18**을 이 작업의 계획 승인과 동시에 사용자가 승인했다(`docs/decisions.md` D18). 정책은 `input`만 보고 DB·목(mock)을 쓰지 않는다.
- **승인 경로(위험도 높음/중간, 메일 외부 수신자)는 1단계에서 `require_approval`이 아니라 `deny`로 낸다(K7).** 이유: 게이트웨이(작업 I)가 아직 없어 `require_approval`을 내면 아직 없는 코드 한 줄에만 안전이 달리기 때문. 2단계 8번에서 상수 `approval_result` 한 줄만 바꾸면 되도록 설계했다.
- **거부(1–5) > 승인 경로(6–8) > 허용(9)** 순서를 `else` 체인으로 명시적으로 구현했다. 허용 조건(`allow_ok`)은 양성 조건의 AND만 쓰고 부정(`not`)을 쓰지 않는다 — 오타·undefined가 나면 항상 기본 거부(닫히는 방향)로 떨어지게 하기 위해서다.
- **알 수 없는 최상위 필드는 무시한다(K8)** — 이 작업의 유일한 "관대한 쪽" 결정. 정책이 읽는 필드가 고정돼 있어 모르는 필드로 허용이 생기지 않음을 테스트(`test_extra_top_level_field_ignored`)로 확인했다.
- **개선 사이클 1에서 추가된 결정: `mail.send`의 `subject`·`body`를 문자열로 필수화(K10, A안).** 구현(③)이 계획에 없던 이 규칙을 넣었는데 거부 테스트가 없었다(04 지적 2). 검토 끝에 "규칙을 계약으로 올리고 거부 테스트·변이를 더한다"(A안)를 사용자가 승인했다. 대안 B(규칙 삭제)는 현재 구현보다 느슨해져 채택하지 않았다.
- 검토했지만 버린 대안: 승인 경로를 지금부터 `require_approval`로 내는 안(D18 출력 계약을 1단계부터 채우지만, 게이트웨이가 없어 이중 방어 효과가 작음 — 채택 안 함).
- decisions.md에 추가한 항목: **D18**(입력·출력 계약, 표 줄 + "D18 상세" 절, `mail.send` 필수 문구는 개선 사이클 2에서 보강).

> 검증 상세: [verification.md](verification.md) · 테스트 상세: [testing.md](testing.md)

## 3. 진행 기록

| 단계 | 판정 | 요지 |
|---|---|---|
| ② 계획 검증 | REVISE(1차) → APPROVE(r2) | 1차: 변이 m의 실패 목록이 5개로 적혀 있었으나 실제로는 8개(C4·C5·G6 누락), junit xml이 해시 보호 밖. r2에서 `exact=True`·`verified_junit()` 추가로 반영 |
| ④ 구현 검증 (사이클1) | REVISE(1차) → APPROVE(r2) | 1차: 46개 테스트가 계획이 정의한 "완전 비교"가 아니라 "필드 개별 비교"로 구현돼 있어 키 추가 변이(u)를 한 곳만 잡음. r2에서 46개를 완전 비교로 강화 |
| ⑤ 테스트 (사이클1) | APPROVE | AC0–AC8 전부 통과, `opa test` 53/53, pytest 13개, flaky 없음, `--verify` 179개 일치 |
| ⑥ 개선사항 계획 (사이클1) | "코드 수정 필요" → 사이클2 | `mail.send` 필수화 규칙에 거부 테스트가 없음(04 지적 2) + (a)의 근본 원인(비교 형태 누락)을 영구 증거(변이 x·y)로 승격 |
| ⑦ 개선 계획 검증 (사이클1) | REVISE(1차) → REVISE(r2) → APPROVE(r3) | 1·2차 REVISE 사유: K10 승인 뒤 decisions.md 보강을 "마무리"로 미룬 것이 규칙(`work-item/SKILL.md`, CLAUDE.md)과 어긋남 → r3에서 grep 패턴을 `K10(A`로 좁혀 반영. K10 A안 사용자 승인 |
| ③④⑤ (사이클2) | 세션 중단 후 변이 m부터 재개 → ④ APPROVE · ⑤ APPROVE | 테스트 1개(`test_mail_subject_body_required_denied`) + 변이 v·w·x·y 추가, 정책 불변(`e2acae27…`) |
| ⑥ 개선사항 계획 (사이클2) | "코드 수정 없음" | 변이 n·r·u 초과 FAIL, 종료 코드 열 혼동, 개행 삭제 실수, Docker 꺼짐/경로변환 무효 로그, cp949 인코딩 — 전부 후속·하네스로 이관, 원칙 7 위반 방지 위해 채점 기준은 고치지 않음 |
| ⑦ 개선 계획 검증 (사이클2) | APPROVE | 마무리 절 실행을 승인, 문구 정정 2건 참고(cp949 바이트 오타, README 문구) |

## 4. 구현 요약

| 파일 | 변경 |
|---|---|
| `policies/authz.rego` | 새로 작성. D18 입력 계약(fail-closed) → 작업별 인자 검사 → 범위·만료·건당 한도 거부 → 승인 경로(1단계는 거부) → 허용, `else` 체인 하나. `mail.send`의 `subject`·`body` 문자열 필수(계획 밖 추가, 개선 사이클1에서 계약으로 승격) |
| `policies/authz_test.rego` | 새로 작성. 54개 테스트(계획 53 + 사이클2 `test_mail_subject_body_required_denied`). 46개는 사이클1 ④ REVISE로 완전 비교(`d == {"result": …, "reason": …}`)로 강화 |
| `tests/test_policy_static.py` | 새 파일. S1(`default` 줄은 거부 쪽만) · S2(`opa.runtime`/`http.send`/`net.*` 금지) — CI pytest job에서 실행 |
| `docs/decisions.md` | D18 표 줄 + "D18 상세" 절 추가(메인 세션, ③ 전). 사이클2에서 `mail.send` 필수 문구·검증 칸(54개·25종) 보강 |
| `docs/plan.md` · `docs/stage1-plan.md` | 4번 체크박스 5개 `[x]`, D행 상태 갱신, D18 승인 표시 |
| `README.md` | 진행 상황·정책 개요·테스트 실행 절 추가(사용자 요청) |

## 5. 테스트

- `opa test`: 54/54 PASS, 3회 반복 동일. pytest: 13 passed(정적 검사 2개 포함). flaky 없음.
- 변이 25종(a–y) 전부 red(실패)→되돌림→green(통과) 증거를 남김. 그중 m·p·v·w·x·y는 FAIL 집합이 **정확히** 일치(exact)해야 통과.
- 완료 조건: AC0–AC8(사이클1) + AC9(사이클2, `checks_c2/c2_evidence.py`)까지 전부 통과.
- 상세: [testing.md](testing.md)

## 6. 문제 상황과 해결

| 문제 | 분류 | 상태 | 상세 |
|---|---|---|---|
| 계획이 "완전 비교"로 정한 기대값 표기를, 구현이 46개 테스트에서 개별 필드 비교로 약하게 구현 | 구현 | 해결 | [링크](../../troubleshooting/ci-test-spec-quantifier-weakening.md) (재발 기록) |
| 계획 밖에 추가한 엄격한 규칙(`mail.send` subject·body 필수)에 거부 테스트가 없음 | 설계/구현 | 해결 | [링크](../../troubleshooting/strict-rule-without-deny-test.md) |
| 개선 사이클에서 사용자 승인된 설계 결정(decisions.md)을 언제 반영할지 순서가 규칙과 어긋남 | 하네스 | 해결 | [링크](../../troubleshooting/improvement-cycle-decision-timing.md) |
| evidence 로그에서 자식 Python의 한국어 출력이 cp949로 깨짐 | 하네스 | 해결 (2026-09-25, H13 적용) | [링크](../../troubleshooting/evidence-log-cp949-garbled-output.md) |
| Windows Git Bash 경로 변환 문제가 reviewer 탐침에서 재발 | 환경 | 해결 | [링크](../../troubleshooting/msys-pathconv-windows.md) (재발 기록) |
| 변이 되돌림 Edit이 파일 끝 개행 문자를 함께 지움 | 구현 | 해결 | [링크](../../troubleshooting/mutation-revert-edit-strips-trailing-newline.md) |
| 세션 재개 시 Docker Desktop이 꺼져 있어 무효 red 로그가 남음 | 환경 | 해결 | [링크](../../troubleshooting/session-resume-docker-down-invalid-red-log.md) |

## 7. 배운 점

- 계획의 "완전히 같음" 같은 표기 규칙은 **모든 테스트에 걸친 전칭 조건**이며, 그것을 깨는 변이는 출력 분기(거부·승인·허용)마다 하나씩 둬야 한다. 한 분기만 덮으면 나머지 분기는 약한 구현이 red 증거 없이 통과할 수 있다.
- 계획 밖에 규칙(더 엄격한 검사 포함)을 추가하면 그 규칙의 거부 테스트도 함께 써야 한다. "계획의 테스트 목록에 없다"는 이유로 테스트 없이 두면 안 된다.
- 개선 사이클에서 사용자 확인을 받은 설계 결정은 다음 구현(③) 시작 **전에** 반영한다. "범위 검사(AC6)의 해시 보호"는 미룰 이유가 아니라 `00-approval.md`에 사람 변경으로 기록할 대상이다.
- 결과를 본 뒤에 채점 기준(exact 집합 등)을 그 결과에 맞춰 고정하면, 더 엄격한 방향이라도 원칙 7(재현성) 위반이다. 관측값은 다음 작업의 사전 추적을 위한 대조용으로만 남긴다.
- 하네스 개선안: [`.claude/harness-notes.md`](../../../../.claude/harness-notes.md) "2026-09-25 4. 정책 (Rego) (작업 D)" 절(H1–H14, 2026-09-25 사용자 승인 · 전부 반영).

## 8. 관련

- 커밋: 대기 (마무리 뒤 커밋 승인 필요)
- 선행: 작업 A(개발 환경), 작업 B(pytest·CI)
- 후속: F-D1–F-D9(`06-improvement-plan.c2.md` 후속 항목 표), 작업 C·E·I·2단계 8번이 이 작업의 계약·값을 따른다
