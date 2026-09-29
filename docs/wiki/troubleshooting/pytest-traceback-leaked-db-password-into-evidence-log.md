# pytest의 긴 트레이스백이 증거 로그에 DB 비밀번호를 평문으로 남긴다

> 요약
> - 한 줄 해결: 미해결 — 현재 우회 방법 없음. `evidence.py`가 로그를 쓰기 직전에 마스킹하는 개선(H1)을 제안했지만 아직 반영되지 않았다.
> - 원인: pytest 기본 트레이스백(`--tb=auto`/`long`)이 스택 프레임마다 함수 인자 · 지역 변수를 repr로 찍는데, psycopg `Connection.connect()`의 `conninfo`·`kwargs`가 DSN 원문이라 `password=…`가 그대로 출력된다. 우리 코드의 `redact_url()`은 우리가 만드는 메시지만 가리고, 서드파티 프레임 인자는 구조적으로 가리지 못한다.
> - 재발 방지: `evidence.py`가 로그 본문을 파일에 쓰기 전에 비밀 패턴을 마스킹하도록 하는 개선안(H1)을 하네스 노트에 제안. 사용자 승인 뒤 반영 예정, **이미 만들어진 로그는 고치지 않는다**(해시가 깨져 증거가 무효가 된다).

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-29 | 하네스 | 미해결(제안 단계) | ④ 구현 검증(r2) 참고 → ⑤ 테스트 재확인 → ⑥ 개선사항 계획 | 원칙 2 (자격 증명 비노출) |

## 증상

`1. 데이터 모델 (1차)` 작업(작업 C)의 증거 로그 두 곳에서 개발용 DB 비밀번호가 평문으로 발견됐다.

```
92-mut-ac-red.log (라벨 mut-ac-red)
cls = <class 'psycopg.Connection'>
conninfo = 'host=127.0.0.1 dbname=broker_do_not_touch user=broker password=broker port=1 …'
kwargs = {… 'password': 'broker' …}
```

```
127-ac4-db-down.log (라벨 ac4-db-down)
conninfo = 'host=localhost dbname=broker user=broker password=broker port=5434 hostaddr=127.0.0.1'
```
27개의 에러 트레이스백마다 반복 출력되어(⑤가 grep으로 5회 이상 확인) 총 발생 횟수가 많다.

이 값은 `env.example`에 적힌 개발용 고정값(`broker`/`broker`)이라 **비밀은 아니다.** 다만 실제
`DATABASE_URL`에 운영 비밀번호가 들어간 환경에서 같은 연결 실패 경로를 거치면, 같은 방식으로
증거 로그에 평문 비밀번호가 남는다.

## 재현 방법

1. `control/db/session.py` 또는 `tests/dbsupport.py`가 psycopg로 DB에 연결을 시도하는 테스트를 만든다.
2. 연결이 실패하는 조건(닫힌 포트, 서비스 중단 등)을 만든다.
3. pytest 기본 옵션(`--tb=auto`/`long`)으로 실행하고 `evidence.py`로 로그를 남긴다.
4. 로그에서 `password=` 또는 `'password':`를 grep한다.

## 원인

1. 직접 원인: pytest의 긴 트레이스백은 실패한 호출 체인의 **각 프레임의 지역 변수 · 인자**를
   repr로 출력한다. psycopg의 `Connection.connect(cls, conninfo, …)` 프레임에서 `conninfo`(DSN 문자열)와
   `kwargs`(딕셔너리, `password` 키 포함)가 그대로 출력 대상이 된다.
2. 왜? → 이것은 **서드파티 라이브러리(psycopg)의 프레임**이고, 우리가 만든 메시지가 아니다.
3. 근본 원인: `control/db/session.py`의 `redact_url()`은 **우리 코드가 직접 만드는 오류 메시지**
   (`_validate_driver`, `create_engine` 실패 메시지)에만 적용되고, pytest가 트레이스백을 만드는 과정
   자체에는 개입하지 않는다. 즉 마스킹 계층이 우리 코드와 서드파티 프레임 사이의 경계를 넘지 못한다 —
   구조적으로 이 지점에서 막을 수 없는 위치에 있다.

## 해결

**미해결.** ④(r2)가 참고 사항으로 지목했고, ⑤가 새로 실행한 `127-ac4-db-down.log`에서도 재현을
확인했다. ⑥이 제안한 수정안(H1, 미반영):

> `evidence.py`의 `main()`이 로그 본문(`명령:` 줄 + stdout + stderr)을 파일에 **쓰기 직전에**
> 아래 패턴으로 치환한다. 파일에 쓰기 전에 치환하므로 `sha256`은 치환된 내용으로 찍혀
> `--verify`와 충돌하지 않는다. **이미 만들어진 로그는 다시 쓰지 않는다**(기존 증거의 해시를 보존해야 한다).
>
> ```python
> SECRET_PATTERNS = [
>     (re.compile(r"(password=)[^\s'\"]+"), r"\1***"),                 # libpq conninfo
>     (re.compile(r"('password':\s*')[^']*(')"), r"\1***\2"),          # psycopg kwargs repr
>     (re.compile(r"(://[^:\s'\"/@]+:)[^@\s'\"]+(@)"), r"\1***\2"),    # URL userinfo
> ]
> ```
>
> 보조안(필수 아님): AC 명령에 `--tb=short`를 붙이면 프레임 인자를 찍지 않아 같은 누출을 막지만
> 진단 정보가 줄어든다. 마스킹이 주 수단이고, `--tb=short`는 다음 작업의 계획이 필요하다고
> 판단할 때만 AC 명령 규약으로 넣는다.

이 개선안은 ⑦(2회차)이 `check_ac.py`가 읽는 줄(`종료 코드:` · `## stdout` · `FAILED|ERROR` · 요약 줄)이
위 세 패턴과 겹치지 않음을 확인했지만, **아직 `evidence.py`에 반영되지 않았다.**

## 검증

해당 없음 — 아직 코드가 바뀌지 않았다.

## 재발 방지

- 지금까지 추가된 것: `.claude/harness-notes.md`에 H1(도구 — `evidence.py` 로그 마스킹)과
  H7(`agents/planner.md` · `agents/broker-builder.md` "하지 말 것"에 "비밀이 들어갈 수 있는 값을
  명령 줄에 인라인하지 않는다") 제안이 `2026-09-29 1. 데이터 모델 (1차) (작업 C)` 절로 기록됐다.
- **미반영:** `evidence.py` 자체의 마스킹 로직, `--tb=short` 보조안 적용 여부.
- 이번 작업(작업 C)의 증거 로그 두 건(`92-mut-ac-red.log`, `127-ac4-db-down.log`)은 개발용
  고정값이라 그대로 두었다(이 사실을 사용자에게 보고함).

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [work-items/20260929-data-model/index.md](../work-items/20260929-data-model/index.md)
- [guard-test-destroyed-the-resource-it-guards.md](guard-test-destroyed-the-resource-it-guards.md) — 같은 작업에서 발견된 별도 문제
