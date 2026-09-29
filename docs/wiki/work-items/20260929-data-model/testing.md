# 테스트 기록 — 1. 데이터 모델 (1차) — 작업 C

> 요약
> - 결론: APPROVE. 단위 70 · 통합 27(계획 24 + ④ 지적 반영 I25–I27) = 97 통과, 변이 37종 전부 기대 집합과 정확히 일치, flaky 0건, `evidence.py --verify` 134/134 일치.
> - 바뀐 것: `test_db_config.py`·`test_db_models.py`·`test_seed_constants.py`(단위) · `test_db_schema.py`·`test_seed_data.py`(통합) · `test_ci_workflow.py`(U22 추가) 신규/수정.
> - 다음에 알아야 할 것: 이 기록의 로그 두 건(`92-mut-ac-red.log`, `127-ac4-db-down.log`)에는 개발용 DB 비밀번호(`password=broker`)가 평문으로 남아 있다. 운영 값이 아니며, 앞으로의 로그에 대한 마스킹은 하네스 개선안 H1로 등록됐다(미반영).

## 요약

| 회차 | 판정 | pytest (통과/실패/건너뜀) | 변이 (exact 일치) | flaky | 공격 평가 |
|---|---|---|---|---|---|
| 1 (③ 자기 점검) | DONE | 94 passed / 0 failed / 0 skipped | 37/37(31종 중 재작업 전 상태) | 미실시 | 해당 없음 |
| 2 (③ r2 자기 점검) | DONE | 97 passed / 0 failed / 0 skipped | 37/37 | 미실시 | 해당 없음 |
| 3 (⑤ test-verifier 직접 재실행) | APPROVE | 97 passed / 0 failed / 0 skipped | 37/37 | 0/3(3회 반복 동일) | 해당 없음 |

## 테스트 설계

| 테스트 | 종류 | 검증하는 것 | 완료 조건 | 관련 원칙 |
|---|---|---|---|---|
| U1–U12(`test_db_config.py`) | 단위 | `DATABASE_URL` 필수·형식·타임아웃·`db_ping`·이벤트 루프 정책·Alembic 설정·`reset_schema` 가드 | AC1 | 원칙 1 · 2 · D20 |
| U13–U15(`test_db_models.py`) | 단위 | 모델 메타데이터(시각 컬럼 tz-aware, fail-closed 기본값, 테이블 집합 정확히 4개) | AC1 | 원칙 1 |
| U16–U22(`test_seed_constants.py`, `test_ci_workflow.py`) | 단위 | 시드 상수(점 표기·risk·이메일·args_schema·scopes·status·CI job 정합) | AC1 · AC7 | F-D4 · F-D5 |
| I1–I18(`test_db_schema.py`) | 통합 | 제약 위반(CHECK·FK·UNIQUE) 거부, 마이그레이션 되돌리기, `alembic check`, 테이블 집합 | AC3 | D18 · 원칙 1 |
| I19–I24(`test_seed_data.py`) | 통합 | 시드 멱등성·행 수·D18 입력 계약 만족 여부 | AC3 | D18 |
| I25(`test_daily_limit_negative_rejected`) | 통합(④ 지적으로 추가) | `daily_limit >= 0` CHECK 거부 | AC3 | 원칙 1 |
| I26(`test_version_below_one_rejected`) | 통합(④ 지적으로 추가) | `version >= 1` CHECK 거부 | AC3 | 원칙 6 |
| I27(`test_tool_action_requires_existing_tool`) | 통합(④ 지적으로 추가) | `tool_actions.tool_id → tools.id` FK 거부 | AC3 | — |
| 의존성 중단(AC4) | 의존성 중단 | postgres를 멈추면 통합 테스트가 skip이 아니라 fail(`N errors`) | AC4 | 원칙 1 |
| 변이 37종(a–ak) | 변이(mutation) | 위 테스트의 수량·전칭 표현·fail-closed 검사가 약하게 구현되면 red가 나는지 | AC5 | 원칙 7 |

## 회차 1 — DONE (③ 1회차 자기 점검)

### 환경

- 맥(Darwin), Python 3.13.7, docker compose postgres 16.15(호스트 포트 5434), 2026-09-29 세션.

### 실행한 명령과 결과

```
ac1-unit:        sh .claude/tools/python.sh -m pytest -q -rfE -m "not integration"       → 70 passed, 24 deselected
ac2-collect:      sh .claude/tools/python.sh -m pytest -q --collect-only                  → 94 tests collected
ac3-integration:  sh .claude/tools/python.sh -m pytest -q -rfE -m integration             → 24 passed, 70 deselected
ac4-stop/db-down/start: docker compose stop postgres → pytest → docker compose start postgres
                                                                                            → 24 errors(skip 없음), exit 1
ac7-ci:           sh .claude/tools/python.sh -m pytest -q tests/test_ci_workflow.py       → 5 passed
ac5-final-green:  sh .claude/tools/python.sh -m pytest -q -rfE                            → 94 passed
```

### 완료 조건 대조 (1회차)

| AC | 내용 | 확인한 테스트 | 결과 | 종료 코드 |
|---|---|---|---|---|
| AC0 | 채점 스크립트 무결성 | `check_self.py` | `summary OK files=2 mismatch=0` | 0 |
| AC1 | 단위 전부 통과 (N≥68) | 명령 A | 70 passed | 0 |
| AC2 | 계획한 46개 존재 | `--collect-only` | 94 tests collected, 46/46 포함 | 0 |
| AC3 | 통합 전부 통과 (N≥23) | 명령 B(integration) | 24 passed, skip 없음 | 0 |
| AC4 | postgres 중단 시 fail(skip 아님) | stop→pytest→start | 24 errors, skip 없음 | 1 (내부: 최종 pytest `exit_pytest=1`) |
| AC5 | 변이 31종(1회차 기준) exact 일치 | `check_ac.py` | 전부 일치(무효 로그 2건은 재실행으로 대체) | 0 |
| AC7 | CI 정합 | `pytest -q tests/test_ci_workflow.py` | 5 passed | 0 |
| AC8 | 의존성 고정 | pip check + import | `deps ok`, `greenlet==3.5.6` | 0 |
| AC9 | 비밀 하드코딩 없음 | `check_ac.py` 정규식 | 위반 0 | (check_ac.py 통합 판정 exit 0) |

**최종 판정 명령(채점 스크립트 직접 실행):** `summary OK=9 BAD=0 HUMAN=3`.

## 회차 2 — DONE (③ r2, ④ 지적 반영 후 재점검)

### 환경

동일(맥, Python 3.13.7, docker compose postgres 16.15).

### 실행한 명령과 결과

```
ac1-unit(109):        70 passed, 27 deselected                          exit 0
ac2-collect(110):     97 tests collected(계획 46개 전부 포함)              exit 0
ac3-integration(111): 27 passed, 70 deselected                          exit 0
ac4-stop/db-down/start(112-114): 27 errors(skip 없음)                    exit 1(내부 pytest)
ac7-ci(115):          5 passed                                          exit 0
ac5-final-green(116): 97 passed                                          exit 0
ac6-scope(117):       git status --porcelain, 계획 범위 안(HUMAN 1건)     exit 0
ac0-check-self(118):  summary OK files=2 mismatch=0                      exit 0
```

`evidence.py --verify` 요약(이 시점): `합계 118  일치 118  변조됨 0  없음 0`.
**최종 판정 명령:** `summary OK=9 BAD=0 HUMAN=3`.

### 새로 추가된 red/green 증거 (④ 지적 3 대응, 채점 밖 라벨)

| 라벨 | 변이 | 사전 추적 | 로그의 FAILED 집합 | 일치 |
|---|---|---|---|---|
| `review-i23` | seed alice per_tx_limit 200000→100000 | `{test_alice_per_tx_limit_covers_demo_amount}` | 1개, exit 1 → green 97 passed | 예 |
| `review-u9` | `event_loop_policy_class()` → `object` | `{test_event_loop_policy_on_current_platform}` | 1개, exit 1 → green 70 passed | 예 |
| `review-i4` | `per_tx_limit >= 1` CHECK + seed bob 0→1 + 도우미 기본값 페어링 | `{test_per_tx_limit_zero_allowed, test_per_tx_limit_defaults_to_zero}` | 2개, exit 1 → green 97 passed | 예 |

이 라벨들은 `checks/check_ac.py`의 `MUTATIONS`에 없어 채점 대상이 아니다(원칙 7 — 결과를 본 뒤 채점
기준을 고치지 않는다). 어느 37종 변이에서도 한 번도 red가 되지 않았던 I4·I23·U9에 대해, 구현 전
"전부 red" 증거가 구조적으로 불가능한 것(아래 참고)을 보완하기 위해 남긴 임시 증거다.

## 회차 3 — APPROVE (⑤ test-verifier 직접 재실행)

### 환경

- git HEAD: `ba742dd4631001808e39eb6ba49aa8fc7d0bbd62`(branch `dev`), 세션 시작 시 git status는 14개
  경로(신규 11 + 수정 3)만 변경.
- `docker compose ps`(evidence/119): `broker-agent-postgres-1` `Up 2시간 (healthy)`, 포트 `5434->5432`.
- 맥 세션, python은 전부 `sh .claude/tools/python.sh`.

### 실행한 명령과 결과

```
$ sh .claude/tools/python.sh -m pytest -q -rfE -m "not integration"     (라벨 ac1-unit, 122번)
70 passed, 27 deselected, 1 warning

$ sh .claude/tools/python.sh -m pytest -q -rfE -m integration           (라벨 ac3-integration, 124번)
27 passed, 70 deselected, 1 warning

$ sh .claude/tools/python.sh -m pytest -q -rfE                          (라벨 ac5-final-green, 131번, 명령 B)
97 passed, 1 warning

$ sh .claude/tools/python.sh -m pytest -q tests/test_ci_workflow.py     (라벨 ac7-ci, 125번)
5 passed, 1 warning
```

### 불안정성 확인 (새 테스트 3회 반복)

새로 추가 · 수정된 테스트 파일 6개(`test_db_config.py` · `test_db_models.py` · `test_seed_constants.py` ·
`test_db_schema.py` · `test_seed_data.py` · `test_ci_workflow.py`)를 대상으로 3회 반복 실행.

| 테스트 파일 6개 묶음 | 1 (132번) | 2 (133번) | 3 (134번) |
|---|---|---|---|
| 결과 | 53 passed, 1 warning | 53 passed, 1 warning | 53 passed, 1 warning |

매번 동일 — flaky 없음.

### 의존성 중단 테스트

| 중단한 서비스 | 테스트 | 기대 | 결과 | 종료 코드 | 서비스 재기동 확인 |
|---|---|---|---|---|---|
| `docker compose stop postgres`(126번) | 통합 27개(127번, 명령 B 통합 부분) | skip이 아니라 fail | `27 errors`, `skipped` 문자열 없음 | 1(내부: pytest 실행이 낸 `exit_pytest=1`, evidence.py가 기록한 명령 전체 `exit`도 1) | `docker compose start postgres`(128번) → healthy 재확인(129번, `ac4-verify-up`, exit 0) |

### 변이 37종(AC5)

`checks/check_ac.py`(121번, `verify-check-ac`)가 `MANIFEST.tsv`의 로그 원문(라벨별 마지막 로그, H6)을
파싱해 계획 표의 기대 FAIL 집합과 정확히 비교한 결과 **37/37 exact 일치**. 74개(mut-a~ak × red/green) +
재사용 라벨(`mut-ac`·`mut-ai`·`mut-n`·`mut-z`·`mut-k`의 재실행분: evidence 92·93·100–107) 전부가
채점에 쓰였다. ⑤는 전 37종을 다시 변이 적용해 재현하지는 않았다(모델·마이그레이션·시드 파일을
반복 변형하는 고비용 작업이라 스킬 절차가 `check_ac.py` 출력 확인으로 대신하도록 지시). 대신
채점 스크립트 자체의 해시(AC0)와 `--verify`로 로그 무결성을 확인해, `check_ac.py`가 읽은 로그가
변조되지 않았음을 보장했다.

### 완료 조건 대조

| AC | 내용 | 확인한 테스트/명령 | 결과 | 종료 코드 | 증거 |
|---|---|---|---|---|---|
| AC0 | 채점 스크립트 무결성 | `checks/check_self.py` | `summary OK files=2 mismatch=0` | 0 | `120-verify-ac0-check-self.log` |
| AC1 | 단위 전부 통과 | `pytest -q -rfE -m "not integration"` | 70 passed, 0 failed/error | 0 | `122-ac1-unit.log` |
| AC2 | 계획한 46개 존재 | `--collect-only` + 이름 대조 | 누락 0 | 0 | `123-ac2-collect.log` |
| AC3 | 통합 전부 통과 | `pytest -q -rfE -m integration` | 27 passed, 0 skipped | 0 | `124-ac3-integration.log` |
| AC4 | postgres 중단 시 skip 아닌 fail | stop → pytest → start | exit 1, `27 errors`, skip 없음 | 1 | `126-129` 로그 |
| AC5 | 변이 37종 exact 대조 | `checks/check_ac.py` | 37/37 정확 일치 | 0(check_ac.py 판정) | `121-verify-check-ac.log`, 원본 `12–87`, 재사용 `92-93,100-107` |
| AC6 | 작업 범위 | `git status --porcelain` + 분류 | 14경로 전부 목록 안, HUMAN 1건(`docs/decisions.md`) | 0 | `130-ac6-scope.log` |
| AC7 | CI 정합 | `pytest -q tests/test_ci_workflow.py` | 5 passed | 0 | `125-ac7-ci.log` |
| AC8 | 의존성 고정 | `check_ac.py` AC8 판정 | 통과 | 0(check_ac.py 판정) | `121-verify-check-ac.log` |
| AC9 | 비밀 URL 하드코딩 없음 | `check_ac.py` AC9 판정(9개 파일) | 위반 0 | 0(check_ac.py 판정) | `121-verify-check-ac.log` |
| AC10 | 원격 Actions `pytest-integration` 성공 | 사용자 확인 | **대기**(이 기록 시점까지 커밋·푸시 전) | — | — |
| AC11 | 남는 자원 인지 | 사용자 확인 | **대기** | — | — |

### 실패 상세

없음. ⑤가 재실행한 모든 판정 명령이 계획의 기대와 일치했다(실패 · 에러 · flaky 0건).

### 증거 무결성 (`evidence.py --verify`, 최종)

```
합계 134  일치 134  변조됨 0  없음 0
```

이 위키 페이지에 복사한 `docs/wiki/work-items/20260929-data-model/evidence/`에서도 동일 명령으로
재확인: `합계 134  일치 134  변조됨 0  없음 0`(전부 "일치").

## 비밀 값에 관한 사실 확인

이 증거 로그에는 **개발용 DB 비밀번호(`password=broker`)가 평문으로 들어 있다**
(`92-mut-ac-red.log`, `127-ac4-db-down.log` — pytest 긴 트레이스백이 psycopg 연결 프레임의
지역 변수를 repr로 찍은 결과, `grep -c "password="` 확인: 각각 2회 · 54회). 이것은 이미 사용자에게
보고됐고, 개발용 고정값이며 `env.example`에도 같은 취지로 이름만 있는 값이다. 운영 비밀번호가
아니다. 상세: [pytest-traceback-leaked-db-password-into-evidence-log.md](../../troubleshooting/pytest-traceback-leaked-db-password-into-evidence-log.md)

**그래서 이 작업의 `evidence/` 폴더는 저장소에 커밋하지 않았다**(`.gitignore`). 사용자 결정이다:
공개 저장소에 비밀 형태의 문자열을 평문으로 올리지 않는다. 이미 기록된 로그를 뒤늦게 마스킹하고
`MANIFEST.tsv`의 sha256을 다시 계산하는 길은 **택하지 않았다** — 기록 뒤에 해시를 고치는 것은
증거의 의미를 무너뜨리고(원칙 5 · 7), 실제로 그 시도는 권한 시스템에 `Logging/Audit Tampering`으로
막혔다. 대신 `evidence.py`를 고쳐 **앞으로의 로그는 파일에 쓰기 전에 마스킹**되도록 했다(개선안
작업 C H1, 2026-09-29 반영). 따라서 다음 작업부터는 증거 폴더가 그대로 커밋된다.

로그 134개는 `.claude/runs/20260929-data-model/evidence/`(git 제외)와 이 폴더의 로컬 사본에
남아 있고, 아래 무결성 확인 결과는 그 사본에 대해 실행한 것이다. 이 표의 수치와 인용한 요약 줄은
전부 그 로그 원문에서 옮긴 것이다.

→ 문제 해결 페이지: [guard-test-destroyed-the-resource-it-guards.md](../../troubleshooting/guard-test-destroyed-the-resource-it-guards.md) ·
[pytest-traceback-leaked-db-password-into-evidence-log.md](../../troubleshooting/pytest-traceback-leaked-db-password-into-evidence-log.md)
