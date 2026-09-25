# evidence 로그에서 자식 Python의 한국어 출력이 깨짐 (cp949 → UTF-8)

> 요약
> - 한 줄 해결: `evidence.py`가 자식 프로세스에 `env={**os.environ, "PYTHONIOENCODING": "utf-8"}`를 넘긴다(H13, 2026-09-25 적용). 적용 뒤 로그 stdout에 한국어가 그대로 남는 것을 확인했다. 적용 전 로그(작업 D의 174 · 242 · 261 등)는 해시로 보호되므로 다시 쓰지 않는다.
> - 원인: `evidence.py`가 자식 프로세스(`.venv/Scripts/python checks/...`) stdout을 UTF-8로 디코딩하는데, 자식 Python은 stdout이 파이프일 때 Windows 한국어 로캘 인코딩(cp949)으로 쓴다. `evidence.py`는 자기 자신의 stdout만 재설정했고 자식에게 인코딩을 넘기지 않았다.
> - 재발 방지: H13(도구) + planner "하지 말 것"에 "채점 스크립트가 한국어를 출력하면 `sys.stdout.reconfigure(encoding="utf-8")`" 규칙. 판정 토큰은 ASCII로 둔다.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-25 | 하네스 | 해결 (2026-09-25, H13 적용) | ⑤ 테스트(사이클2) 참고, ⑥ 개선사항 계획(사이클2) 직접 확인 | — |

## 증상

`checks/ac_scope.py`가 콘솔/로그에 출력한 HUMAN 판정 한국어 문구("00-approval.md에 기록됨, 범위 밖으로 처리")가 evidence 로그 파일에서 `U+FFFD`(깨진 문자)로 저장돼 있다.

```
$ sed -n '14p' evidence/261-ac6-scope.log
HUMAN rule4: protected files unchanged: 'docs/decisions.md' (�� ��ϵ�, ...)
```

같은 패턴이 로그 174(사이클1 ⑤ AC6)·242(사이클2 ③ 자기 점검)·261(사이클2 ⑤ AC6)에서 반복 확인됐다 — 사이클1부터 있던 기존 현상이며 이번 작업으로 새로 생긴 것이 아니다.

## 재현 방법

1. 한국어 Windows에서 `.venv/Scripts/python checks/ac_scope.py`처럼 한국어 문자열을 `print`하는 자식 Python 스크립트를, `evidence.py`가 `subprocess.run`으로 파이프 캡처한다.
2. 자식 Python은 stdout이 콘솔이 아니라 파이프이므로 콘솔 UTF-8 처리가 적용되지 않고, 로캘(cp949)로 인코딩한 바이트를 stdout에 쓴다.
3. `evidence.py`는 그 바이트를 `encoding="utf-8", errors="replace"`로 디코딩해 로그에 남긴다 — cp949 바이트가 UTF-8 규칙에 맞지 않는 부분이 `U+FFFD`로 치환된다.

## 원인

1. 직접 원인: `checks/ac_scope.py:66`(원문은 정상 UTF-8 소스 파일)이 한국어 문자열을 출력하는데, 자식 프로세스의 실제 stdout 인코딩은 cp949다.
2. 왜? → `evidence.py`가 `subprocess.run([find_bash(), "-lc", command], ...)`을 부를 때 자식에게 `PYTHONIOENCODING` 등 인코딩 관련 환경 변수를 넘기지 않는다. `evidence.py:124-126`은 **자기 자신의** stdout만 `reconfigure(encoding="utf-8")`했다.
3. 근본 원인: Python은 표준 출력이 터미널(tty)일 때는 OS 콘솔 코드페이지를 존중해 UTF-8로 재구성하는 경우가 있지만, **파이프로 리다이렉트되면** 이 처리가 적용되지 않고 로캘 기본 인코딩(한국어 Windows는 cp949)을 그대로 쓴다.
4. 검증(직접 바이트 대조): "기록됨"을 cp949로 인코딩하면 `B1 E2 B7 CF B5 CA`이고, 이것을 UTF-8 `errors="replace"`로 디코드하면 `��ϵ�`가 나온다 — 로그 261의 해당 자리 원문과 바이트 단위로 일치한다(⑦ 사이클2 검토자가 재확인, `07-improvement-review.c2.md` "직접 확인한 사실"). *(참고: 06-improvement-plan.c2.md는 이 바이트를 `B1 E2 B7 CF B5 C6`로 적었으나 오타이며, 실제는 `B5 CA`다. 결론(cp949 → UTF-8 replace)은 맞다.)*

## 해결

**해결 (2026-09-25, H13 적용 — 사용자 결정: "1,2,3,4번을 진행해주세요").**

- 작업 D 안에서는 판정 토큰(`OK`·`HUMAN`·`BAD`)과 경로가 전부 ASCII라 판정 결과·개수에 영향이 없어, 정책·테스트·`checks/`를 바꾸지 않고 기록만 남겼다.
- 작업 D 마무리 뒤 `.claude/tools/evidence.py`의 자식 실행을 아래처럼 바꿨다. 판정 로직 · 로그 형식 · 권한 필터(ask · deny 규칙 검사)는 그대로다.
  ```python
  proc = subprocess.run([find_bash(), "-lc", command], capture_output=True,
                        text=True, encoding="utf-8", errors="replace",
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
  ```
  `PYTHONUTF8=1`보다 범위가 좁다(표준 입출력만 바뀌고 `open()` 기본값은 그대로).
- 기존 로그는 해시로 보호되므로 다시 쓰지 않는다. 적용 전 로그의 깨짐은 "기존 현상"으로 남는다(F-D9).

## 검증

- ⑤(사이클2)가 참고 사항으로 발견하고 판정에 영향이 없음을 확인(로그 261의 `HUMAN`/`BAD` 개수는 정상).
- ⑥(사이클2)이 바이트 단위로 원인을 재현해 "자식 Python의 파이프 stdout이 cp949로 쓰였다"고 확정.
- ⑦(사이클2)이 06.c2의 바이트 표기 오타(`C6`→`CA`)를 잡아 정정했다.
- **H13 적용 뒤 확인 (2026-09-25, 스크래치 run 폴더 `scratchpad/enc-run`, git 제외 위치):**
  - `python .claude/tools/evidence.py <스크래치 run> enc-check ".venv/Scripts/python -c \"print('\\ud55c\\uae00')\""` → 종료 코드 0, 로그 `01-enc-check.log`의 `## stdout` 아래에 `한글`이 그대로 저장됨.
  - 대조 실험(evidence 밖, 같은 자식 명령을 파이프로 캡처): 환경 변수 없음 → `b'\xc7\xd1\xb1\xdb\r\n'`(cp949), `PYTHONIOENCODING=utf-8` → `b'\xed\x95\x9c\xea\xb8\x80\r\n'`(UTF-8). 원인 분석과 일치.
  - 권한 필터: 같은 폴더에서 `evidence.py … guard-curl "curl --version"` → 종료 코드 126, 거부 메시지 출력, 로그 파일이 생기지 않음(필터 약화 없음).
  - `--verify`(H5 요약 줄 함께 추가): 스크래치 `합계 1  일치 1  변조됨 0  없음 0`. 기존 증거 폴더도 전부 일치 — `docs/wiki/work-items/20260924-pytest-ci` 60/60, `docs/wiki/work-items/20260925-rego-policy` 268/268, `.claude/runs/20260924-pytest-ci` 62/62, `.claude/runs/20260925-rego-policy` 268/268(모두 종료 코드 0).

## 재발 방지

- **H13** (적용됨) — `.claude/tools/evidence.py`가 자식에게 `PYTHONIOENCODING=utf-8`을 넘긴다.
- planner "하지 말 것"(적용됨): "채점 스크립트(`checks/`)가 한국어를 출력하면 첫 부분에서 `sys.stdout.reconfigure(encoding="utf-8")`를 한다. 판정 토큰(`OK` · `BAD` · `HUMAN` · `summary`)은 ASCII로 둔다."
- **F-D9**(후속 항목, 완료): 적용 전 로그의 한국어 깨짐은 "기존 현상"으로만 기록한다.
- 같은 계열의 사례: [hook-cp949-fail-open.md](hook-cp949-fail-open.md) — 다만 그 문제는 훅이 **예외로 죽어 판정 자체가 통과로 새는(fail-open)** 문제였고, 이 문제는 판정에는 영향이 없고 **로그 가독성**만 떨어지는 문제라 성격이 다르다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [개요](../work-items/20260925-rego-policy/index.md) · [테스트 기록](../work-items/20260925-rego-policy/testing.md)
- 관련(다른 성격의 인코딩 문제): [hook-cp949-fail-open.md](hook-cp949-fail-open.md)
