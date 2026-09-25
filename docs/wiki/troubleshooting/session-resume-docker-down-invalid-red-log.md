# 세션 재개 때 Docker Desktop이 꺼져 있어 무효 red 로그가 남음

> 요약
> - 한 줄 해결: 세션을 시작·재개할 때 파일 해시 확인과 함께 `docker compose ps`를 evidence로 기록하고, 서비스가 healthy가 아니면 변이·테스트를 실행하지 않는다. 이번에는 Docker Desktop을 evidence 밖에서 기동한 뒤 재실행해 해결했다.
> - 원인: red 증거의 판정 기준이 "종료 코드 ≠ 0"뿐이라, 인프라(Docker) 오류로 인한 실패와 의도한 테스트 실패가 겉보기에 같은 신호(≠0)를 낸다. 채점기(`ac_build_evidence.py`)는 라벨의 마지막 로그만 보므로, 무효 로그가 마지막이었어도 결국 BAD(닫히는 방향)였겠지만 판정 위험은 없었다.
> - 재발 방지: red·탐침 로그에 테스트 러너의 결과 요약 줄(`opa test`의 `PASS:`/`FAIL:` 줄, pytest 요약 줄)이 없으면 "무효 실행"으로 규정하고 다시 실행한다(H12, 사용자 결정 대기).

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-25 | 환경 | 해결 | ③ 구현(개선 사이클2, 세션 재개) 중 직접 발견 | 원칙 1 (fail-closed) |

## 증상

개선 사이클2 ③이 이전 세션에서 중단된 뒤(절차 1–3, 변이 a–l까지 완료), 새 세션이 세 파일 해시만 확인하고 변이 m부터 이어서 진행했다. 변이 m red를 처음 실행했을 때(로그 211) Docker Desktop이 꺼져 있어 OPA 컨테이너가 뜨지 않았다.

```
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine
```

종료 코드는 0이 아니었으므로(`exit=1`) 겉보기에는 "정상적인 red"와 구분되지 않았다.

## 재현 방법

1. 여러 세션에 걸친 작업(개선 사이클 등)에서, 이전 세션이 끝난 뒤 Docker Desktop을 종료한다.
2. 새 세션이 파일 해시만 확인하고(서비스 상태는 확인하지 않고) `docker compose run --rm opa test /policies -v`를 실행한다.
3. Docker 연결 오류로 명령이 실패하는데, 종료 코드가 0이 아니라는 점만으로는 "의도한 정책 테스트 실패(red)"와 구분할 수 없다.

## 원인

1. 직접 원인: 세션 재개 절차가 "세 파일 해시가 이전 baseline과 같은가"만 확인했고, **실행 환경(compose 서비스 상태)은 확인하지 않았다.**
2. 왜? → red 판정 기준이 "종료 코드 ≠ 0"뿐이라, 환경 오류(Docker 꺼짐)도 겉보기에는 red와 같은 신호를 낸다.
3. 근본 원인: 채점기(`ac_build_evidence.py`)는 변이 red에서 "계획한 테스트가 FAIL 목록에 있는가"를 요구하는데, Docker가 꺼진 로그에는 애초에 `opa test`의 `PASS:`/`FAIL:` 요약 줄 자체가 없다. 이 요약 줄의 유무를 "실행이 유효했는가"의 신호로 쓰는 규칙이 없었다.

## 해결

evidence.py 밖에서 Docker Desktop을 기동하고 준비될 때까지 대기한 뒤 재실행했다(권한 규칙이 막은 것이 아니라 인프라가 꺼져 있었을 뿐이며, `docker compose` 자체는 계획이 이미 허용한 명령이다).

```bash
"/c/Program Files/Docker/Docker/Docker Desktop.exe"
# docker info가 성공할 때까지 폴링
docker info
```

이후 변이 m red를 같은 라벨로 다시 실행(로그 212, 유효)했다. 무효 로그 211은 지우지 않고 03-build-notes.c2.md에 원인과 함께 기록했다.

## 검증

- 로그 212에서 `opa test`가 정상 실행돼 `PASS: 46/54, FAIL: 8/54`(계획과 정확히 일치)를 확인.
- `ac_build_evidence.py`(`_ev.last()`)가 라벨의 **마지막** 로그(212)만 채점 대상으로 봄을 확인 — 로그 211은 판정에 영향을 주지 않았다.
- ④(사이클2) 검토자가 "무효 로그가 마지막이었어도 채점기는 `PASS:`/`FAIL:` 요약 줄을 요구하므로 BAD(닫히는 방향)가 됐을 것"이라고 확인해 판정 위험이 없었음을 재확인.

## 재발 방지 (제안, 사용자 결정 대기)

- **H12(1)** — `agents/broker-builder.md` "작업 순서"·`agents/test-verifier.md` "절차": "세션을 시작하거나 재개할 때, 파일 해시 확인과 함께 `docker compose ps`를 evidence.py로 기록한다. 서비스가 healthy가 아니면 변이·테스트를 실행하지 않는다. 환경을 복구하는 명령(Docker Desktop 기동 등)을 evidence 밖에서 실행했다면 원문을 03·05에 적는다."
- **H12(2)** — `agents/broker-builder.md`·`skills/code-review-invariants/SKILL.md` D4: "red·탐침 로그에 테스트 러너의 결과 요약 줄(opa `PASS:`/`FAIL:` 줄, pytest 요약 줄)이 없으면 **무효 실행**이다. 종료 코드가 0이 아니어도 red 증거로 쓰지 않는다. 무효 로그 번호와 이유를 03·04에 적고 같은 라벨로 다시 실행한다(채점은 마지막 로그)."

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [개요](../work-items/20260925-rego-policy/index.md) · [테스트 기록](../work-items/20260925-rego-policy/testing.md)
