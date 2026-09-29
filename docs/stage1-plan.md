# 1단계 시작 계획서

> 대상: `docs/plan.md` 1단계 (0 ~ 6번). 이 문서는 **무엇을 어떤 순서로 `/work-item`에 넣을지**와 **코드 전에 정할 결정**을 정리한다.
> 작업 단위마다 세부 계획(`01-plan.md`)은 `/work-item` 안에서 planner가 따로 쓴다.

## 1. 목표

브로커를 거치지 않으면 도구를 호출할 수 없는 최소 형태를 만든다. 1단계가 끝났다는 기준은 `plan.md` 6번 완료 판정 4개다.

- 에이전트가 도구 주소로 직접 호출하면 실패한다
- 위임 없는 작업, 취소된 위임, 건당 한도 초과가 모두 거부된다
- OPA를 멈추면 모든 요청이 거부된다
- 판단마다 이유가 로그에 남는다

여기에 시연 1개를 더한다: "어제 거래처 저녁 식사 18만 원 청구해 줘"가 데모 에이전트 → 브로커 → 모의 경비 시스템까지 끝까지 돈다.

## 2. 현재 상태 (2026-09-29 갱신)

> 진행 상황의 원본은 이 절과 4장 표의 "상태" 열이다. 작업이 끝날 때마다 갱신한다. 체크박스는 `docs/plan.md`, 작업별 상세는 `docs/wiki/Home.md`.

### 다음 세션 시작점 (2026-09-29 세션 종료 시점)

**직전까지 한 일.** 작업 C(`1. 데이터 모델 (1차)`)를 `/work-item` 7단계로 끝내고 커밋 · 푸시했다
(`b0d7991`, `origin/dev`). 원격 CI 전 job 성공 —
[run 36561845563](https://github.com/SunWoo1213/broker-agent/actions/runs/36561845563).
그 앞에 맥 환경 준비와 하네스 자체 점검 테스트 수정도 커밋했다(`ba742dd`). README는 사용자가
직접 개편해 커밋했다(`0a65ab9`) — 목적 · 기술 스택 · 아키텍처 · 역할과 기여도 · 트러블슈팅 · 결과
구조이며, 앞으로 이 구조를 기준으로 갱신한다.

**커밋되지 않은 변경 2개 (다음 세션에서 가장 먼저 처리할 것).**
`docs/plan.md`와 이 파일(`docs/stage1-plan.md`)에 AC10(원격 CI) 결과를 반영한 줄이 워킹트리에만
있다. 사용자 승인을 받아 커밋하거나, 다음 작업 커밋에 함께 넣는다. 그대로 두고 `/work-item`을
시작하면 새 작업의 범위 검사(AC6)가 이 두 경로를 범위 밖 변경으로 잡으므로, 그때는 새 작업의
`00-approval.md` "작업 중 사람이 한 변경" 표에 적어야 한다.

**다음에 할 수 있는 작업 (사용자가 고른다).**

| 후보 | 내용 | 선행 |
|---|---|---|
| **E `2. 모의 도구`** | MCP 서버 3종(expense · mail · crm), 공유 비밀 헤더 검사(D19), `customer.lookup` 응답에 민감 필드, F-D5 인자 스키마 | A(완료) |
| **F-C5 `.env` 권한 구멍** | `settings.json`의 Bash deny가 `Bash(* .env.*)` 하나뿐이라 **정확히 `.env`인 대상은 걸리지 않는다.** `guard_critical.py`에는 env 패턴이 아예 없고 `evidence.py`도 같은 구멍을 물려받는다. 규칙 · 훅 · `tests/test_harness_hooks.py` 세 곳을 함께 고친다. **사용자만 반영** | — |
| F `3. 게이트웨이 뼈대` | MCP 서버 기동, `tools/list`, `tools/call`은 무조건 거부로 시작 | C(완료) · **E(대기)** |

F-C5는 지금 하네스에 실제로 뚫려 있는 구멍이다. 검증은 `tests/test_harness_hooks.py` 안에서
서브프로세스에 가짜 payload를 넘기는 방식으로만 하고, **Bash 명령 원문과 `-k` 패턴에 `.env` 조각을
넣지 않는다**(넣으면 현행 규칙에 걸려 실행 전에 막힌다).

**결정 대기 중인 하네스 개선안.** `.claude/harness-notes.md`의 `2026-09-29 1. 데이터 모델 (1차)
(작업 C)` 절 — H1 · H8은 이미 반영했고(evidence.py 비밀 마스킹 · LF 고정), **H2–H7은 제안 상태로
사용자 결정을 기다린다.** H4 · H5는 오늘 두 번 나온 "안전장치를 검증하는 테스트" 문제를 규칙으로
올리는 것이라 다음 작업 전에 반영하면 바로 효과가 있다.

**후속 항목.** `docs/plan.md`의 F-C1~F-C4(데이터 모델 절) · F-C5 · F-C6(하네스 후속 항목 절).
F-C6은 예전 증거 328개의 MANIFEST가 CRLF 기준이라 저장소에서 검증되지 않는 문제다 —
**해시를 다시 계산하지 않는다.** 상세: `docs/wiki/troubleshooting/evidence-manifest-crlf-hash-mismatch.md`.

**남아 있는 자원 (사용자가 AC11로 "그대로 두세요" 확인함).** `docker compose` postgres 컨테이너가
떠 있고, `broker_test` · `broker_test_mig` 데이터베이스와 `.claude/runs/20260929-data-model/`
(증거 134개 · `mutbak/` · 계획 · 검증 문서 전부)가 남아 있다. run 폴더는 git 제외 대상이고, 이번
작업의 증거 로그는 개발용 DB 비밀번호가 평문으로 남아 `.gitignore`로 커밋에서 뺐다. 다음 작업의
증거부터는 `evidence.py`가 쓰기 전에 마스킹하므로 그대로 커밋된다.

**환경.** 맥에 Python 3.13.7(uv 설치) · 저장소 루트 `.venv` 준비됨. 확인 명령은
`sh .claude/tools/python.sh -m pytest -q`(현재 97 passed)와
`sh .claude/tools/python.sh -m pytest -q tests/test_harness_hooks.py`(35 passed).

| 항목 | 상태 |
|---|---|
| 하네스 (agents · skills · hooks) | 완료. 규칙: 권한 우회 금지, 증거 도구 `.claude/tools/evidence.py`(권한 필터 포함), 계획 검증 P10 · P11, 승인 기록 `00-approval.md`, 변이 확인 · 탐침 (`.claude/harness-notes.md`). **2026-09-29 맥 · 윈도우 공용화:** 훅은 `.claude/hooks/run_hook.sh`를 거치고(인터프리터를 못 찾으면 fail-closed 판정), python 호출은 `sh .claude/tools/python.sh`로 통일, ask · deny 규칙은 커밋되는 `settings.json` 한 곳, `tests/test_harness_hooks.py` 35개가 훅이 실제로 막는지 확인 |
| `docker-compose.yml` | 이미지 고정(postgres 16.15 · redis 7.4.11-alpine · opa 1.20.2), OPA healthcheck, postgres 호스트 포트 5434 — 작업 A |
| `requirements*.txt` | 전부 `==` 고정 — 작업 A |
| `policies/` | D18 계약 정책(`policies/authz.rego`) + `opa test` 54개 · 정적 pytest 2개 — 작업 D, 완료 (d9b6b16, Actions 성공) |
| pytest · CI | `pytest.ini`, 테스트 13개(작업 D에서 정책 정적 검사 2개 추가), `.github/workflows/ci.yml` — 작업 B, 완료 (Actions run #1 성공, 7c0ad0d) |
| `control/db/` · Alembic | 테이블 4개(`agents` · `tools` · `tool_actions` · `delegations`), 마이그레이션 `0001_initial_schema`, 고정 · 멱등 시드 — 작업 C, 완료 (2026-09-29). 설계 확정은 `docs/decisions.md` **D21** |
| pytest (작업 C 이후) | 단위 70 · 통합 27 = **97개**. 통합은 `@pytest.mark.integration`, CI는 `pytest`(`-m "not integration"`) + **`pytest-integration`**(ubuntu + postgres 서비스) 두 job. `requirements.txt`에 `greenlet==3.5.6` 추가 |
| 원격 저장소 | `origin` = https://github.com/SunWoo1213/broker-agent (공개). main 푸시 완료 |
| 변수 이름 목록 | `env.example` (`.env.*`는 권한에서 전부 차단) |
| 로컬 도구 (윈도우) | Python 3.13.7, Docker 29.3 / Compose v5.1. **OPA CLI · gh CLI 없음** → `opa test`는 Docker 이미지로 실행 |
| 로컬 도구 (맥) | Docker 29.8, gh CLI 있음, OPA CLI 없음 → `opa test`는 Docker 이미지로 실행. **2026-09-29 환경 준비 완료:** `uv`(Homebrew)로 Python 3.13.7을 설치하고 저장소 루트에 `.venv` 생성, `requirements-dev.txt` 설치. CI가 고정한 3.13.7과 패치 버전까지 일치시키려고 Homebrew `python@3.13`(3.13.15) 대신 `uv`를 썼다. 확인: `sh .claude/tools/python.sh -m pytest -q` 48개 통과 |
| 결정 D15~D20 | **전부 승인(2026-09-25)** — `docs/decisions.md` D15~D20. D18은 K10 보강 포함 |

## 3. 코드 전에 정할 결정 (초안)

아래 결정은 2026-09-25에 모두 권장안대로 승인됐고 `docs/decisions.md` D15~D20으로 옮겼다. 이 절은 제안 당시의 설명으로 남긴다(확정 문구는 decisions.md가 기준).

### D15 에이전트 인증 방식 (①)
**승인됨 (2026-09-25). 확정 문구는 `docs/decisions.md` D15**
- **권장안:** 에이전트마다 Ed25519 키 쌍을 둔다. 공개키는 `agents` 테이블에 둔다. 에이전트는 HTTP 요청마다 헤더 4개(`X-Agent-Id`, `X-Timestamp`, `X-Nonce`, `X-Signature`)를 붙인다. 서명 대상: 메서드 · 경로 · 타임스탬프 · nonce · 본문 SHA-256.
- 타임스탬프는 ±60초까지만 받는다. nonce는 Redis `SET NX`(TTL 120초)로 재사용을 막는다. **Redis에 닿지 않으면 거부**한다.
- 대안: 에이전트가 직접 서명한 짧은 JWT를 Bearer로 보내는 방식. 구현은 쉽지만 본문과 묶이지 않는다.
- 이유: MCP Streamable HTTP는 한 세션으로 여러 요청을 보낸다. 세션 단위 인증이면 요청 본문을 바꿔치기해도 알 수 없다.

### D16 "누구를 대신한" 요청인지 전달하는 방식
**승인됨 (2026-09-25). 확정 문구는 `docs/decisions.md` D16**
- **권장안(1단계 한정):** 에이전트가 서명된 헤더 `X-On-Behalf-Of: <user_id>`로 보낸다. 게이트웨이는 그 사용자가 이 에이전트에게 위임했는지만 확인한다.
- **알려진 한계:** 에이전트가 손상되면 "자기에게 위임한 다른 사용자"를 사칭할 수 있다. Keycloak이 들어오는 단계에서 사용자 토큰과 묶는다. 이 한계는 평가 시나리오 "남의 데이터 접근"의 원인 분석에 그대로 적는다.

### D17 게이트웨이 · 도구의 MCP 구성
**승인됨 (2026-09-25). 확정 문구는 `docs/decisions.md` D17**
- 게이트웨이는 에이전트에게 MCP 서버(Streamable HTTP)이고, 도구 3종에게는 MCP 클라이언트다.
- **도구 이름:** `expense.create`처럼 점을 쓴다. 0번에서 고정한 MCP SDK가 점을 허용하지 않으면 `expense_create`로 바꾸고, 그 사실을 기록한다.
- **`tools/list`:** 등록된 작업 중, 요청한 사용자가 이 에이전트에게 위임한 것만 보여 준다. 보여 주는 것과 별개로, 실제 판단은 항상 `tools/call`에서 한다.
- **인자 검사:** 작업마다 JSON Schema를 `tool_actions`에 두고, 형식이 틀린 인자는 OPA에 보내기 전에 거부한다. 금액은 원 단위 정수.

### D18 OPA 입력 · 출력 계약과 역할 분담
**승인됨 (2026-09-25). 확정 문구 · 상세는 `docs/decisions.md` D18**
- ② 위임 확인은 게이트웨이가 DB로 한다: 위임 존재 · 작업 범위 · 만료 · 취소. 여기서 걸리면 OPA까지 가지 않고 거부한다.
- ③ OPA는 위험도 · 건당 한도 · 범위를 판단한다. 범위는 ②와 겹치지만 이중 방어로 둔다.
- 입력: `{agent, user, action: {name, risk}, delegation: {scopes, per_tx_limit, expires_at}, args}`
- `mail.send` 인자 `to` · `subject` · `body`는 모두 필수, `subject` · `body`는 문자열(빈 문자열 허용) — K10
- 출력: `{result: "allow" | "deny" | "require_approval", reason: string}`
- **아래 경우는 모두 거부:** OPA 응답 형식이 다름, 알 수 없는 result 값, 타임아웃(200ms), 연결 실패. `require_approval`도 1단계에서는 거부로 처리한다.

### D19 도구 호출자 확인 (1단계 임시)
**승인됨 (2026-09-25). 확정 문구는 `docs/decisions.md` D19**
- 게이트웨이만 아는 공유 비밀을 `X-Broker-Secret` 헤더로 보낸다. 도구는 이 헤더가 없거나 다르면 거부하고, 비교는 `hmac.compare_digest`로 한다.
- 비밀 값은 환경 변수로만 받는다. `env.example`에는 이름만 둔다.
- 2단계에서 서명 토큰으로 교체한다.

### D20 비동기 DB 접근
**승인됨 (2026-09-25). 확정 문구는 `docs/decisions.md` D20**
- SQLAlchemy asyncio + psycopg 3를 쓴다. 게이트웨이 지연 목표(p95 20ms)를 고려한 선택이다.
- **Windows 주의:** psycopg 비동기는 기본 이벤트 루프(Proactor)에서 동작하지 않는다. 로컬 실행과 pytest에서 Selector 이벤트 루프를 쓰도록 설정한다.

## 4. 작업 순서

`/work-item`에 넣을 단위다. 번호는 `plan.md` 번호를 따른다.

```
A 0-a 개발 환경 ─┬─ B 0-b 테스트 · CI
                 ├─ C 1 데이터 모델 ──┐
                 ├─ D 4 정책 ────────┤
                 └─ E 2 모의 도구 ───┤
                                     ├─ F 3-a 게이트웨이 뼈대 (전부 거부)
                                     │   └ G 3-b ① 에이전트 인증
                                     │      └ H 3-c ② 위임 확인
                                     │         └ I 3-d ③ 정책 판단 + 판단 로그
                                     │            └ J 3-e ⑦ 도구 호출
                                     └──────────────── K 5 데모 에이전트
                                                        └ L 6 1단계 완료 판정
```

| 순서 | `/work-item` 인자 | 범위 | 선행 | 상태 |
|---|---|---|---|---|
| A | `0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동` | venv, 미고정 패키지와 OPA 이미지 태그를 `==`/태그로 고정, compose 3종 healthy 확인 | — | 완료 (커밋 780b009) |
| B | `0. 개발 환경 — pytest · CI` | pytest 설정(asyncio, Windows 루프, `integration` 마커), 최소 테스트, GitHub Actions(pytest + Docker로 `opa test`) | A | 완료 (커밋 7c0ad0d, Actions run #1 성공) |
| C | `1. 데이터 모델 (1차)` | Alembic 초기화, 테이블 4개, 시드 스크립트 (에이전트 1 · 도구 3 · 작업 4 · 직원 2의 위임) | A | **완료** (2026-09-29, 커밋 `b0d7991`. 단위 70 · 통합 27 통과, 변이 37종 정확 일치, 증거 134개, 원격 CI 전 job 성공) |
| D | `4. 정책 (Rego)` | 기본값 거부 · 낮은 위험 허용 · 건당 한도 초과 거부 · 높은 위험 거부(임시), 규칙별 `opa test` | A (C와 병렬 가능) | 완료 (커밋 d9b6b16, Actions opa-test · pytest 성공) |
| E | `2. 모의 도구` | MCP 서버 3개, 공유 비밀 헤더 검사, `customer.lookup` 응답에 민감 필드 포함 | A | 대기 |
| F | `3. 게이트웨이 — 뼈대` | MCP 서버 기동, `tools/list`, **`tools/call`은 무조건 거부**로 시작 | C, E | 대기 |
| G | `3. 게이트웨이 — ① 에이전트 인증` | D15 서명 검증, nonce 재사용 차단 | F | 대기 |
| H | `3. 게이트웨이 — ② 위임 확인` | D16 · D18의 DB 확인 | G | 대기 |
| I | `3. 게이트웨이 — ③ 정책 판단` | OPA 호출, D18 계약 검증, 판단 로그(JSON 구조화, 결정 ID · 이유) | H, D | 대기 |
| J | `3. 게이트웨이 — ⑦ 도구 호출` | allow일 때만 도구 호출. 도구 오류 · 타임아웃은 에이전트에 실패로 반환 | I | 대기 |
| K | `5. 데모 에이전트` | LangGraph 에이전트가 브로커 주소 · 자기 개인키만 가지고 시연 문장을 끝까지 처리 | J | 대기 |
| L | `6. 1단계 완료 판정` | 완료 판정 4개를 통합 테스트로 묶어 compose 환경에서 실행 | J (시연은 K) | 대기 |

**순서를 이렇게 잡은 이유**
- 게이트웨이는 **처음부터 "전부 거부"로 시작**하고, 검사를 하나씩 붙인 뒤 마지막에 허용 경로(⑦)를 연다. 중간 어느 시점에 멈춰도 기본값이 허용인 코드가 남지 않는다 (원칙 1).
- D(정책)는 DB 없이 할 수 있어서 하네스 첫 연습 문제로도 적합하다 (`harness-notes.md`의 "정상" 연습 문제).

## 5. 테스트 전략

- **단위 테스트:** 서명 검증 · 인자 스키마 검사 · OPA 응답 해석처럼 외부 의존성이 없는 함수.
- **통합 테스트(`@pytest.mark.integration`):** compose의 실제 PostgreSQL · Redis · OPA를 쓴다. fail-closed 테스트는 목(mock)만으로 끝내지 않는다. 연결 실패(닫힌 포트), 타임아웃(느린 응답 서버), 이상한 응답(형식 오류)을 각각 확인한다 (`fail-closed-tests` 스킬).
- **실패 경로를 먼저 쓴다:** 작업 단위마다 거부 테스트가 허용 테스트보다 먼저 들어간다.
- **CI:** GitHub Actions에서 PostgreSQL · Redis를 서비스 컨테이너로 띄운다. OPA는 Docker 이미지로 `opa test`를 실행한다.

## 6. 위험과 대응

| 위험 | 대응 |
|---|---|
| MCP SDK · LangGraph API가 버전마다 바뀜 | A에서 `==` 고정. 예제 코드는 고정 버전 기준으로만 참고 |
| Windows 환경 문제 (이벤트 루프, 인코딩) | D20 설정을 `sys.platform` 조건부로 적용. 실제로 문제가 생기면 `/dev-wiki`로 트러블슈팅 기록 |
| 맥 · 윈도우 두 환경을 오가며 생기는 차이 (실행 파일 이름, venv 경로, 줄바꿈) | 훅 · 명령 원문은 `run_hook.sh` · `python.sh`로 통일하고 `.gitattributes`로 LF 고정. 환경을 옮기면 먼저 `sh .claude/tools/python.sh -m pytest -q tests/test_harness_hooks.py`로 하네스가 살아 있는지 확인한다 |
| 에이전트가 도구 포트에 직접 닿을 수 있음 (로컬) | 1단계 방어는 공유 비밀(D19). "직접 호출 실패" 테스트로 확인하고, 네트워크 격리는 5단계(보안 그룹)에서 |
| D16 사칭 한계 | 결정 기록 · 평가 원인 분석에 명시. 숨기지 않음 |
| 데모 에이전트 LLM 비결정성 | 시연은 모델 · temperature 고정. 완료 판정 테스트(L)는 LLM 없이 MCP 클라이언트로 직접 호출 |

## 7. 시작 전에 사용자가 할 일

- `env.example`을 복사해 `.env` 만들기. Claude는 `.env`를 읽거나 쓰지 않는다. D19 공유 비밀 값도 여기에 직접 넣는다.
- `docker compose up -d` 실행 (A에서 Claude가 해도 된다).
- 데모 에이전트용 `OPENAI_API_KEY`는 K 전까지만 준비하면 된다.
- ~~3번 결정 D15~D20을 승인 · 수정해 주기.~~ → 2026-09-25 전부 승인
