# 0. 개발 환경 — pytest · CI

> 요약
> - 결론: 로컬 관문(①–⑦) 전부 APPROVE로 끝났다. 원격 확인도 끝났다: U1 푸시(09-24 23:26) → U2 Actions run #1 성공(opa-test · pytest 두 job 모두 success, 증거 `62-u2-actions-result.log`) → U3 plan.md 체크. **완료.**
> - 바뀐 것: `pytest.ini`, `tests/test_pytest_config.py`(T1–T7), `tests/test_ci_workflow.py`(T8–T11), `.github/workflows/ci.yml`, `tests/README.md`. 판정 스크립트(`checks/*.py`)를 계획(①) 단계에서 미리 고정하고 증거 도구(`evidence.py`)로 모든 AC를 실행하는 방식을 이번에 처음 썼다.
> - 다음에 알아야 할 것: 사용자가 U1(푸시) 승인 → U2(Actions 결과 확인) → U3(`docs/plan.md` 체크 + 두 번째 커밋)를 진행해야 이 항목이 끝난다. `docs/plan.md` 체크박스는 아직 바꾸지 않았다.

| 날짜 | plan.md 항목 | 결과 | 관문 재시도 | 개선 사이클 |
|---|---|---|---|---|
| 2026-09-24 | 1단계 0번 세 번째 체크박스(pytest·CI) | 완료 (Actions run #1 성공) | ② 1회(r1→r2→r3, 판정은 r3에서 1회만) · ④ 2회(1차 REVISE→2차 APPROVE) · ⑦ 1회 | 1회(코드 수정 없음) |

## 1. 목표

`docs/plan.md` 1단계 0번의 세 번째 체크박스("pytest가 도는 최소 테스트 1개 + GitHub Actions 워크플로", `docs/stage1-plan.md` 4장 작업 순서 B)를 만든다. 관련 불변 원칙: 1(fail-closed — 테스트·CI 자신에 적용), 2(자격 증명 비노출 — 워크플로가 비밀을 안 씀), 7(재현성 — CI와 로컬이 같은 명령, 채점 기준을 결과보다 먼저 고정).

## 2. 설계와 결정

- pytest 9의 `strict = true`(strict_config·strict_markers 등 일괄), `asyncio_mode = strict`를 쓴다. `-m "not integration"`을 addopts에 넣지 않아 기본 실행에서 통합 테스트가 조용히 빠지는 일(fail-open)을 막는다.
- Windows Selector 이벤트 루프 설정과 CI의 PostgreSQL·Redis 서비스 컨테이너는 **이번 범위에 넣지 않는다**(판단 1·2). 이유: Selector 루프는 D20(미승인)에 의존하고, 이번 작업에는 통합 테스트가 0개(AC5)라 서비스를 띄워도 확인할 방법이 없다. → C(1. 데이터 모델)로 넘긴다.
- `docs/plan.md` 체크박스는 U2(Actions 첫 실행 성공)가 성공한 뒤에만 `[x]`로 바꾼다(판단 3). "GitHub Actions 워크플로"라는 항목 문구를 원격에서 한 번도 안 돌려보고 완료로 표시하지 않기 위함.
- **r2에서 추가한 결정(사용자 지시: "테스트를 했다 하고 끝내는 것이 아니라 실제로 수행한 흔적과 그 증거가 있어야 한다")**: 모든 AC와 ③ 자기 점검을 `.claude/tools/evidence.py`로 실행해 로그·해시를 남긴다. 판정 기준(`checks/*.py`)을 결과를 보기 전에 ① 단계에서 스크립트로 고정한다(원칙 7).
- **r3에서 추가한 결정**: r2 작업 중 evidence.py로 명령을 감싸면 `.claude/settings*.json`의 ask·deny 규칙이 명령 앞부분만 보기 때문에 안쪽 명령이 규칙을 비껴가는 구멍을 발견했다. → evidence.py에 권한 필터(종료 코드 126)를 추가해 규칙 조각이 명령 어디에든 있으면 실행하지 않고 거부하도록 바꿨다. U1(`git push`)·U2(`curl`)처럼 원래 ask 대상인 명령은 도구로 감싸지 않고 직접 실행해 사람 확인을 받은 뒤, 출력을 `evidence.py … "cat <파일>"`로만 기록한다.
- 검토했지만 버린 대안: actionlint 실행(로컬 설치나 컨테이너 실행에 ask 대상 명령이 필요해 범위 밖으로 뺌), OPA 결과를 artifact로 올리는 것(로컬 재현 명령이 파일을 만들지 않게 하려고 뺌).
- decisions.md 변경: 없음. D1–D9와 충돌하지 않고 D15–D20에 의존하지 않는다.

> 검증 상세: [verification.md](verification.md) · 테스트 상세: [testing.md](testing.md)

## 3. 진행 기록

| 단계 | 판정 | 요지 |
|---|---|---|
| ② 계획 검증 | APPROVE (r3 대상) | REVISE 없음. P1–P11 전부 통과, `evidence.blocked_by()`로 계획 명령 36개 통과·대조군 4개(126 거부 대상) 확인 |
| ④ 구현 검증 | 1차 REVISE → 2차(r2) APPROVE | 1차: T11이 `permissions:` 확장을, T8이 job별 timeout 누락을 놓침(계획의 "하나다"·"모든" 조건을 줄여 구현). r2에서 두 테스트를 강화하고 변이 f·g 증거로 확인 |
| ⑤ 테스트 | APPROVE | AC0–AC14 중 14개 exit 0(AC5는 기대값 exit 5로 통과), AC12만 exit 1이지만 `00-approval.md` 기록과 정확히 일치하는 범위 밖 변경이라 실패로 세지 않음 |
| ⑦ 개선 계획 검증 | APPROVE (판정: 코드 수정 없음) | 04·05 지적 전부 반영 확인, 근본 원인 2가지(변이 표가 수량·전칭 표현을 안 덮음, checks·tests 검사 강도 불일치)로 정리. 06 도입부 문장 오류 1건 정정(AC5 exit 5를 "exit 0"으로 잘못 씀) |

## 4. 구현 요약

| 파일 | 변경 |
|---|---|
| `pytest.ini` (새 파일) | `testpaths=tests`, `strict=true`, `asyncio_mode=strict`, loop-scope 2개 `function`, `integration` 마커 등록 |
| `tests/test_pytest_config.py` (새 파일) | T1–T7. `pytester.runpytest_subprocess`로 실제 `pytest.ini`를 복사한 내부 세션을 돌려 검증 |
| `tests/test_ci_workflow.py` (새 파일) | T8–T11. `ci.yml`을 텍스트로만 읽음(PyYAML 미사용). r2에서 T8·T11 강화(아래 6절) |
| `.github/workflows/ci.yml` (새 파일) | job 2개(`pytest`, `opa-test`). action SHA 3개 고정(아래 표), `timeout-minutes: 10`(두 job), pytest junit 업로드 |
| `tests/README.md` | 실행 방법, `integration` 마커 규칙(서비스 꺼지면 실패, skip 금지), async 테스트는 `@pytest.mark.asyncio` 필수. r2에서 문구 1곳 정정 |
| `docs/plan.md` | **바꾸지 않음.** U2 성공 뒤 오케스트레이터가 처리(판단 3) |

action SHA 고정값 (`git ls-remote --tags`로 확인, `curl`·`gh` 미사용):

| action | 태그 | SHA |
|---|---|---|
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | `v7.0.0` | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

## 5. 테스트

상세: [testing.md](testing.md). 요약: pytest 전체 `11 passed`, flaky 3회 반복 동일, opa test `PASS: 1/1`, AC0–AC14 중 14개 통과·1개(AC12) 범위 밖 처리.

## 6. 문제 상황과 해결

| 문제 | 분류 | 상태 | 상세 |
|---|---|---|---|
| evidence.py로 명령을 감싸면 ask·deny 권한 규칙을 비껴가는 우회 경로가 생김 | 하네스 | 해결 | [링크](../../troubleshooting/evidence-tool-permission-bypass.md) |
| ④ 1차 REVISE — 계획의 "하나다"·"모든" 같은 수량·전칭 조건이 테스트 구현에서 줄어들어도 변이 표가 잡지 못함 | 테스트 | 해결(r2에서 테스트 강화 + 변이 f·g·h 추가) | [링크](../../troubleshooting/ci-test-spec-quantifier-weakening.md) |
| `JOB_HEADER_RE`가 `_`로 시작하는 job id를 헤더로 인식하지 못해 timeout 검사 대상에서 빠짐 | 테스트 | 미해결 — 후속 항목 F1으로 이관 | [링크](../../troubleshooting/ci-test-spec-quantifier-weakening.md) (재발 기록 절) |

## 7. 배운 점

- 계획 단계에서 "먼저 쓸 테스트"에 수량·전칭 표현("모든", "하나", "정확히")이 있으면 그 조건을 깨는 변이(변이 표)를 반드시 짝지어야 한다. 이번에는 변이 a–e가 설정 줄만 다뤄서, 테스트 구현이 조건을 줄여도(T11 "다음 한 줄만", T8 "개수만 2") red 증거 없이 그대로 통과했다.
- 같은 조건을 채점 스크립트(`checks/`, YAML 완전 일치)와 저장소 테스트(`tests/`, 텍스트 파싱)에 다른 강도로 지정하면, 더 강한 쪽(로컬 채점)이 CI에서 돌지 않으므로 CI 안의 회귀 방지에 구멍이 남는다.
- 하네스 개선안(`.claude/harness-notes.md` 76–91행): ⑦ 통과 뒤 사용자가 "네 추천대로 진행해주세요"로 결정해 **반영 완료**됐다: H1(`agents/planner.md` "변이 확인" 단락 — 검증 문장의 수량·전칭·보안 관련 검사에 한정) · H2(`agents/planner.md` "하지 말 것" — checks·tests 강도 불일치 금지) · H4(같은 곳 — 사람 변경으로 BAD가 날 수 있는 AC는 통과 규칙 명시) · H5(`skills/work-item/SKILL.md` 00-approval 절 — ③–⑤ 동안 추적 파일 수정 금지, 급하면 00-approval 선기록) · H7(`skills/code-review-invariants/SKILL.md` D4 — 탐침 절차, 보안 검사에 한정)이 실제로 파일에 들어갔다. H3는 H1에 합쳐졌다. **H6(ac6을 ③ 권장 목록에 포함)은 보류**됐다 — F1과 별개로 아직 미반영.

## 8. 관련

- 커밋: 7c0ad0d(구현 · 로컬 완료) → 원격 확인 기록 커밋(U3)
- 선행: `20260924-dev-env`(A. 가상환경·버전 고정·compose 기동)
- 후속: U1(푸시)·U2(Actions 결과)·U3(plan.md 체크 + 두 번째 커밋), F1(`JOB_HEADER_RE` `_` 허용 + 헤더 누락 검출, 다음에 `test_ci_workflow.py`를 건드리는 항목 또는 사이클 2), F2(D20 승인 뒤 Selector 루프, C에서 CI에 PostgreSQL·Redis 추가), F3(action SHA 자동 갱신 검토)
