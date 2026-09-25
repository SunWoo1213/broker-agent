# Windows Git Bash가 컨테이너 안 절대경로를 Windows 경로로 잘못 변환함

> 요약
> - 한 줄 해결: 컨테이너 내부 절대경로(`/opa`, `/policies`)를 인자로 넘기는 명령 앞에 `MSYS_NO_PATHCONV=1`을 붙여 Git Bash의 경로 변환을 끈다.
> - 원인: MSYS(Git Bash)가 유닉스 스타일 절대경로를 로컬 프로그램용으로 자동 변환하는데, `docker exec`처럼 인자를 컨테이너 안으로 그대로 전달해야 하는 명령에도 적용돼 인자가 깨졌다.
> - 재발 방지: `04-code-review.md`가 이를 "권한 우회가 아닌 환경 변수"로 명시 판정. `agents/broker-builder.md`·`test-verifier.md`에 한 줄 추가하는 안(H4·H5)은 아직 미반영.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 환경 | 해결 | 구현(③) 중 직접 발견 | — |

## 증상

Windows에서 Bash 도구는 Git Bash(MSYS)인데, `docker compose exec opa /opa ...`, `docker compose run --rm opa test /policies` 처럼 컨테이너 **안**의 절대경로(`/opa`, `/policies`)를 인자로 넘기면 MSYS가 이를 Windows 경로로 자동 변환해 `docker exec`·`docker run` 인자가 깨졌다.

## 재현 방법

1. Windows + Git Bash 환경에서
2. `docker compose exec <서비스> /opa version` 처럼 `/`로 시작하는 컨테이너 내부 경로를 인자로 전달
3. MSYS의 경로 변환기가 `/opa`를 `C:/Program Files/Git/opa` 류의 호스트 경로로 바꿔 컨테이너 안에서 찾을 수 없는 경로가 됨

## 원인

1. 직접 원인: MSYS(Git Bash)는 유닉스 스타일 절대경로를 기본적으로 Windows 경로로 변환하는 호환성 기능을 갖고 있다.
2. 왜? → 이 변환은 Git Bash에서 실행되는 로컬 프로그램을 위한 것인데, `docker exec`처럼 인자를 그대로 컨테이너 안으로 전달해야 하는 명령에는 적용되면 안 된다. 하네스 문서 어디에도 Windows의 Bash 도구가 Git Bash라는 사실과 이 특성이 기록되어 있지 않았다.
3. 근본 원인: 하네스가 크로스플랫폼 셸 차이를 문서화하지 않아 매번 같은 문제로 시간을 쓰거나, 낯선 사람이 보면 "명령을 임의로 바꾼 것"(우회)으로 오해할 수 있는 상태였다.

## 해결

- 실행 시 환경 변수 `MSYS_NO_PATHCONV=1`을 명령 앞에 붙여 경로 변환을 끈다. 파일은 건드리지 않고 실행 방법만 조정한다.
  ```
  MSYS_NO_PATHCONV=1 docker compose exec opa /opa version
  MSYS_NO_PATHCONV=1 docker compose run --rm opa test /policies -v
  ```
- `04-code-review.md`가 이를 "권한 우회가 아니라 Git Bash의 경로 변환을 끄는 환경 변수"로 명시적으로 적절하다고 판정했다 (BLOCK 사유 세 건과 분리해서 다뤘다).

## 검증

- `03-build-notes.md`: AC10(`docker compose run --rm opa test /policies -v` → `PASS: 1/1`), AC7의 `docker compose exec opa /opa version` → `Version: 1.20.2`가 `MSYS_NO_PATHCONV=1`로 정상 실행됨을 확인.
- `05-test-report.md`: 같은 방식으로 재실행해 동일하게 통과.

## 재발 방지

- `06-improvement-plan.md` H4(미반영, 제안 상태): `agents/broker-builder.md`·`agents/test-verifier.md`에 "Windows의 Bash 도구는 Git Bash(MSYS)다. 컨테이너 안 절대경로를 인자로 넘길 때는 `MSYS_NO_PATHCONV=1`을 붙인다. 이것은 경로 변환을 끄는 설정이지 권한 우회가 아니다" 한 줄 추가.
- `06-improvement-plan.md` H5(미반영, 제안 상태): planner가 완료 조건 명령을 적을 때 셸 중립 형태를 우선하고, 셸 전용 명령이 필요하면 실제 쓰는 Bash(Git Bash) 기준으로 적고 `MSYS_NO_PATHCONV=1`을 함께 적는다. (이번엔 계획이 PowerShell 명령으로 AC를 적었는데 ③·⑤는 Bash 명령(`grep -c`, `sha256sum`)으로 실행해 AC 원문과 실제 실행 명령이 달라졌다.)

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|
| 2026-09-25 | 4. 정책 (Rego) (작업 D) · ④ 탐침 로그 248 | reviewer가 개선 사이클2에서 정책 약화 탐침(scratchpad 사본 마운트)을 `docker compose run --rm -v <사본>:/probe:ro`로 실행했는데, Git Bash가 `/probe`를 `C:/Program Files/Git/probe`로 변환해 OPA가 파일을 못 읽고 무효 실행(로그 248)이 됐다. `MSYS_NO_PATHCONV=1`을 붙여 249로 재실행해 정상 동작. 원인은 `MSYS_NO_PATHCONV=1` 안내가 `agents/broker-builder.md`·`test-verifier.md`에만 있고 `agents/reviewer.md`·`skills/code-review-invariants/SKILL.md`(탐침 D4)에는 없었기 때문(하네스 문서 확산 누락). 하네스 개선안 H12-3(제안, 사용자 결정 대기): reviewer 문서와 code-review-invariants D4에 같은 안내를 추가. 상세: [work-items/20260925-rego-policy](../work-items/20260925-rego-policy/testing.md#변이별-결과-사이클2-라벨-build-mut-x-redgreen) |

## 관련

- 작업 페이지: [개요](../work-items/20260924-dev-env/index.md) · [검증 기록](../work-items/20260924-dev-env/verification.md)
- 재발: [4. 정책 (Rego) (작업 D)](../work-items/20260925-rego-policy/index.md)
