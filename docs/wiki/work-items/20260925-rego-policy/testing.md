# 테스트 기록 — 4. 정책 (Rego) (작업 D)

> 요약
> - 결론: 사이클1 APPROVE(`opa test` 53/53, pytest 13개, flaky 없음), 사이클2 APPROVE(`opa test` 54/54, AC0–AC9 전부 `0 bad`). `evidence.py --verify`는 위키 복사본 기준 268개 전부 "일치".
> - 바뀐 것: 새 Rego 테스트 54개(`policies/authz_test.rego`, 계획 53 + 사이클2에서 `test_mail_subject_body_required_denied` 1개), 새 정적 pytest 2개(S1·S2, `tests/test_policy_static.py`), 변이 확인 25종(a–y).
> - 다음에 알아야 할 것: **종료 코드는 MANIFEST의 `exit` 열로 통일한다.** COMBINED 명령 안쪽의 `exit_opa`·`exit_pytest`는 이 문서에서 별도로 이름을 붙여 적는다(03-build-notes.c2.md 표가 두 기준을 한 열에 섞어 적은 것을 여기서는 분리했다). 변이 n·r·u의 초과 FAIL은 "관측값"이며 채점 대상이 아니다.

## 요약

| 회차 | 판정 | pytest (통과/실패/건너뜀) | opa test (PASS/FAIL) | flaky | 공격 평가 |
|---|---|---|---|---|---|
| 사이클1 | APPROVE | 13 / 0 / 0 | 53 / 0 | 없음(새 파일 3회 반복 동일) | 해당 없음(1단계, 공격 평가는 3단계) |
| 사이클2 | APPROVE | 13 / 0 / 0 | 54 / 0 | 없음(새 테스트 포함 54개 3회 반복 동일) | 해당 없음 |

## 테스트 설계 (01-plan.r2.md)

| 테스트 | 종류 | 검증하는 것 | 완료 조건 | 관련 원칙 |
|---|---|---|---|---|
| `authz_test.rego` A(23) | 정책(opa test) | 입력 계약 fail-closed — input 없음/비객체, 필드 누락 10종, 타입 오류 각 필드 | AC1 | 1 |
| `authz_test.rego` B(9) | 정책 | 거부 규칙 — 범위 밖, 만료, 건당 한도 초과, 인자 오류 | AC1 | 1 |
| `authz_test.rego` C(6) | 정책 | 승인 경로 — 1단계는 `deny` (위험도 높음/중간, 외부 수신자) | AC1 | 1 |
| `authz_test.rego` D(5) | 정책 | 우선순위 — 거부 > 승인 > 허용, 기본값 | AC1 | 1 |
| `authz_test.rego` E(3) | 정책, 안전선 | 규칙 하나가 약해져도 결과는 거부로 남는지(이중 방어) | AC1 | 1 |
| `authz_test.rego` F(1) | 정책 | 출력 형식 — 키 정확히 2개, result 값 집합, reason 비어있지 않음 | AC1 | 5 |
| `authz_test.rego` G(6) | 정책 | 허용 — 위험도 낮음+범위 안, 한도 경계, 만료 경계, 알 수 없는 필드 무시 | AC1 | — |
| `test_mail_subject_body_required_denied`(사이클2 추가) | 정책 | `mail.send`의 subject·body 필수(계약으로 승격, K10) | AC1(사이클2) | 1 |
| 변이 a–u(21종, 사이클1) + v·w·x·y(4종, 사이클2) | 정책, 의존성 없는 회귀 | 계획 문장을 깨는 코드 변경마다 정해진 테스트가 실패하는지(red) 확인 후 되돌림(green) | AC4 | 1, 7 |
| `test_policy_default_lines_are_deny_only`(S1) | 정적 검사(pytest) | `default` 줄은 전부 거부 쪽(원문 그대로이거나 `:= false`)인지 | AC3 | 1 |
| `test_policy_has_no_runtime_env_or_network_builtins`(S2) | 정적 검사(pytest) | `opa.runtime`·`http.send`·`net.*` 금지(개발용 우회 스위치 차단) | AC3 | 1, 2 |

## 사이클 1 — APPROVE

### 환경

- 작업 트리: `git rev-parse --short HEAD` = `7a40f19`. `git status --porcelain`: ` M docs/decisions.md`, ` M policies/authz.rego`, ` M policies/authz_test.rego`, `?? tests/test_policy_static.py` (`evidence/163-ac0-env.log`).
- 서비스: `docker compose ps` — postgres·redis·opa 모두 healthy, OPA `openpolicyagent/opa:1.20.2`.
- 도구: `.venv/Scripts/python --version` = 3.13.7, Docker 서버 29.3.0.

### ③ 구현이 대응한 테스트 (03-build-notes.md · .r2.md)

- ③은 계획한 53개 테스트를 A→G 순서로 작성했고, `policies/authz.rego`를 골격대로 구현해 첫 시도(`build-green-initial`)에서 53/53을 통과시켰다.
- **변이 u(허용 분기 출력에 키 추가) red를 실행하던 중, 계획이 정의한 "완전 비교" 표기를 지키지 않는 46개 테스트를 발견**하고 그중 변이 u가 드러낸 2개(G1)만 완전 비교로 고쳤다. 테스트 파일이 바뀌어 baseline을 다시 잡고 변이 21종을 처음부터 재실행했다.
- ④ 구현 검증 1차 REVISE(지적1)로, ③은 나머지 44개도 전부 완전 비교(`d == {"result": X, "reason": Y}`)로 강화했다(46개 전체). 재실행 결과 변이 m(exact 8개)·p(exact 1개)는 그대로, 변이 u의 FAIL 집합은 2개→7개(G그룹 전체+`test_decision_shape`)로 늘었으나 계획이 요구하는 부분집합을 포함해 통과.
- 03-build-notes.r2.md의 자체 오기 정정: "로그 94개 전부 일치" → 실제 **93개**(MANIFEST 94행은 헤더 1 + 93).

### 실행한 명령과 결과 (⑤ AC0–AC8)

```
$ docker compose run --rm opa test /policies -v
PASS: 53/53
$ .venv/Scripts/python -m pytest -q
13 passed
```

- `opa test` 53/53을 3회 반복(AC1·AC2-2·AC2-3) — 매번 같은 이름 집합, 전부 PASS.
- `tests/test_policy_static.py`(S1·S2)만 3회 추가 반복 — 매번 `2 passed`, flaky 없음.

### 완료 조건 대조 (사이클1)

| AC | 내용 | 확인한 명령/스크립트 | 결과 | 증거 |
|---|---|---|---|---|
| AC0 | 환경·기준선·D18 선반영 | ENV 명령 → `ac0_env.py` | 통과, `11 ok, 0 bad` | [evidence/163-ac0-env.log](evidence/163-ac0-env.log), [164-ac0-check.log](evidence/164-ac0-check.log) |
| AC1 | `opa test` 53개 전부 통과 | CI 명령 → `check_opa.py` | 통과, `PASS: 53/53`, `6 ok, 0 bad` | [165](evidence/165-ac1-opa-test.log), [166](evidence/166-ac1-check.log) |
| AC2 | 반복해도 같음 | CI 명령 2회 반복 | 통과, 3회 모두 동일 이름 집합, `19 ok, 0 bad` | [167](evidence/167,168-ac2-opa-2.log), [169](evidence/169-ac2-check.log) |
| AC3 | pytest 전체(S1·S2 포함) | `check_junit.py` | 통과, `13 passed`, xml 해시 대조 포함 `5 ok, 0 bad` | [170](evidence/170-ac3-pytest.log), [171](evidence/171-ac3-junit.log) |
| AC4 | ③ 증거(실패 먼저·변이·되돌림) | `ac_build_evidence.py` | 통과, `253 ok, 0 bad` | [172](evidence/172-ac4-build-evidence.log) |
| AC5 | D18 계약 주석 | `grep -n "D18" policies/authz.rego` | 통과, 2줄 매치 | [173](evidence/173-ac5-contract-comment.log) |
| AC6 | 범위 준수 | `ac_scope.py` | 통과, `8 ok, 0 bad`. 계획한 3줄 외 없음, 사람 변경 6줄은 HUMAN 처리 | [174](evidence/174-ac6-scope.log) |
| AC7 | 금지 명령 미실행 | `ac_forbidden_commands.py` | 통과, `2 ok, 0 bad` | [175](evidence/175-ac7-forbidden.log) |
| AC8 | 증거 무결성 | `evidence.py --verify` | 통과, 179개 전부 "일치" | [176](evidence/176-ac8-verify.log), [180](evidence/180-ac8-verify-final.log) |

## 사이클 2 — APPROVE

### 환경

- 작업 트리: `git rev-parse --short HEAD` = `7a40f19`, `git status --porcelain`은 사이클1과 동일 4줄.
- 서비스: postgres·redis·opa 모두 healthy(opa 이미지 동일).
- 정책 파일 해시: `policies/authz.rego` = `e2acae27…`(사이클1 기준선과 동일, 사이클2 내내 불변), `policies/authz_test.rego` = `22217c68…`(54개로 확장).

### ③ 구현 노트 (03-build-notes.c2.md) — 세션 중단 후 변이 m부터 재개

- 테스트 1개 추가(`test_mail_subject_body_required_denied`, subject·body 없음/타입 오류 6경우, 완전 비교)와 변이 4종(v·w·x·y)은 이전 세션에서 절차 1–3(env·테스트 추가·baseline) + 변이 a–l까지 끝났고, 이 세션은 **변이 m부터** 이어서 진행했다(세 파일 해시가 이전 baseline과 일치함을 재확인 후 시작).
- **환경 문제(evidence.py 밖 조치):** 변이 m red를 처음 실행할 때 Docker Desktop이 꺼져 있어 OPA 연결이 실패했다(로그 211, 무효). Docker Desktop을 기동한 뒤 재실행(로그 212, 유효)했다.
- **작업 중 편집 실수(자체 발견·자체 수정):** 변이 s(개발용 우회 스위치)를 되돌리는 Edit에서 파일 끝 개행 문자까지 함께 지워져 되돌린 직후 해시가 기준선과 달랐다(`bdf19fdd…`). `git diff`로 원인을 확인하고 `printf '\n' >> policies/authz.rego`로 개행 1글자를 복원해 기준선(`e2acae27…`)으로 되돌렸다.
- **변이 n·r·u에서 계획의 부분집합보다 많은 FAIL(관측값, 채점 대상 아님):** `plan_tests.py`는 n·r·u에 `exact`를 지정하지 않아 "계획한 테스트가 FAIL에 포함되는지"만 채점한다. 실측:
  - n: 계획 3개(부분집합) + 초과 2개(`test_invalid_input_beats_other_reasons`, `test_mail_invalid_recipients_denied`) = **5개**
  - r: 계획 1개 + 초과 2개(`test_expense_zero_limit_denies_any_amount`, `test_over_limit_beats_approval`) = **3개**
  - u: 계획 2개 + 초과 5개(G그룹 나머지 + `test_extra_top_level_field_ignored`) = **7개**
  - 사이클1 재확인 로그(137·145·151)와 사이클2 로그(214·222·228)의 FAIL 이름 집합이 완전히 동일하며, 안전선(`test_over_limit_never_allowed` 등)은 계속 PASS — 허용으로 뒤집힌 것은 없다. 이 값은 **F-D8에서 다음 작업이 실행 전에 손 추적으로 exact 집합을 고정할 때 대조용으로만** 쓴다(관측값을 기대값으로 옮겨 적으면 원칙 7 위반).

### 변이별 결과 (사이클2, 라벨 `build-mut-<x>-red/green`)

| 변이 | 지키는 문장 | exact | FAIL 집합 | 결과 |
|---|---|---|---|---|
| m | 1단계 승인 경로는 `deny` | exact(8) | 8개, 이름 정확히 일치 | 통과 |
| n | 거부(1–5) > 승인(6–8) 우선순위 | 아님 | 5개(계획 3 + 관측값 2) | 통과(부분집합 충족) |
| o | 만료 판정 `>=` 경계 | 아님 | 1개, 일치 | 통과 |
| p | 실제 시각에 기대지 않음 | exact(1) | 1개, 일치 | 통과 |
| q | 허용 쪽 오타 = 거부로 닫힘 | 아님 | 2개, 안전선 PASS 유지 | 통과 |
| r | 거부 쪽 오타여도 허용 안 됨 | 아님 | 3개(계획 1 + 관측값 2) | 통과(안전선 PASS) |
| s | 개발용 우회 스위치 금지 | 아님(pytest_fail) | opa 54/54, pytest S2만 실패 | 통과 |
| t | 빈 수신자 목록 경계 | 아님 | 1개, 일치 | 통과 |
| u | 출력 키는 정확히 2개 | 아님 | 7개(계획 2 + 관측값 5) | 통과(부분집합 충족) |
| v | subject·body 필수(body 제거) | exact(1) | 1개, 일치 | 통과 |
| w | 같음(subject 제거) | exact(1) | 1개, 일치 | 통과 |
| x | "완전히 같음"이 거부 분기 전체에 걸림 | exact(37) | 37개, 이름 정확히 일치 | 통과 |
| y | 같은 표기가 승인 분기 전체에 걸림 | exact(7) | 7개, 이름 정확히 일치 | 통과 |

무효 로그: **211**(`build-mut-m-red` 1차, Docker Desktop 꺼짐, `exit=1`이지만 OPA가 실행되지 않은 무효 실행) · **248**(`review-c2-probe-subject-body-weak` 1차, ④ reviewer의 Git Bash 경로 변환 실패). 같은 라벨의 **212**·**249**가 각각 유효한 재실행이며, 채점(`_ev.last()`)은 라벨의 마지막 로그를 보므로 무효 로그는 판정에 영향이 없다.

### 완료 조건 대조 (사이클2, AC0–AC9)

| AC | 내용 | 결과 | 증거 |
|---|---|---|---|
| AC0 | 환경·기준선·D18 선반영 | 통과, `11 ok, 0 bad` | [250](evidence/250-ac0-env.log), [251](evidence/251-ac0-check.log) |
| AC1 | `opa test` 53개(+사이클2 추가 1)=54개 전부 통과 | 통과, `PASS: 54/54`, `6 ok, 0 bad` | [252](evidence/252-ac1-opa-test.log), [253](evidence/253-ac1-check.log) |
| AC2 | 반복해도 같음 | 통과, 3회 모두 `54/54` 동일 집합, `19 ok, 0 bad` | [254](evidence/254-ac2-opa-2.log), [255](evidence/255-ac2-opa-3.log), [256](evidence/256-ac2-check.log) |
| AC3 | pytest 전체 | 통과, `13 passed`, `5 ok, 0 bad` | [257](evidence/257-ac3-pytest.log), [258](evidence/258-ac3-junit.log) |
| AC4 | ③ 증거(변이 되돌림 포함) | 통과, `253 ok, 0 bad` | [259](evidence/259-ac4-build-evidence.log) |
| AC5 | D18 계약 주석 | 통과, 2줄 매치 | [260](evidence/260-ac5-contract-comment.log) |
| AC6 | 범위 준수 | 통과, `8 ok, 0 bad`. HUMAN 줄 정확히 1줄(`docs/decisions.md`, K10 D18 보강) | [261](evidence/261-ac6-scope.log) |
| AC7 | 금지 명령 미실행 | 통과, `2 ok, 0 bad` | [262](evidence/262-ac7-forbidden.log) |
| AC8 | 증거 무결성 | 통과, 264개 전부 "일치" | [263](evidence/263-ac8-verify.log), [265](evidence/265-ac8-verify-final.log) |
| AC9 | 사이클2 증거(`checks_c2/c2_evidence.py --require-ac1`) | 통과, `44 ok, 0 bad`. v–y exact, m·p exact 재확인, 사이클2 내내 정책 해시 불변 | [264](evidence/264-ac9-c2-evidence.log) |

### AC6 HUMAN 1줄 판정

`ac_scope.py` 출력에 `HUMAN rule4: protected files unchanged: 'docs/decisions.md'` 정확히 1줄이 나왔다(K10 A안 승인에 따라 메인 세션이 사이클2 ③ 시작 전에 D18 상세 문장을 교체한 것). `00-approval.md`의 해당 표 행 시각(2026-09-25 19:36)이 사이클2 첫 증거 `build-c2-env`(19:38:16)보다 앞이라, 결과를 보고 나중에 표를 채운 것이 아니라 사전에 기록됐음을 확인했다.

### 종료 코드 정리 (H10 반영 — MANIFEST `exit`로 통일)

03-build-notes.c2.md의 자기 점검 표는 evidence.py의 종료 코드(MANIFEST `exit`)와 COMBINED 명령 안쪽의 `exit_opa`를 한 열에 섞어 적었다(m·o·s·t·u·v·w·x·y는 MANIFEST `exit`=1, n·p·q·r은 `exit_opa`=2를 적음). 이 문서에서는 **MANIFEST `exit`만 "종료 코드"로 쓰고, 안쪽 값은 별도로 이름을 붙여 적는다.** 실제 MANIFEST `exit`는 red 로그 26개(무효 2개 포함) 전부 1, green·자기 점검·AC 로그는 전부 0이다. `exit_opa`는 opa test가 FAIL을 낼 때 2, 컴파일 오류 등에서는 다른 값이 될 수 있다.

### 증거 무결성 (최종 재확인 — 위키 복사본)

`docs/wiki/work-items/20260925-rego-policy/evidence/`로 run 폴더의 `evidence/`를 통째로 복사(MANIFEST.tsv 포함, 파일 내용 수정 없음)한 뒤 재검증했다.

```
$ .venv/Scripts/python .claude/tools/evidence.py docs/wiki/work-items/20260925-rego-policy --verify
... (268줄)
일치   268-review-c2i-bytes-and-sort.log  (exit=0, 2026-09-25T22:25:41+09:00)
```

268개 로그 전부 "일치", "변조됨"·"없음" 0건(MANIFEST.tsv 269행 − 헤더 1 = 268행과 일치). 로그에 비밀 값(토큰·비밀번호·키) 검색 결과 없음을 복사 전에 확인했다.

## 완료 조건 대조 (전체)

| AC | 내용 | 확인한 테스트 | 결과 |
|---|---|---|---|
| AC0–AC8 | `01-plan.r2.md` 원문 | 사이클1·사이클2 두 번 모두 실행 | 전부 통과 |
| AC9 | `06-improvement-plan.r3.md`(사이클2 코드 수정안) | `checks_c2/c2_evidence.py --require-ac1` | 통과 |

## 실패 상세

없음. 모든 AC가 계획·개선 계획이 정한 명령·기대값 그대로 통과했다.
