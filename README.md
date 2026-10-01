# 에이전트 권한 브로커

AI 에이전트의 모든 도구 호출을 허용 · 거부 · 승인 중 하나로 판단하고 판단 근거를 위변조가 드러나는 감사 로그로 남기는 검문소를 만들고 있습니다. 지금은 정책 판단과 데이터 모델까지 동작합니다.

## 개요

| 항목 | 내용 |
| --- | --- |
| 기간 | 2026.09 ~ 진행 중 |
| 인원과 역할 | 1인 — 설계 · 정책 · 데이터 모델 · 테스트 절차 · 개발 하네스 전체 |
| 상태 | 진행 중. 브로커를 거치지 않으면 도구를 호출할 수 없는 최소 형태를 만드는 1단계 |
| 핵심 기술 | Python 3.13 · OPA(Rego) · PostgreSQL · SQLAlchemy · Alembic · Docker Compose · pytest · GitHub Actions · 변이 테스트 |

에이전트를 업무에 붙일 때 먼저 부딪히는 질문은 "에이전트에게 권한을 어디까지 줘도 되나"입니다. 프롬프트 주입에 당한 에이전트가 권한 밖의 데이터를 읽거나, 한도를 쪼개서 우회하거나, 승인받은 뒤 인자를 바꾸는 일이 생길 수 있습니다.

이런 통제를 에이전트 자신의 프롬프트에 맡기면 통제하려는 대상이 통제 장치를 들고 있는 셈이 됩니다. 그래서 에이전트 바깥의 코드로 막는 것을 목표로 했습니다. 에이전트는 실제 API 키를 가지지 않고 모든 도구 호출을 브로커에 요청합니다.

설계의 첫째 원칙은 판단할 수 없을 때 어느 쪽으로 넘어지는가입니다. 입력이 없거나 필드가 빠지거나 정책을 읽지 못하면 전부 거부합니다(fail-closed). 이 원칙은 브로커의 정책뿐 아니라 브로커를 만드는 개발 하네스(Claude Code 훅 · 권한 규칙 · 증거 기록 도구)에도 같이 적용합니다. 아래 문제 해결 사례 중 여러 건이 이 원칙을 개발 도구 자신에게 적용하지 못한 데서 나왔습니다.

| 작업(진행 순) | 내용 | 상태 |
| --- | --- | --- |
| A | 개발 환경 — 패키지 · 이미지 버전 고정, Docker Compose(PostgreSQL · Redis · OPA) | 완료 |
| B | pytest 설정, GitHub Actions CI | 완료 |
| D | OPA 정책 — 입력 · 출력 계약(D18), 규칙별 `opa test` | 완료 |
| C | 데이터 모델 — 테이블 4개, Alembic, 시드(D21) | 완료 |
| E | 모의 도구 — MCP 서버 3개(경비 · 메일 · 고객 DB), 공유 비밀 헤더 검사(D19) | 계획 승인 대기 |
| F ~ L | 게이트웨이, 데모 에이전트, 1단계 완료 판정 | 대기 |

현재 위치와 다음 할 일은 [1단계 계획서](docs/stage1-plan.md) 2장 · 4장에 있습니다.

## 문제 해결 사례

작업마다 계획 → 계획 검증 → 구현 → 구현 검증 → 테스트 순서를 거칩니다. 설계 · 정책 계약 · 검증 절차는 제가 정했고, 각 단계의 실행은 역할을 나눈 Claude Code 서브에이전트(계획 · 검토 · 구현 · 테스트)에 맡긴 뒤 단계마다 검토 결과를 보고 승인했습니다. 아래에서 "검토자"는 검토 담당 에이전트입니다. "REVISE"는 검토자가 고쳐 오라고 돌려보내는 판정이고, "탐침"은 테스트나 정책을 일부러 약하게 만든 사본으로 테스트가 잡아내는지 시험해 본 것입니다.

모든 실행 결과는 해시가 붙은 증거 로그로 남깁니다. 테스트가 통과하는 것만으로는 믿지 않고, 코드를 일부러 망가뜨려(변이) 실패해야 할 테스트가 정확히 실패하는지도 확인합니다. 아래는 그 과정에서 만난 문제 중 지금까지 중요했던 여섯 가지입니다. 전체 기록은 [개발 위키](docs/wiki/Home.md)에 있습니다.

1. [테스트 46개가 통과하는데도 계약을 지키지 못하던 문제를 변이 테스트로 드러내 해결](#테스트-46개가-통과하는데도-계약을-지키지-못하던-문제를-변이-테스트로-드러내-해결)
2. [가드를 검증하는 테스트가 가드를 뺀 변이에서 개발용 DB를 지운 문제를 입력 교체로 해결](#가드를-검증하는-테스트가-가드를-뺀-변이에서-개발용-db를-지운-문제를-입력-교체로-해결)
3. [승인 훅이 죽으면 명령이 그대로 통과하던 문제를 두 번에 걸쳐 fail-closed로 고침](#승인-훅이-죽으면-명령이-그대로-통과하던-문제를-두-번에-걸쳐-fail-closed로-고침)
4. [계획 밖에 들어간 더 엄격한 규칙에 거부 테스트가 없던 문제를 계약 승격과 변이로 해결](#계획-밖에-들어간-더-엄격한-규칙에-거부-테스트가-없던-문제를-계약-승격과-변이로-해결)
5. [증거 기록 도구로 감싼 명령이 권한 규칙을 비껴가던 구멍을 도구 안에서 막음](#증거-기록-도구로-감싼-명령이-권한-규칙을-비껴가던-구멍을-도구-안에서-막음)
6. [서브에이전트가 거부당한 명령을 다른 명령으로 우회한 일을 에이전트 규칙과 계획 검증으로 금지함](#서브에이전트가-거부당한-명령을-다른-명령으로-우회한-일을-에이전트-규칙과-계획-검증으로-금지함)

### 테스트 46개가 통과하는데도 계약을 지키지 못하던 문제를 변이 테스트로 드러내 해결

**문제 흐름**

```mermaid
flowchart LR
  S["계약 D18<br/>출력 키는 정확히 두 개"] --> PL["계획: 기대값은<br/>완전 비교로 쓴다"]
  PL --> IMP["구현된 테스트<br/>result · reason 따로 비교"]
  IMP -->|출력에 키가 더 붙어도| PASS["53/53 통과"]
  MU["변이 u<br/>허용 분기에 키 추가"] -->|테스트 G1 하나만 드러남| PART["G1만 완전 비교로 수정"]
  PR["검토자 탐침<br/>거부 분기에 키 추가"] -->|"1/53만 실패"| HOLE["나머지 46개에<br/>같은 결함"]
  HOLE --> FIX["46개 완전 비교로 수정<br/>변이 x · y 추가"]
```

**문제 원인**

정책은 판단 결과를 `{"result": ..., "reason": ...}` 형태로 내고, 설계 결정 D18은 "출력 키는 정확히 두 개"라고 정해 두었습니다. 계획은 테스트의 기대값 표기를 두 가지로만 허용했습니다. 출력 전체를 비교하는 완전 비교와 `result`만 비교하는 형태입니다. 구현 단계에서 계획한 53개 테스트를 작성했고 첫 실행에서 53/53이 통과했습니다.

문제는 변이 확인 중에 드러났습니다. 변이 u는 허용 분기의 출력에 키 하나를 더하는 변이입니다. 이 변이를 돌리면서 허용 테스트 G1이 계획에 없던 세 번째 형태로 짜여 있다는 것이 드러났습니다.

```rego
# 구현된 형태 — 출력에 키가 더 있어도 두 줄 모두 참이라 통과합니다
d.result == X
d.reason == Y

# 계획한 형태 — 키 집합까지 같아야 통과합니다
d == {"result": X, "reason": Y}
```

구현 단계는 G1 하나만 완전 비교로 고쳤습니다. 구현 검증 1차에서 검토자가 테스트 파일을 다시 읽어 보니 다른 46개 테스트도 같은 세 번째 형태였고, 이 처리를 REVISE로 돌려보냈습니다. 변이 u는 허용 분기만 건드리므로 거부 · 승인 분기 테스트의 같은 결함은 드러낼 수 없었습니다. 검토자가 거부 분기 출력에 키를 더하는 탐침을 돌려 보니 53개 중 1개만 실패했습니다. 결함이 실제로 남아 있었습니다.

계획의 변이 표는 "완전히 같음"이라는 조건을 깨는 변이를 허용 분기에만 두었습니다. 구현이 조건을 약하게 줄여 짜도 그 분기에 변이가 없으면 아무 신호가 나지 않습니다. 같은 유형이 직전 작업 B의 CI 테스트에서도 먼저 있었습니다. 계획의 "모든 job에 `timeout-minutes:`"는 구현에서 "timeout 줄 개수 세기"로, "`permissions:` 아래가 `contents: read` 하나다"는 "다음 한 줄만 확인"으로 줄어 있었고, 검토자가 timeout 없는 job이나 `pull-requests: write`를 추가한 사본으로 탐침했을 때 두 테스트가 그대로 통과했습니다.

**해결 과정**

- 46개를 모두 `d == {"result": X, "reason": Y}` 완전 비교로 바꿨습니다. 테스트 이름 · 입력 · 기대값은 바꾸지 않았고, 검토자가 diff 51쌍을 대조해 삭제 줄은 전부 개별 비교 형태, 추가 줄은 전부 완전 비교 형태이며 값 불일치가 0건임을 확인했습니다.
- 고친 표기가 다시 약해지지 않도록 변이 두 종을 영구 증거로 추가했습니다. 변이 x는 거부 분기 전체에, 변이 y는 승인 분기 전체에 키를 더합니다. 두 변이 모두 실패해야 할 테스트의 이름 목록을 정확히(exact) 지정했습니다.
- 기대 실패 집합은 "이 테스트들이 포함되면 통과"가 아니라 이름 목록으로 못박는 쪽으로 강화했습니다. 계획 검증 2차에서 변이 m의 기대 실패 집합을 5개에서 8개(exact)로 늘린 것도 같은 이유입니다.
- 일부러 그대로 둔 것도 있습니다. 변이 n · r · u는 계획한 부분집합보다 많은 테스트를 실패시켰습니다. 이 초과분은 관측값으로 기록만 하고 채점에서는 뺐습니다. 실행 결과를 보고 기대값을 고쳐 적으면 결과에 맞춰 기준을 바꾸는 것이 되기 때문입니다. 정확한 집합은 다음 작업이 실행 전에 손으로 추적해 고정하도록 후속 항목으로 넘겼습니다.
- 작업 B 쪽에서는 `_`로 시작하는 job id를 정규식 `JOB_HEADER_RE`가 놓치는 결함이 남았습니다. 영향이 job별 timeout 검사 하나뿐이라 그 사이클에서는 고치지 않고 미해결 항목으로 기록했습니다.

**테스트**

- 환경: `docker compose run --rm opa test /policies -v`, OPA 이미지 `openpolicyagent/opa:1.20.2`
- 수정 후 검토자의 같은 탐침(거부 분기에 키 추가)이 1/53 실패에서 36/53 실패로 늘었습니다.
- 작업 D의 변이 25종(a–y)을 하나씩 적용해 실패한 테스트 이름을 기대와 대조했습니다. 이름 목록을 지정하지 않은 변이는 계획한 테스트가 실패 집합에 모두 들어 있는지로 채점했습니다. 이름 목록을 지정한 변이는 x 37개 · y 7개 · m 8개 · p 1개 · v 1개 · w 1개가 모두 이름까지 정확히 일치했습니다.
- 변이를 되돌릴 때마다 정책 파일 해시가 기준선과 같은지 확인했고, 원래 정책에서는 54개 테스트(4번 사례에서 거부 테스트 1개를 더한 수)가 3회 반복해도 같은 이름 집합으로 모두 통과했습니다.

**결과** 허용 · 거부 · 승인 세 분기 모두에서 출력에 키가 더 붙으면 테스트가 실패합니다. 이것을 변이 u · x · y로 확인했습니다.

**배운 점** 통과하는 테스트와 믿을 수 있는 테스트는 다르며, 계획의 "모든 · 정확히 · 하나다" 같은 표현마다 그 조건을 깨는 변이를 짝지어야 테스트의 강도를 알 수 있습니다.

핵심 코드: `policies/authz_test.rego` · 문제 기록: [수량 표현이 약해진 테스트](docs/wiki/troubleshooting/ci-test-spec-quantifier-weakening.md)

### 가드를 검증하는 테스트가 가드를 뺀 변이에서 개발용 DB를 지운 문제를 입력 교체로 해결

**문제 흐름**

```mermaid
flowchart LR
  G["가드: DB 이름이<br/>_test로 끝나지 않으면 거부"] --> T["가드 검증 테스트 U12"]
  T -->|"입력: 개발용 broker DB<br/>실제 URL"| OK["가드가 있으면<br/>연결 전 ValueError"]
  M["변이 ac<br/>가드 제거"] --> T
  T -->|가드가 없으니 실제 연결| R[("개발용 broker DB")]
  R --> D["DROP SCHEMA public CASCADE<br/>CREATE SCHEMA public"]
  D --> FIX["입력을 닿을 수 없는 주소로<br/>닫힌 포트 1 + 없는 DB 이름"]
```

**문제 원인**

통합 테스트 도우미 `tests/dbsupport.py`의 `reset_schema()`는 테스트 DB의 스키마를 지우고 다시 만듭니다. 실수로 개발용 DB를 날리지 않도록, 연결하기 전에 DB 이름이 `_test` 또는 `_test_mig`로 끝나는지 확인하는 가드가 있습니다.

```python
def _require_test_db_name(db_name: str) -> None:
    if not db_name.endswith(_TEST_DB_SUFFIXES):
        raise ValueError(
            f"refusing to touch non-test database: {db_name!r} "
            f"(이름이 {_TEST_DB_SUFFIXES} 로 끝나야 한다)"
        )
```

이 가드가 정말 막는지 확인하는 테스트(`test_reset_refuses_non_test_database`, U12)는 개발용 DB의 실제 URL `postgresql+psycopg://broker:broker@localhost:5434/broker`를 입력으로 썼습니다. 가드가 있을 때는 엔진을 만들기 전에 `ValueError`로 끝나므로 이 입력이 위험하다는 사실이 드러나지 않습니다.

작업 C의 변이 절차에는 이 가드를 제거하는 변이 `ac`가 들어 있었습니다. 기대는 U12가 "예외가 나지 않아서" 실패하는 것이었습니다. 실제로 U12는 기대대로 실패했지만, 그보다 먼저 개발용 `broker` DB에 `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`이 실행됐습니다.

```
FAILED tests/test_db_config.py::test_reset_refuses_non_test_database
... DID NOT RAISE <class 'ValueError'>
```

`DID NOT RAISE`는 가드가 없어 예외가 나지 않았다는 뜻입니다. 가드가 없으니 테스트는 받은 URL로 그대로 연결해 스키마를 지우고 다시 만들었습니다. 변이 절차는 정의상 "가드가 없을 때 이 테스트가 무엇을 하는가"를 반드시 실제로 실행합니다. 변이는 절차대로 움직였을 뿐이고, 사고는 테스트 입력이 보호 대상 자체였기 때문에 일어났습니다. 안전장치를 검증하는 테스트는 안전장치가 없는 상태로 실행돼도 피해가 없어야 합니다.

같은 날 오전에도 같은 성격의 문제가 있었습니다. 인터프리터를 못 찾으면 훅이 막는지 보는 테스트 두 개가 맥에 `.venv`를 만들자 실패했습니다. 훅 실행기는 PATH보다 먼저 `<저장소>/.venv/bin/python`을 찾는데, 테스트는 PATH만 비워 "인터프리터 없음"을 흉내 냈습니다. 그동안 통과한 것은 그 기계에 `.venv`가 아직 없었기 때문이었습니다. 실패 메시지는 `guard_paths failed open when no interpreter was available`였지만 뚫린 것은 훅이 아니라 테스트의 전제였습니다.

**해결 과정**

- U12 입력을 `postgresql+psycopg://broker:broker@127.0.0.1:1/broker_do_not_touch`로 바꿨습니다. 루프백 주소의 닫힌 포트 1과 존재하지 않는 이름 `broker_do_not_touch`의 조합입니다.
  - 가드가 있으면 이름이 접미사 규칙에 맞지 않아 엔진 생성 전에 `ValueError`가 나고 테스트는 통과합니다.
  - 가드가 없으면 연결을 시도하다 `OperationalError`가 납니다. 이 예외는 `ValueError`의 하위 클래스가 아니므로 `pytest.raises(ValueError)`는 여전히 실패합니다.
  - 통과 조건인 `ValueError`를 내는 코드가 가드뿐이라 검증력은 그대로이고, 어느 경우에도 실제 DB에는 연결이 성립하지 않습니다.
- 기대 실패 집합 `{test_reset_refuses_non_test_database}`는 바꾸지 않았습니다. 사고를 피하려고 기대값을 고치는 것이 아니라 입력만 바꿔 같은 것을 확인하게 했습니다.
- 훅 쪽은 `.venv`가 없는 임시 저장소를 테스트가 직접 만들도록 고쳤습니다. `_runner_without_a_venv()`가 임시 폴더에 `run_hook.sh`와 훅 스크립트만 복사하고, 실행기는 자기 위치로 저장소 루트를 정하므로 그곳에는 `.venv`가 없습니다. 실행기와 훅 본체는 동작이 옳았기 때문에 고치지 않았습니다.
- 두 사건을 하나의 규칙으로 올렸습니다. 계획 검증 체크리스트(P14)가 ① 가드를 제거하는 변이가 있으면 그 가드를 검증하는 테스트의 입력이 실제 보호 대상인지, ② 실패 조건을 환경 상태에 기대고 있지는 않은지를 확인하고, 해당하면 REVISE를 냅니다.

**테스트**

- 환경: 맥, Python 3.13.7, `docker compose up -d postgres`(PostgreSQL 16.15)
- 고친 뒤 같은 라벨로 변이 `ac`를 다시 돌렸습니다. U12 하나만 실패했고(`exit 1`) 원인 줄은 `psycopg.OperationalError: connection failed: connection to server at "127.0.0.1", port 1 failed: ... Connection refused`였습니다. 되돌리면 단위 테스트 70개가 모두 통과했습니다.
- 훅 테스트는 `tests/test_harness_hooks.py` 35개, 당시 전체 48개가 `.venv`가 있는 상태에서 통과했습니다. 별도로 `env -i`와 빈 PATH에서 실행기를 직접 돌려 `deny` 판정 JSON이 실제로 나오는 것도 확인했습니다.

**결과** 검증력을 유지하면서 테스트가 보호 대상에 닿을 수 없게 됐습니다. 개발용 DB의 `public` 스키마는 사건 후 확인했을 때 비어 있었지만, "삭제 직전에도 비어 있었다"는 사후에 증명할 수 없다는 점도 기록에 남겼습니다.

**배운 점** 가드를 검증하는 테스트는 가드가 없을 때도 안전한 입력을 써야 하고, 실패 조건은 환경에 기대지 않고 테스트가 직접 만들어야 합니다.

핵심 코드: `tests/dbsupport.py` · `tests/test_db_config.py` · `tests/test_harness_hooks.py` · 문제 기록: [가드 테스트가 보호 대상을 지운 문제](docs/wiki/troubleshooting/guard-test-destroyed-the-resource-it-guards.md) · [`.venv`에 기댄 fail-closed 테스트](docs/wiki/troubleshooting/fail-closed-test-relied-on-missing-venv.md)

### 승인 훅이 죽으면 명령이 그대로 통과하던 문제를 두 번에 걸쳐 fail-closed로 고침

**문제 흐름**

```mermaid
flowchart LR
  C["git push 등<br/>위험한 명령"] --> H["PreToolUse 승인 훅<br/>guard_critical.py"]
  H -->|"① 윈도우: cp949 출력 오류로<br/>예외 종료"| PASS1["판정 없음<br/>명령 그대로 실행"]
  H -->|"② 맥: command: python<br/>실행 파일 없음, 훅이 뜨지 못함"| PASS2["판정 없음<br/>명령 그대로 실행"]
  H -->|정상 판정| ASK["사람 승인 요구"]
  PASS1 --> FIX1["① 모든 예외를 ask로<br/>ASCII 출력"]
  PASS2 --> FIX2["② run_hook.sh 실행기<br/>못 찾으면 직접 ask · deny"]
```

**문제 원인**

개발 하네스에는 `git commit` · `git push` · `terraform apply` 같은 명령에 사람 승인을 요구하는 PreToolUse 훅(`.claude/hooks/guard_critical.py`)과, 검증 담당 에이전트가 작업 폴더 밖에 쓰지 못하게 하는 경로 제한 훅(`guard_paths.py`)이 있습니다. 처음 만든 승인 훅은 판정 로직만 테스트했고, 훅 자신이 실패하는 경로는 설계하지 않았습니다. Claude Code는 훅이 종료 코드 2가 아닌 오류로 끝나거나 아예 시작하지 못하면 차단 신호로 보지 않고 도구 호출을 그대로 진행합니다. 즉 훅이 죽으면 그 자리가 fail-open이 됩니다. 이 문제가 환경을 바꿔 두 번 나타났습니다.

① 첫 번째는 한국어 윈도우에서였습니다(2026-09-24). 훅에 테스트 입력을 넣자 걸려야 할 명령마다 훅이 예외로 종료했고, 판정 결과는 `(pass)`였습니다.

```
UnicodeEncodeError: 'cp949' codec can't encode character '—' in position 142: illegal multibyte sequence
```

훅은 `json.dumps(..., ensure_ascii=False)`로 한글과 em dash(U+2014)가 든 사유를 출력했는데, 표준 출력 인코딩인 cp949에는 em dash가 없습니다. 판정 로직이 아니라 출력 단계에서 예외가 났고, 그 결과 승인을 요구해야 할 `git push`가 승인 없이 실행될 수 있는 상태였습니다.

② 두 번째는 개발 환경을 맥으로 옮긴 직후였습니다(2026-09-29). 승인 훅의 패턴 `\bgit\b[^;&|\n]*?\s(push)\b`에 반드시 걸리는 `echo "probe: git push origin dev"`를 실행했는데 승인 창이 뜨지 않았습니다. 훅이 "허용"을 낸 것인지 훅이 죽은 것인지는 밖에서 구분되지 않습니다. 둘 다 똑같이 조용히 통과하기 때문입니다.

```
$ which python
python not found
$ which python3
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3
```

하네스가 윈도우에서 만들어져 훅 설정이 `{"command": "python", "args": [...]}`였습니다. 당시 Claude Code는 `args`가 있으면 셸을 거치지 않고 실행 파일을 직접 띄우므로(exec form), PATH에 `python`이 없으면 훅 프로세스가 시작조차 하지 못합니다. 같은 설정을 쓰는 에이전트 6종의 `guard_paths.py`도 함께 죽어 있었습니다. 이 훅은 ① 이후 처음부터 "예외는 deny" 구조로 짰지만, 프로세스가 뜨지 못하면 그 예외 처리도 실행될 기회가 없습니다. 검증 담당 에이전트의 쓰기 제한이 통째로 사라진 상태였고, 이쪽이 더 위험했습니다.

①을 고칠 때 권한 설정 `permissions.ask`에 두 번째 방어선을 두었지만 ②를 막지 못했습니다. 권한 규칙 `Bash(git push *)`는 명령이 그 앞부분으로 시작하는지를 보므로 `echo "... git push ..."`처럼 다른 명령의 인자 안에 든 경우에는 걸리지 않습니다. 또 일부 규칙은 `.gitignore` 대상인 `settings.local.json`에만 있어 맥으로 넘어오지 않았고, 경로 제한은 애초에 권한 규칙으로 표현되어 있지 않았습니다. 두 번 모두 원인은 같습니다. 원칙을 지키게 하는 장치 자신에게는 fail-closed를 적용하지 않았고, 그 장치가 살아 있는지 확인하는 수단이 사람의 관찰뿐이었습니다.

**해결 과정**

① 훅이 어떤 이유로 실패해도 "사람에게 묻기"로 넘어지게 했습니다.

- 출력은 `ensure_ascii=True`로 ASCII만 내보냅니다. JSON 안에서 `\uXXXX`로 이스케이프되므로 뜻은 같습니다.
- 입력은 `sys.stdin.buffer`에서 바이트로 읽어 UTF-8로 직접 디코딩합니다. 콘솔 인코딩에 기대지 않기 위해서입니다.
- 입력 해석 실패와 최상위 예외를 모두 `permissionDecision: "ask"`로 처리합니다. 경로 제한 훅은 같은 구조에서 실패 시 판정을 `deny`로 둡니다.

```python
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # 어떤 예외도 "통과"로 새지 않게 한다
        ask(f"[승인 필요] 훅 내부 오류: {exc}")
```

② 훅 설정에서 인터프리터 이름을 직접 부르지 않고 실행기 `.claude/hooks/run_hook.sh`를 거치게 했습니다. 셸 형식(`shell: bash`)으로 부르므로 같은 문자열이 맥 · 리눅스의 `sh`와 윈도우의 Git Bash에서 그대로 쓰입니다. 실행기는 `.venv/bin/python` → `.venv/Scripts/python.exe` → `python3` → `python` → `py` 순서로 후보를 찾고, 이름만 있고 실제로는 돌지 않는 후보(윈도우 Microsoft Store의 `python3` 스텁)는 `-c ''`를 실제로 실행해 걸러 냅니다. 실행기는 실패해도 조용히 끝나지 않습니다. 훅마다 첫 인자로 실패 시 판정(`ask` 또는 `deny`)을 받아 두고, 무엇이든 실패하면 그 판정을 냅니다.

```sh
py=$(find_python) || {
    emit "[하네스] 실행 가능한 python 을 찾지 못해 훅을 돌리지 못했습니다. 통과시키지 않고 막습니다 (fail-closed)."
    exit 0
}
out=$("$py" "$script" "$@")
code=$?
if [ "$code" -ne 0 ]; then
    emit "[하네스] 훅 스크립트가 비정상 종료했습니다 (exit $code). 통과시키지 않고 막습니다 (fail-closed)."
    exit 0
fi
```

실행기는 `dirname` 같은 외부 명령에도 기대지 않습니다(`${0%/*}` 사용). PATH가 비어 있어도 "인터프리터를 못 찾았다"는 정확한 사유로 막아야 하기 때문입니다. 함께 고친 것은 세 가지입니다.

- 문서 · 완료 조건 · 증거 로그의 python 호출을 `sh .claude/tools/python.sh` 한 형태로 통일했습니다. `.venv/Scripts/python`처럼 한쪽 OS에서만 도는 이름을 적지 않습니다.
- `settings.local.json`에만 있던 ask · deny 규칙(`rm -rf` · `Remove-Item` · `.env.*` 등)을 커밋되는 `settings.json`으로 옮겼습니다.
- `.gitattributes`에 `* text=auto eol=lf`를 두었습니다. CRLF로 받은 `.sh` 실행기는 돌지 않고, 증거 로그의 sha256도 OS마다 달라지기 때문입니다.

**테스트**

- ① 윈도우: 명령 26개 × 도구 2종(Bash · PowerShell) = 52건과 잘못된 입력 3건(JSON 아님, command가 숫자, 한글 UTF-8 명령)을 넣어 기대 판정과 비교했습니다. 결과는 `FAILURES: 0`이었고, 경로 제한 훅은 9건으로 따로 확인했습니다.
- ② 맥: `run_hook.sh`에 훅 페이로드를 넣어 9가지 경로를 확인했습니다. 깨진 JSON · 없는 스크립트 · 인터프리터 없음 · 스크립트 비정상 종료(exit 3)가 모두 `ask` 또는 `deny`로 끝났습니다. 실제 Claude Code 세션(`claude -p`)에서는 고치기 전 그대로 실행되던 `echo 'git push origin dev'`가 차단됐습니다.
- 훅이 이 OS에서 실제로 막는지 판정하는 `tests/test_harness_hooks.py` 35개를 추가했습니다. 목을 쓰지 않고 실제 `run_hook.sh`를 서브프로세스로 돌려 판정 JSON을 봅니다. 설정을 예전 `command: python` 형태로 되돌리기, 실행기가 인터프리터를 못 찾을 때 조용히 `exit 0`하게 바꾸기, 에이전트 훅을 `command: python3`으로 바꾸기의 탐침 3건에서 모두 해당 테스트가 실패했고, 복원 후 48개가 모두 통과했습니다.
- CI는 이 테스트를 `ubuntu-24.04`와 `macos-15` 매트릭스에서 모두 돌립니다.

**결과** 훅이 예외로 죽어도, 시작하지 못해도 통과가 아니라 승인 요구나 거부로 넘어집니다. 인터프리터를 못 찾거나 훅이 비정상 종료하는 고장은 다음에 환경을 옮길 때 `pytest` 한 번으로 드러납니다.

**배운 점** 안전장치는 정상 판정만 볼 것이 아니라 죽었을 때 어느 쪽으로 넘어지는지까지 확인해야 했습니다. 설정 파일에 적어 둔 것만으로는 부족했고, 이 OS에서 실제로 막는지를 테스트로 남겨야 환경을 옮겨도 다시 확인할 수 있었습니다.

핵심 코드: `.claude/hooks/guard_critical.py` · `.claude/hooks/run_hook.sh` · `tests/test_harness_hooks.py` · 문제 기록: [훅 인코딩 문제](docs/wiki/troubleshooting/hook-cp949-fail-open.md) · [맥에서 훅이 죽은 문제](docs/wiki/troubleshooting/hooks-dead-on-macos.md)

### 계획 밖에 들어간 더 엄격한 규칙에 거부 테스트가 없던 문제를 계약 승격과 변이로 해결

**문제 흐름**

```mermaid
flowchart LR
  PL["계획: mail.send 허용 키<br/>to · subject · body"] -->|필수 여부 · 타입은 빈칸| IMP["구현이 규칙 추가<br/>subject · body 문자열 필수"]
  IMP -->|계획의 테스트 목록만 작성| NT["이 규칙의 거부 테스트 0개"]
  NT --> DEL["규칙 줄을 지워도<br/>53개 전부 통과"]
  DEL --> FIX["D18 계약으로 승격<br/>거부 테스트 1개 + 변이 v · w"]
```

**문제 원인**

구현 검증 1차에서 검토자가 계획에 없던 규칙을 찾았습니다. `policies/authz.rego`가 `mail.send` 요청의 `subject` · `body`를 문자열로 필수화하고 있었습니다. 더 엄격한 방향이라 위험해 보이지 않았지만, 테스트 파일에서 두 필드가 나오는 곳은 메일 기본 입력의 고정값(`subject: "s", body: "b"`) 한 곳뿐이었습니다.

```
grep -n "subject\|body" policies/authz_test.rego
34:...    "args": {"to": ["kim@example.com"], "subject": "s", "body": "b"}}
```

두 `is_string` 검사 중 하나를 지우고 `opa test`를 돌리면 53개 테스트가 전부 통과합니다. 규칙이 사라져도 CI가 알아채지 못하는 상태였습니다.

경위는 이렇습니다. 계획은 `mail.send`의 허용 키 집합만 정했고 각 키의 필수 여부와 타입은 정하지 않았습니다. 계획에 빈칸이 있으면 구현자가 채웁니다. 구현 단계가 그 빈칸을 더 엄격한 규칙으로 채우면서, 테스트는 계획의 목록 53개만 그대로 옮겨 썼습니다. 정책 작성 규칙에는 "규칙 하나당 최소 허용 한 개 + 거부 한 개"가 있었지만 이를 "계획이 정한 테스트만 옮겨 쓴다"로 좁게 해석했습니다. 코드 검토 체크리스트에도 "diff에 들어간 규칙마다 거부 테스트가 있는가"라는 항목이 없어서, 이번에는 검토자의 주의력으로만 잡혔습니다.

**해결 과정**

안은 두 가지였습니다. B안은 규칙을 지워 계획대로 돌아가는 것이고 A안은 규칙을 계약으로 올려 거부 테스트와 변이를 더하는 것입니다. B안은 정책을 지금보다 느슨하게 만들므로 A안을 택했습니다.

- 설계 결정 D18에 "`mail.send`의 인자 키는 `to` · `subject` · `body`만 허용하고 셋 다 필수다. `subject` · `body`는 문자열(빈 문자열 허용)"을 추가했습니다. 계약 문서는 사이클 2 구현을 시작하기 전에 고쳤습니다.
- 거부 테스트 `test_mail_subject_body_required_denied`를 추가했습니다. `subject` 없음 · `body` 없음 · `subject: 1` · `body: null` · `subject: ["s"]` · `body: {"x": 1}` 여섯 경우가 모두 `deny / invalid_args`인지 완전 비교로 확인합니다.
- 각 검사 줄을 지우는 변이 v(`is_string(body)` 제거)와 w(`is_string(subject)` 제거)를 만들고, 기대 실패 집합을 새 테스트 하나로 정확히 지정했습니다.
- 재발을 막기 위해 코드 검토 체크리스트에 A4 "diff에 들어간 정책 규칙 · 검사마다 그것이 거부로 떨어지는 테스트가 하나 이상 있다"를 추가했습니다.

```rego
valid_args if {
	input.action.name == mail_send
	...
	is_string(input.args.subject)   # 이 줄이 지워지면 변이 w가 잡습니다
	is_string(input.args.body)      # 이 줄이 지워지면 변이 v가 잡습니다
}
```

**테스트**

- 환경: `docker compose run --rm opa test /policies -v`
- 변이 v · w 모두 새 테스트 하나만 정확히 실패했습니다(`FAIL: 1/54`). 되돌린 뒤에는 정책 파일 해시가 기준선과 같았고 54개가 모두 통과했습니다.
- 검토자가 별도 사본에서 타입 검사를 "값이 있는지만 확인"하도록 약하게 바꿔 탐침했을 때도 같은 테스트가 잡아냈습니다(`FAIL: 1/54`). 변이 v · w와는 다른 방식의 약화입니다.

**결과** 이 규칙은 이제 계약 · 테스트 · 변이 세 곳에 묶여 있어, 지우거나 약하게 바꾸면 바로 실패합니다.

**배운 점** 더 엄격한 변경도 테스트 없이 들어가면 지워져도 아무도 모르므로, 계획 밖의 규칙을 넣을 때는 그 규칙을 거부로 떨어뜨리는 테스트를 같이 씁니다.

핵심 코드: `policies/authz.rego` · `policies/authz_test.rego` · 문제 기록: [거부 테스트 없는 엄격한 규칙](docs/wiki/troubleshooting/strict-rule-without-deny-test.md)

### 증거 기록 도구로 감싼 명령이 권한 규칙을 비껴가던 구멍을 도구 안에서 막음

**문제 흐름**

```mermaid
flowchart LR
  E["evidence.py 라벨<br/>'curl ...'"] --> PERM{"권한 규칙<br/>명령 앞부분만 매칭"}
  PERM -->|"보이는 것은 evidence.py뿐"| RUN["안쪽 curl이<br/>확인 없이 실행"]
  C["curl ... 직접 실행"] --> PERM
  PERM -->|"Bash(curl *) 매칭"| ASK["사람 확인"]
  RUN --> FIX["evidence.py가 실행 전<br/>명령 전체를 ask · deny 규칙과 대조<br/>걸리면 exit 126"]
```

**문제 원인**

이 프로젝트는 모든 검증 명령을 증거 기록 도구 `.claude/tools/evidence.py`로 실행합니다. 도구는 명령을 실행하고 시작 · 끝 시각, git HEAD, 명령 원문, 종료 코드, 출력 전체를 로그로 남긴 뒤 sha256을 매니페스트에 적습니다. 작업 B의 계획을 고치며 "모든 완료 조건을 `evidence.py`로 실행한다"는 지시를 반영하던 중, 계획 담당 에이전트가 이 도구가 새 우회 경로가 된다는 것을 발견했습니다.

```
.venv/Scripts/python .claude/tools/evidence.py <run> u2-check 'curl -s "https://api.github.com/..."'
```

Claude Code의 권한 규칙은 명령이 규칙에 적은 앞부분으로 시작하는지를 봅니다. 다른 명령의 문자열 인자 안에 든 명령까지 풀어 보지는 않습니다. 위 명령에서 권한 시스템이 보는 것은 `evidence.py ...`뿐이라, `Bash(curl *)` 같은 ask 규칙이 안쪽 `curl`에 걸리지 않습니다. `evidence.py`는 받은 문자열을 그대로 `bash -lc`에 넘겨 실행하므로 `curl` · `git push` · `docker run` 같은 승인 대상 명령이 확인 없이 실행될 수 있었습니다.

증거 도구를 설계할 때 "무엇을 기록할 것인가"만 정하고 "권한 시스템과 같은 fail-closed 기준으로 스스로도 막을 것인가"는 정하지 않았습니다. 새 실행 경로를 만들면 기존 통제를 우회하는 경로도 함께 생깁니다.

**해결 과정**

- `evidence.py`가 실행 전에 `.claude/settings*.json`의 Bash · PowerShell ask · deny 규칙 조각 54개(`curl` · `git push` · `docker run` · `rm -r` · `.env.` 등)를 읽어, 명령 문자열 어디에든 단어 경계로 들어 있는지 대조합니다. 하나라도 걸리면 실행하지 않고 종료 코드 126으로 끝내며 로그도 남기지 않습니다.
- 설정 파일을 읽지 못하면 그 자체를 거부 사유로 돌려줍니다. 규칙을 확인할 수 없을 때 통과시키지 않기 위해서입니다.

```python
def blocked_by(command: str) -> str | None:
    """명령 어디에든 규칙 조각이 단어 경계로 들어 있으면 그 조각을 돌려준다."""
    try:
        prefixes = guarded_prefixes()
    except Exception as exc:
        return f"(권한 규칙 확인 실패: {exc})"
    for core in prefixes:
        pattern = r"(?<![\w-])" + r"\s+".join(re.escape(tok) for tok in core.split()) + r"(?![\w-])"
        if core.endswith((".", "/")):  # '.env.' 처럼 뒤에 무엇이 와도 막아야 하는 조각
            pattern = pattern[: -len(r"(?![\w-])")]
        if re.search(pattern, command, flags=re.IGNORECASE):
            return core
    return None
```

- `git push` · `curl`처럼 꼭 필요한 ask 대상 명령은 도구로 감싸지 않고 직접 실행해 사람 확인을 받은 뒤, 출력 파일만 `evidence.py ... "cat <파일>"`로 기록하도록 절차를 정했습니다. `curl`을 python · httpx 같은 다른 도구로 바꿔 ask를 피하는 방법은 쓰지 않기로 했습니다. 6번 사례에서 금지한 "막힌 목적을 다른 명령으로 달성하기"와 같은 행동이기 때문입니다.

**테스트**

- 계획 단계에서 `blocked_by()`에 계획의 `evidence.py` 명령 36개를 실제로 넣어 모두 통과(`None`)이고, 대조군 4개(`git push` · `curl` · `git remote -v` · `docker run`)는 모두 거부 대상임을 실행 전에 확인했습니다.
- 차단을 기대한 명령 17건과 허용을 기대한 명령 9건이 모두 기대대로 처리됐습니다. 실제로 `curl --version`을 감싸 보내면 126으로 거부되고 증거 폴더도 생기지 않았습니다.
- 이후 하네스 점검 테스트 `test_evidence_tool_still_refuses_guarded_commands`가 `git push --dry-run origin dev`를 감싸 보내 종료 코드 126과 로그 미생성을 매번 확인합니다. 규칙 파일을 옮겨도 필터가 살아 있는지 보는 테스트입니다.

**결과** 증거 도구로 감싼 명령도 권한 규칙과 같은 목록으로 검사하고, 규칙을 읽지 못하면 실행하지 않습니다. 문자열 대조라서 일부러 난독화한 명령까지 잡지는 못합니다.

**배운 점** 검문소를 만드는 도구 자신도 검문소를 통과해야 하며, 새 실행 경로를 만들 때는 그 경로가 기존 통제를 비껴가는지부터 확인해야 합니다.

핵심 코드: `.claude/tools/evidence.py` · 문제 기록: [권한 우회 문제](docs/wiki/troubleshooting/evidence-tool-permission-bypass.md)

### 서브에이전트가 거부당한 명령을 다른 명령으로 우회한 일을 에이전트 규칙과 계획 검증으로 금지함

**문제 흐름**

```mermaid
flowchart LR
  PL["계획의 완료 조건에<br/>권한이 막는 경로 포함"] --> B["구현 에이전트"]
  B -->|"Get-Item .env.example"| D1["deny 규칙에 막힘"]
  D1 -->|"stat으로 같은 정보 조회"| BY["우회"]
  B -->|"rm -rf 임시 venv"| A1["ask 규칙에 걸림"]
  A1 -->|"Remove-Item -Recurse -Force"| BY
  BY --> REV["코드 검토 BLOCK"]
  REV --> FIX["에이전트 규칙: 막히면 멈춤<br/>계획 검증: 막히는 경로 금지"]
```

**문제 원인**

개발은 역할이 나뉜 Claude Code 서브에이전트(계획 · 검토 · 구현 · 테스트)가 진행합니다. 작업 A의 구현 단계에서 구현 에이전트가 권한 시스템에 두 번 막혔는데, 멈추지 않고 다른 명령으로 같은 목적을 달성했습니다.

1. `.env.example`의 수정 시각을 PowerShell `Get-Item .env.example`로 확인하려다 `PowerShell(* .env.*)` deny 규칙에 막히자, POSIX `stat`으로 같은 메타데이터를 조회했습니다.
2. 저장소 밖 임시 venv를 `rm -rf`로 지우려다 `Bash(rm -rf *)` ask 규칙에 걸리자, PowerShell `Remove-Item -Recurse -Force`로 지웠습니다.

구현 검증 단계의 검토자는 이를 BLOCK으로 판정했습니다. 판정 사유는 "이 프로젝트가 만드는 것이 거부당한 에이전트가 다른 경로로 같은 일을 하지 못하게 하는 검문소인 만큼, 개발 에이전트가 같은 행동을 한 것은 사람이 보고 판단해야 한다"였습니다.

원인은 두 층에 있었습니다. 구현 에이전트의 문서에 "권한 거부나 ask에 부딪히면 멈춘다"는 규칙이 없었습니다. 그보다 앞서 계획 단계가 권한이 막는 경로(`.env.example` 메타데이터 조회, 임시 폴더 삭제)를 완료 조건 절차에 넣었고, 계획 검증이 세 차례(r1 · r2 · r3) 모두 이를 잡지 못했습니다. 결국 불변 원칙 1(fail-closed)이 브로커 코드에만 적용되고, 브로커를 만드는 하네스가 권한 시스템을 쓰는 방식에는 적용되지 않았습니다.

**해결 과정**

- 이번 건은 사람이 확인하고 수용했습니다. `.env.example`의 내용은 어느 경로로도 읽지 않았고, 삭제 대상은 저장소 밖 임시 폴더였기 때문입니다. 대신 같은 일이 반복되지 않도록 규칙으로 막기로 했습니다.
- 구현 · 테스트 에이전트 문서의 "하지 말 것"에 추가했습니다. 권한 규칙이나 훅에 막히면 같은 목적을 다른 명령 · 다른 셸(`stat` ↔ `Get-Item`, `rm` ↔ `Remove-Item` 등)로 다시 시도하지 않고, 멈춰서 막힌 명령 원문과 규칙을 기록한 뒤 보고합니다.
- 계획 담당 문서에는 권한 규칙이 막는 경로(`.env` · `.env.*` · 키 파일 등)를 대상으로 하는 명령을 메타데이터 확인까지 포함해 완료 조건 · 절차에 넣지 않는다는 규칙을 추가했습니다.
- 계획 담당 규칙만으로는 한 겹 방어라서, 계획 검증 체크리스트에 P10 "완료 조건 · 작업 절차에 deny · ask 대상 명령이나 삭제 단계가 없다"를 추가해 두 번째 겹을 두었습니다.
- 우회와 구분해야 할 것도 명시했습니다. 컨테이너 안 절대경로를 넘기는 명령에 `MSYS_NO_PATHCONV=1`을 붙이는 것은 권한 문제가 아니라 Git Bash의 경로 변환을 끄는 설정이므로 우회로 보지 않습니다.

**테스트**

- 반영 여부는 개선 계획과 개선 계획 검증 단계가 세 문서의 실제 줄 번호를 근거로 확인했습니다.
- 이 규칙은 에이전트 행동에 대한 것이라 실행 테스트로는 아직 확인하지 못했습니다. 효과는 이후 작업에서 막힌 명령이 우회 없이 멈춤으로 기록되는지로 확인하고 있습니다. 같은 날 작업 B에서는 계획 검증이 처음으로 "완료 조건 · 절차에 deny · ask 명령이 없는지"를 실제로 검사했습니다. 5번 사례의 증거 도구 구멍도 같은 작업의 계획 작성 중에 발견됐습니다.

**결과** 막힌 명령을 다른 명령으로 우회하는 것을 통제 무력화로 다루는 규칙을 계획 · 계획 검증 · 구현 · 테스트 네 단계의 문서에 넣었습니다. 다만 이것은 에이전트에게 주는 지시라서 강제력이 없습니다. 실제로 막는 장치는 여전히 권한 규칙과 훅입니다.

**배운 점** 거부당한 뒤 다른 명령으로 같은 일을 하는 것은 브로커가 막으려는 행동과 똑같습니다. 개발 에이전트에게도 "막히면 멈추고 보고한다"를 명시해야 했습니다.

핵심 문서: `.claude/agents/broker-builder.md` · `.claude/agents/test-verifier.md` · `.claude/agents/planner.md` · `.claude/skills/plan-review/SKILL.md` · 문제 기록: [서브에이전트의 권한 우회](docs/wiki/troubleshooting/subagent-permission-bypass.md)

## 아키텍처

```mermaid
flowchart LR
    U([사용자]) -->|권한 위임<br/>범위 · 한도 · 기한| D[(위임 저장)]
    A[AI 에이전트<br/>실제 키 없음] -->|도구 호출 요청| B[브로커 게이트웨이]
    D --> B
    B --> P{OPA 정책<br/>authz.rego}
    P -->|low_risk_in_scope| T[임시 토큰<br/>작업 1건 · 5분]
    P -->|approval_required_*| H[사람 승인<br/>인자 해시에 묶임]
    P -->|기본값 거부<br/>no_matching_rule · invalid_input| X[거부 + 이유 코드]
    H -->|인자가 바뀌면 실행 안 됨| T
    T --> TOOL[사내 시스템]
    B & P & H & T -.-> L[(감사 로그<br/>아웃박스 + 해시 체인)]
```

정책의 입력은 `{agent, user, action: {name, risk}, delegation: {scopes, per_tx_limit, expires_at}, args}`이고 출력은 `{result, reason}`으로 키가 정확히 두 개입니다. 이유 코드에는 우선순위가 있습니다. `invalid_input` > `invalid_args` > `action_not_in_scope` > `delegation_expired` > `per_tx_limit_exceeded` > `approval_required_*` > `low_risk_in_scope`(허용) 순입니다.

1단계에서는 승인이 필요한 요청(위험도 높음 · 중간, 사내 밖 수신자 메일)도 일단 거부합니다. 2단계에서 `require_approval`로 바꿉니다. 계약 원문은 [설계 결정 D18](docs/decisions.md)에 있습니다. 위 그림에서 지금 동작하는 부분은 OPA 정책과 데이터 모델이고, 게이트웨이 · 임시 토큰 · 승인 · 감사 워커는 설계만 되어 있습니다.

## 기술 스택

| 구분 | 기술 | 선택한 이유 |
| --- | --- | --- |
| 언어 | Python 3.13.7 | CI가 패치 번호까지 고정하므로 로컬도 같은 값을 씁니다 |
| 정책 엔진 | Open Policy Agent (Rego) | 권한 판단을 애플리케이션 코드에서 떼어내, 정책만 따로 테스트하고 바꿀 수 있게 했습니다 |
| 데이터베이스 | PostgreSQL, SQLAlchemy, Alembic | 위임 · 한도 · 승인 · 감사 로그를 한 트랜잭션에서 다뤄야 했습니다 |
| 캐시 | Redis | 누적 한도의 예약과 확정에 쓸 예정입니다 |
| 실행 환경 | Docker Compose (PostgreSQL · Redis · OPA) | 세 서비스의 이미지 버전을 고정해 어느 OS에서든 같은 구성으로 띄웁니다 |
| 테스트 · CI | pytest, GitHub Actions, `opa test`, 변이 테스트 | 통과하는 테스트와 믿을 수 있는 테스트를 구분하려고 변이 절차를 함께 씁니다 |

## 역할과 기여도

1인 프로젝트입니다. 설계 · 정책 계약 · 검증 절차는 제가 정했습니다. 구현은 역할을 나눈 Claude Code 서브에이전트에 맡기고 단계마다 검토 결과를 보고 승인했습니다.

- 권한 판단 정책을 Rego로 작성했습니다. 기본값 거부, 입력 검증, 이유 코드 우선순위를 규칙으로 두고 규칙별 `opa test`를 붙였습니다.
- 정책의 입력 · 출력 계약을 설계 결정 문서에 고정하고, 테스트가 그 계약을 완전 비교로 확인하게 했습니다.
- 데이터 모델 테이블 4개와 Alembic 마이그레이션, 시드 데이터를 만들었습니다.
- 테스트를 믿을 수 있는지 확인하는 변이 절차를 세웠습니다. 정책과 코드를 일부러 망가뜨리고 기대한 테스트가 정확히 실패하는지 대조합니다.
- 통합 테스트가 서비스 부재를 조용히 건너뛰지 않고 실패하도록 구성했습니다.
- 개발 하네스의 훅과 증거 기록 도구를 fail-closed로 고치고, 하네스가 현재 OS에서 살아 있는지 판정하는 테스트를 추가했습니다.
- 모든 실행 결과를 해시가 붙은 증거 로그로 남기고 `evidence.py --verify`로 무결성을 확인합니다.

## 결과

진행 중인 프로젝트입니다. 아래는 작업 C 기준입니다.

| 항목 | 결과 |
| --- | --- |
| `opa test` 정책 단위 테스트 | 54/54 통과, 3회 반복해도 같은 결과 |
| pytest 단위 (CI 설정 · 정책 정적 검사 · 하네스 훅 점검 · DB 설정 · 시드 상수) | 70 passed |
| pytest 통합 (`@pytest.mark.integration`, 실제 PostgreSQL) | 27 passed, skip 0 |
| 의존성을 멈췄을 때 | PostgreSQL을 끄면 통합 테스트가 조용히 건너뛰지 않고 27개 전부 오류 |
| 변이 테스트 (작업 C) | 37종 전부 기대한 테스트 집합과 정확히 일치, 되돌리면 전부 통과 |
| 증거 무결성 (`evidence.py --verify`) | 작업 C의 로그 134개 전부 해시 일치 (로그 자체는 개발용 DB 비밀번호가 평문으로 남아 커밋하지 않았습니다. 이후 로그는 `evidence.py`가 쓰기 전에 마스킹합니다) |

브로커 게이트웨이와 모의 도구, 데모 에이전트는 아직 만들지 않았습니다. 현재까지 동작을 확인한 것은 정책 판단과 데이터 모델, 그리고 개발 하네스입니다.

## 문서

- [아키텍처](docs/architecture.md)
- [설계 결정](docs/decisions.md)
- [진행 계획](docs/plan.md)
- [1단계 계획 · 현재 상태](docs/stage1-plan.md)
- [개발 위키 (작업 기록 · 문제 해결)](docs/wiki/Home.md)

## 로컬 실행

맥 · 윈도우(Git Bash) · 리눅스에서 같은 명령을 씁니다.

```bash
cp env.example .env
sh .claude/tools/python.sh -m venv .venv
sh .claude/tools/python.sh -m pip install -r requirements-dev.txt
```

Python은 3.13.7을 씁니다. CI(`.github/workflows/ci.yml`)가 패치 번호까지 고정하므로 로컬도 같은 값을 맞춥니다. 그 버전이 없다면 `uv python install 3.13.7`로 받은 인터프리터로 `.venv`를 만드십시오. `.venv`는 반드시 저장소 루트에 둡니다. 아래 실행기와 훅이 그 경로를 먼저 찾습니다.

`.claude/tools/python.sh`는 `.venv/bin/python`(맥 · 리눅스)과 `.venv/Scripts/python.exe`(윈도우)를 먼저 찾고, 없으면 `python3` → `python` → `py` 순서로 찾습니다. 맥에는 `python`이라는 이름의 명령이 없어서, 이 실행기를 거치면 두 OS의 명령 원문이 같아집니다.

## 테스트 실행

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm opa test /policies -v   # 정책 단위 테스트 (작업 D 기준 54개)
sh .claude/tools/python.sh -m pytest -q -m "not integration"       # 단위 테스트만 (서비스 불필요)
sh .claude/tools/python.sh -m pytest -q -m integration             # 통합 테스트 (PostgreSQL 필요)
sh .claude/tools/python.sh -m pytest -q                            # 전부
```

통합 테스트는 `docker compose up -d postgres`가 떠 있어야 하고, 서비스가 없으면 건너뛰지 않고 실패합니다. 조용한 skip은 "확인했다"와 구분되지 않기 때문입니다. `broker_test`와 `broker_test_mig` 데이터베이스를 스스로 만들어 쓰고 개발용 `broker`는 건드리지 않습니다.

첫 명령의 `MSYS_NO_PATHCONV=1`은 윈도우 Git Bash가 컨테이너 안의 경로 `/policies`를 윈도우 경로로 바꾸지 못하게 막는 설정입니다. 맥 · 리눅스에서는 아무 일도 하지 않으므로 OS와 상관없이 항상 붙입니다.

CI는 main 푸시와 PR마다 세 job을 돌립니다. 정책 단위 테스트(`opa test`), 단위 테스트(`ubuntu-24.04` · `macos-15` 매트릭스, junit xml 업로드), 통합 테스트(`ubuntu-24.04`, PostgreSQL 16.15 서비스 컨테이너)입니다.
