# 테스트 기록 — 0. 개발 환경 — pytest · CI

> 요약
> - 결론: ⑤ APPROVE. pytest 전체 `11 passed`, flaky 3회 반복 동일, opa test `PASS: 1/1`. AC0–AC14 중 14개 통과·1개(AC12)는 범위 밖 변경으로 처리. 증거 60개 전부 `--verify` "일치".
> - 바뀐 것: 이번 작업에서 처음으로 모든 AC와 ③ 자기 점검을 `evidence.py`로 실행해 로그·해시를 남기고, 판정 기준(`checks/*.py`)을 결과를 보기 전에 미리 고정했다.
> - 다음에 알아야 할 것: U1(푸시)·U2(Actions 첫 실행 결과)·U3(plan.md 체크)는 이 리포트의 AC가 아니다. 2026-09-25에 모두 끝났다 — Actions run #1 성공(증거 `62-u2-actions-result.log`).

> 관문 ⑤의 실행 기록. 근거: `.claude/runs/20260924-pytest-ci/05-test-report.md`. 숫자와 오류 메시지는 실제 출력 그대로 옮겼다(06이 아니라 05 표에서 옮김 — 06 도입부에 AC5 종료 코드 표현 오류가 있었고 ⑦이 정정했다).

## 요약

| 회차 | 판정 | pytest (통과/실패/건너뜀) | opa test (PASS/FAIL) | flaky | 공격 평가 |
|---|---|---|---|---|---|
| 1 (③ 자기 점검 + ⑤ 공식 채점, 개선 사이클 없이 1회로 종료) | APPROVE | 11 / 0 / 0 | PASS: 1/1 | 3회 반복 모두 `11 passed`, `counts=[11,11,11,11]` | 해당 없음 (이번 작업은 공격 평가 대상 아님) |

## 테스트 설계

이번 작업에서 새로 쓴 테스트와 그 의도 (계획 `01-plan.r3.md` "먼저 쓸 테스트" 절 기준).

| 테스트 | 종류 | 검증하는 것 | 완료 조건 | 관련 원칙 |
|---|---|---|---|---|
| T1 `test_async_test_without_marker_fails` | 단위(pytester 내부 세션) | 표시 없는 async 테스트가 failed=1, passed=0이고 특정 오류 메시지가 있다 | AC1·AC2 | 1 |
| T2 `test_marked_async_test_body_actually_runs` | 단위 | `@pytest.mark.asyncio` 본문이 실제로 실행된다(코루틴만 만들고 안 도는 경우 방지) | AC1·AC2 | 1 |
| T3 `test_unregistered_marker_is_error` | 단위 | 오타 마커가 수집 오류가 된다 | AC1·AC2, AC4a | 1 |
| T4 `test_unknown_ini_option_is_error` | 단위 | ini 옵션 오타가 USAGE_ERROR가 된다 | AC1·AC2 | 1 |
| T5 `test_integration_marker_not_deselected_by_default` | 단위 | 통합 테스트가 기본 실행에서 빠지지 않는다(fail-open 방지) | AC1·AC2, AC5 | 1, 7 |
| T6 `test_pytest_ini_settings` | 단위 | ini 설정값이 실제로 적용됐다 | AC1·AC2, AC4b | 1 |
| T7 `test_asyncio_smoke` | 단위(성공 경로) | async 테스트가 정상 통과한다 | AC1·AC2, AC4c | — |
| T8 `test_ci_workflow_does_not_swallow_failures` | 정책성(CI 텍스트 검사) | `ci.yml`에 실패를 삼키는 설정이 없고, **모든** job에 timeout이 있다 | AC1·AC2, AC8, AC10a | 1 |
| T9 `test_ci_workflow_actions_pinned_to_commit_sha` | 정책성 | action이 전부 40자리 커밋 SHA로 고정돼 있다 | AC1·AC2, AC11 | 7 |
| T10 `test_ci_workflow_runs_same_commands_as_local` | 정책성 | CI 명령이 로컬 명령과 글자 그대로 같다 | AC1·AC2, AC9a | 7 |
| T11 `test_ci_workflow_has_no_secrets_and_read_only_token` | 정책성 | secrets 미사용, 권한이 `contents: read` **하나뿐** | AC1·AC2, AC10b | 2 |

## 회차 1 — APPROVE

### 환경

- 저장소 루트: `C:\Portpolio\agent-broker`, git HEAD `780b009` (evidence 실행 동안 변화 없음)
- `git status --porcelain --untracked-files=all` (`ac0-env`, [evidence/35-ac0-env.log](evidence/35-ac0-env.log)): 추적 대상 변경 15개(`.claude/agents/*` 3개, `.claude/harness-notes.md`, `.claude/skills/*` 5개, `docs/wiki/_templates/*.md` 4개, `tests/README.md`), 신규(`??`) 6개. 이 작업의 "바꿀 파일" 목록과 정확히 일치하는 부분은 `.github/workflows/ci.yml`, `pytest.ini`, `tests/test_ci_workflow.py`, `tests/test_pytest_config.py`, ` M tests/README.md` 5줄뿐. 나머지는 하네스·오케스트레이터 변경
- 서비스 상태(`docker compose ps`): `postgres`(healthy), `redis`(healthy), `opa`(healthy). 이번 테스트에서 stop/start 하지 않음
- Python: `Python 3.13.7`
- 126 거부 없음, 우회 없음. 기존 증거 01–34(③·④가 남긴 것)는 건드리지 않았고 이번 실행은 35번부터 쌓임

### 실행한 명령과 결과

모두 `.venv/Scripts/python .claude/tools/evidence.py .claude/runs/20260924-pytest-ci <라벨> "<명령>"` 형태로 실행(AC0–AC14, 로그 35~59).

```
$ (ac1-pytest) .venv/Scripts/python -m pytest -q --junitxml=.../pytest-ac1-pytest.xml
exit=0, "11 passed"
$ (ac7-opa-test) docker compose run --rm opa test /policies -v
exit=0, 출력에 "PASS: 1/1"
```

### 불안정성 확인 (AC3, 새 테스트 3회 반복)

| 테스트 | 1 | 2 | 3 |
|---|---|---|---|
| 전체 스위트 (`ac3-flaky-1/2/3`) | `11 passed` | `11 passed` | `11 passed` |

`check_junit.py` 비교 결과(`ac3-compare`): `counts=[11, 11, 11, 11]`(AC1 결과 포함 4개 xml 비교), `13 ok, 0 bad` → flaky 없음.

### 완료 조건 대조

| AC | 내용 | 확인한 테스트/명령 | 결과 | 증거 |
|---|---|---|---|---|
| AC0 | 환경 기준선 | `ac0-env` | 통과 — exit 0, `checks/*.py` 8개 해시가 `build-00-env`와 동일 | [evidence/35-ac0-env.log](evidence/35-ac0-env.log) |
| AC1 | 전체 pytest(T1–T11) | `ac1-pytest` | 통과 — exit 0, `11 passed` | [evidence/36-ac1-pytest.log](evidence/36-ac1-pytest.log), `evidence/pytest-ac1-pytest.xml` |
| AC2 | 계획한 11개·실패 0 | `ac2-junit`(`check_junit.py`) | 통과 — exit 0, `4 ok, 0 bad`(missing=[], bad=[], tests=11) | [evidence/37-ac2-junit.log](evidence/37-ac2-junit.log) |
| AC3 | flaky 없음 | `ac3-flaky-1/2/3` + `ac3-compare` | 통과 — 3회 모두 exit 0, `11 passed`; compare `13 ok, 0 bad` | [evidence/38-ac3-flaky-1.log](evidence/38-ac3-flaky-1.log) ~ [41-ac3-compare.log](evidence/41-ac3-compare.log) |
| AC4a | 마커 등록 | `ac4-markers` | 통과 — exit 0, `count=1` | [evidence/42-ac4-markers.log](evidence/42-ac4-markers.log) |
| AC4b | asyncio 설정 적용 | `ac4-header` | 통과 — exit 0, 한 줄 출력(strict, loop_scope=function) | [evidence/43-ac4-header.log](evidence/43-ac4-header.log) |
| AC4c | deprecation 없음 | `ac4-no-deprecation` | 통과 — exit 0, `11 passed` | [evidence/44-ac4-no-deprecation.log](evidence/44-ac4-no-deprecation.log) |
| AC5 | 통합 테스트 0개 | `ac5-integration-none` | 통과 — exit **5**(계획 기대값), `11 deselected` | [evidence/45-ac5-integration-none.log](evidence/45-ac5-integration-none.log) |
| AC6 | ③ 증거(실패 먼저·변이 a–e·되돌림) | `ac6-build-evidence` | 통과 — exit 0, `35 ok, 0 bad` | [evidence/46-ac6-build-evidence.log](evidence/46-ac6-build-evidence.log) |
| AC7a | OPA 로컬 재현 | `ac7-opa-test` | 통과 — exit 0, `PASS: 1/1` | [evidence/47-ac7-opa-test.log](evidence/47-ac7-opa-test.log) |
| AC7b | 0건 방지 grep이 막는다 | `ac7-opa-guard-negative` | 통과 — exit 0, `rejected:` 세 줄 | [evidence/48-ac7-opa-guard-negative.log](evidence/48-ac7-opa-guard-negative.log) |
| AC8 | YAML 파싱·구조 | `ac8-workflow-structure` | 통과 — exit 0, `16 ok, 0 bad` | [evidence/49-ac8-workflow-structure.log](evidence/49-ac8-workflow-structure.log) |
| AC9a | CI 명령=로컬 명령, Python 버전 | `ac9-workflow-commands` | 통과 — exit 0, `4 ok, 0 bad` | [evidence/50-ac9-workflow-commands.log](evidence/50-ac9-workflow-commands.log) |
| AC9b | 로컬에서 새로 안 깔림 | `ac9-local-install` | 통과 — exit 0, `Successfully installed` 없음 | [evidence/51-ac9-local-install.log](evidence/51-ac9-local-install.log) |
| AC9c | `pip check` | `ac9-pip-check` | 통과 — exit 0, `No broken requirements found.` | [evidence/52-ac9-pip-check.log](evidence/52-ac9-pip-check.log) |
| AC10a | 실패 무시·비밀 참조 없음 | `ac10-no-swallow` | 통과 — exit 0, 출력 없음(매치 없음) | [evidence/53-ac10-no-swallow.log](evidence/53-ac10-no-swallow.log) |
| AC10b | checkout 토큰 미보존 | `ac10-persist-cred` | 통과 — exit 0, `count=2` | [evidence/54-ac10-persist-cred.log](evidence/54-ac10-persist-cred.log) |
| AC11 | action SHA=릴리스 커밋 | `ac11-action-shas` | 통과 — exit 0, `6 ok, 0 bad` | [evidence/55-ac11-action-shas.log](evidence/55-ac11-action-shas.log) |
| AC12 | 범위 준수 | `ac12-scope` | **BAD(예견됨, 실패로 안 셈)** — exit 1, `14 ok, 1 bad`. 아래 "AC12 상세" 참고 | [evidence/56-ac12-scope.log](evidence/56-ac12-scope.log) |
| AC13 | 금지 명령 미실행 | `ac13-forbidden-commands` | 통과 — exit 0, `2 ok, 0 bad`(logs checked: 56) | [evidence/57-ac13-forbidden-commands.log](evidence/57-ac13-forbidden-commands.log) |
| AC14 | xml 해시 고정·무결성 | `ac14-xml-hashes` + `ac14-verify` | 통과 — 둘 다 exit 0. verify: 로그 01–58 전부 `일치` | [evidence/58-ac14-xml-hashes.log](evidence/58-ac14-xml-hashes.log), [evidence/59-ac14-verify.log](evidence/59-ac14-verify.log) |

### AC12 상세 (예견된 BAD, 실패로 치지 않음)

`checks/ac12_scope.py`가 낸 유일한 BAD:

```
BAD added lines == planned 5: unexpected=[
  ' M docs/wiki/_templates/testing.md',
  ' M docs/wiki/_templates/troubleshooting.md',
  ' M docs/wiki/_templates/verification.md',
  ' M docs/wiki/_templates/work-item-index.md'
] missing=[]
```

`00-approval.md` "작업 중 사람이 한 변경" 표의 22:47 행과 BAD 4줄(파일명·개수)이 정확히 일치 → 사용자 지시에 따른 오케스트레이터 변경(작업 범위 밖)으로 처리하고 실패로 세지 않는다. "no baseline line disappeared"(`[]`)와 보호 파일 12개 해시 불변은 통과이며, 표에 없는 예상 밖 변경은 없었다.

### 변이 f/g/h (표 밖 추가 증거, ④ r2에서 확인)

계획 표(a–e)에는 없는 변이. `ac6_build_evidence.py`의 MUTATIONS는 a–e만 알기 때문에 `ac6-build-evidence`가 f/g/h를 채점하지 않는다(BAD도 안 냄). ④ r2(`04-code-review.r2.md` D2행)가 세 변이(f: `permissions:` 확장, g: `timeout-minutes` 누락 job, h: OPA grep 약화) 모두 "red가 의도한 테스트·이유로 정확히 실패하고, green에서 baseline 해시로 완전히 복원됨"을 확인해 APPROVE 판정을 냈다. ⑤는 이 인용으로 대신하고 별도 재실행은 하지 않았다.

### 완료 조건 대조 (요약)

AC0–AC14 전부 위 표에 있다. U1–U3(푸시, Actions 결과, `plan.md` 체크)은 이 리포트의 AC가 아니며 계획 296–326줄에 따라 커밋 승인 → 사용자 승인 뒤 오케스트레이터가 진행한다. 이번 ⑤ 실행에서는 손대지 않았다.

### 실패 상세

실패한 AC 없음. AC12는 "BAD"가 났지만 근거를 대며 계획이 사전에 예견하고 `00-approval.md`에 기록된 오케스트레이터 변경(작업 범위 밖)이라 실패로 세지 않았다.

→ 관련 문제 해결 페이지: [ci-test-spec-quantifier-weakening.md](../../troubleshooting/ci-test-spec-quantifier-weakening.md)(④ 1차 REVISE 원인), [evidence-tool-permission-bypass.md](../../troubleshooting/evidence-tool-permission-bypass.md)(evidence.py 권한 필터)

## 증거 보존

`.claude/runs/20260924-pytest-ci/evidence/`(로그 60개 + `MANIFEST.tsv` + junit xml)를 통째로 `docs/wiki/work-items/20260924-pytest-ci/evidence/`로 복사했다(내용 수정 없음). 복사 전 로그·xml·raw 파일에서 비밀 값(AWS 키 패턴, GitHub 토큰 패턴, PEM 헤더, `password=`/`secret=`, Bearer 토큰) 검색을 했고 일치하는 것이 없어 그대로 복사했다("token"이라는 단어가 있는 3곳은 테스트 이름(`test_ci_workflow_has_no_secrets_and_read_only_token`)과 `pip install` 로그의 `tiktoken` 패키지명일 뿐 실제 비밀값 아님).

복사 뒤 `.venv/Scripts/python .claude/tools/evidence.py docs/wiki/work-items/20260924-pytest-ci --verify` 실행 결과, **60개 로그 전부 `일치`**:

```
일치   01-build-00-env.log  (exit=0, 2026-09-24T22:31:12+09:00)
일치   02-build-lsremote-checkout.log  (exit=0, 2026-09-24T22:31:26+09:00)
일치   03-build-lsremote-setup-python.log  (exit=0, 2026-09-24T22:31:29+09:00)
일치   04-build-lsremote-upload-artifact.log  (exit=0, 2026-09-24T22:31:32+09:00)
일치   05-build-red-initial.log  (exit=1, 2026-09-24T22:34:10+09:00)
일치   06-build-green-initial.log  (exit=0, 2026-09-24T22:35:13+09:00)
일치   07-build-hash-baseline.log  (exit=0, 2026-09-24T22:35:44+09:00)
일치   08-build-mut-a-red.log  (exit=1, 2026-09-24T22:35:54+09:00)
일치   09-build-mut-a-green.log  (exit=0, 2026-09-24T22:36:30+09:00)
일치   10-build-mut-b-red.log  (exit=1, 2026-09-24T22:37:04+09:00)
일치   11-build-mut-b-green.log  (exit=0, 2026-09-24T22:37:39+09:00)
일치   12-build-mut-c-red.log  (exit=1, 2026-09-24T22:38:13+09:00)
일치   13-build-mut-c-green.log  (exit=0, 2026-09-24T22:38:42+09:00)
일치   14-build-mut-d-red.log  (exit=1, 2026-09-24T22:39:21+09:00)
일치   15-build-mut-d-green.log  (exit=0, 2026-09-24T22:39:55+09:00)
일치   16-build-mut-e-red.log  (exit=1, 2026-09-24T22:40:33+09:00)
일치   17-build-mut-e-green.log  (exit=0, 2026-09-24T22:41:12+09:00)
일치   18-build-ac8.log  (exit=0, 2026-09-24T22:41:47+09:00)
일치   19-build-ac9.log  (exit=0, 2026-09-24T22:41:50+09:00)
일치   20-build-ac11.log  (exit=0, 2026-09-24T22:41:57+09:00)
일치   21-build-final-check.log  (exit=0, 2026-09-24T22:42:25+09:00)
일치   22-review-verify.log  (exit=0, 2026-09-24T22:45:35+09:00)
일치   23-review-ac6-build-evidence.log  (exit=0, 2026-09-24T22:47:03+09:00)
일치   24-review-ac13-forbidden-commands.log  (exit=0, 2026-09-24T22:47:04+09:00)
일치   25-build-r2-sanity-green.log  (exit=0, 2026-09-24T22:52:04+09:00)
일치   26-build-r2-mut-f-red.log  (exit=1, 2026-09-24T22:52:43+09:00)
일치   27-build-r2-mut-f-green.log  (exit=0, 2026-09-24T22:53:16+09:00)
일치   28-build-r2-mut-g-red.log  (exit=1, 2026-09-24T22:53:54+09:00)
일치   29-build-r2-mut-g-green.log  (exit=0, 2026-09-24T22:54:30+09:00)
일치   30-build-r2-mut-h-red.log  (exit=1, 2026-09-24T22:55:04+09:00)
일치   31-build-r2-mut-h-green.log  (exit=0, 2026-09-24T22:55:40+09:00)
일치   32-build-r2-final-check.log  (exit=0, 2026-09-24T22:56:13+09:00)
일치   33-review-r2-verify.log  (exit=0, 2026-09-24T22:58:55+09:00)
일치   34-review-r2-ac13-forbidden-commands.log  (exit=0, 2026-09-24T22:58:56+09:00)
일치   35-ac0-env.log  (exit=0, 2026-09-24T23:01:41+09:00)
일치   36-ac1-pytest.log  (exit=0, 2026-09-24T23:01:51+09:00)
일치   37-ac2-junit.log  (exit=0, 2026-09-24T23:02:22+09:00)
일치   38-ac3-flaky-1.log  (exit=0, 2026-09-24T23:02:30+09:00)
일치   39-ac3-flaky-2.log  (exit=0, 2026-09-24T23:02:57+09:00)
일치   40-ac3-flaky-3.log  (exit=0, 2026-09-24T23:03:21+09:00)
일치   41-ac3-compare.log  (exit=0, 2026-09-24T23:03:49+09:00)
일치   42-ac4-markers.log  (exit=0, 2026-09-24T23:03:57+09:00)
일치   43-ac4-header.log  (exit=0, 2026-09-24T23:04:03+09:00)
일치   44-ac4-no-deprecation.log  (exit=0, 2026-09-24T23:04:13+09:00)
일치   45-ac5-integration-none.log  (exit=5, 2026-09-24T23:04:39+09:00)
일치   46-ac6-build-evidence.log  (exit=0, 2026-09-24T23:04:47+09:00)
일치   47-ac7-opa-test.log  (exit=0, 2026-09-24T23:04:57+09:00)
일치   48-ac7-opa-guard-negative.log  (exit=0, 2026-09-24T23:05:01+09:00)
일치   49-ac8-workflow-structure.log  (exit=0, 2026-09-24T23:05:09+09:00)
일치   50-ac9-workflow-commands.log  (exit=0, 2026-09-24T23:05:11+09:00)
일치   51-ac9-local-install.log  (exit=0, 2026-09-24T23:05:19+09:00)
일치   52-ac9-pip-check.log  (exit=0, 2026-09-24T23:05:27+09:00)
일치   53-ac10-no-swallow.log  (exit=0, 2026-09-24T23:05:37+09:00)
일치   54-ac10-persist-cred.log  (exit=0, 2026-09-24T23:05:40+09:00)
일치   55-ac11-action-shas.log  (exit=0, 2026-09-24T23:05:46+09:00)
일치   56-ac12-scope.log  (exit=1, 2026-09-24T23:05:57+09:00)
일치   57-ac13-forbidden-commands.log  (exit=0, 2026-09-24T23:06:05+09:00)
일치   58-ac14-xml-hashes.log  (exit=0, 2026-09-24T23:06:12+09:00)
일치   59-ac14-verify.log  (exit=0, 2026-09-24T23:06:20+09:00)
일치   60-review-i-verify.log  (exit=0, 2026-09-24T23:11:56+09:00)
```

60개 전부 `일치`. "변조됨"·"없음" 0건.
