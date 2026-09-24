# 승인 훅이 Windows 인코딩 오류로 죽으면서 명령을 그대로 통과시킴 (fail-open)

> 요약
> - 한 줄 해결: 훅 출력을 `ensure_ascii=True`로 내보내고, 입력 해석 실패와 최상위 예외를 전부 `permissionDecision: "ask"`로 처리한다.
> - 원인: cp949 콘솔에 없는 문자(em dash)를 출력하려다 `UnicodeEncodeError`가 나고, Claude Code는 훅이 예외로 끝나면 차단 신호로 보지 않고 도구 호출을 그대로 진행한다.
> - 재발 방지: `guard_paths.py`도 처음부터 ASCII 출력·"예외=deny" 구조로 작성. `settings.json`의 `permissions.ask`를 두 번째 방어선으로 추가.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-24 | 하네스 | 해결 | 훅 파이프 테스트 (직접 발견) | 원칙 1 (fail-closed) |

## 증상

`git commit`, `git push` 같은 명령에 사람 승인을 요구하도록 만든 PreToolUse 훅(`.claude/hooks/guard_critical.py`)에 테스트 입력을 넣자, 걸려야 할 명령마다 훅이 예외로 종료했다.

```
UnicodeEncodeError: 'cp949' codec can't encode character '—' in position 142: illegal multibyte sequence
```

같은 테스트에서 출력 결과는 `(pass)`, 즉 **훅이 아무 판단도 내리지 않은 것**으로 나왔다.

## 재현 방법

1. 한국어 Windows(콘솔 코드 페이지 cp949)에서 Python 3.13으로 훅 실행
2. 표준 입력으로 `{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}` 전달
3. 훅이 `json.dumps(..., ensure_ascii=False)`로 한글과 `—`(U+2014)가 든 사유를 `print` → 예외

## 원인

1. 직접 원인: 표준 출력 인코딩이 cp949인데, cp949에 없는 문자(`—`)를 출력하려 했다.
2. 왜 위험한가? → Claude Code는 훅이 오류로 끝나면 **차단 신호로 보지 않고 도구 호출을 계속 진행**한다. 승인을 요구해야 할 `git push`가 승인 없이 실행될 수 있었다.
3. 근본 원인: 훅의 "판단 실패" 경로를 설계하지 않았다. 판단 로직만 테스트하고 출력 단계가 실패할 수 있다는 가정을 하지 않았다. 브로커의 원칙 1(문제가 생기면 전부 막는다)을 훅 자신에게는 적용하지 않은 셈이다.

## 해결

- 출력은 `ensure_ascii=True`로 ASCII만 내보낸다 (JSON 안에서 `\uXXXX`로 이스케이프되므로 뜻은 같다).
- 입력은 `sys.stdin.buffer`에서 바이트로 읽어 UTF-8로 직접 디코딩한다.
- 입력 해석 실패와 **최상위 예외 모두** `permissionDecision: "ask"`로 처리한다.
- 훅 프로세스 자체가 뜨지 못하는 경우(python 미설치 등)에 대비해 `.claude/settings.json`의 `permissions.ask`에 같은 명령 규칙을 두 번째 방어선으로 추가했다.

```python
if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # 어떤 예외도 "통과"로 새지 않게 한다
        ask(f"[승인 필요] 훅 내부 오류: {exc}")
```

## 검증

테스트 스크립트로 명령 26개 × 도구 2종(Bash, PowerShell) = 52건과 잘못된 입력 3건(JSON 아님, command가 숫자, 한글 UTF-8 명령)을 넣어 기대 판정과 비교했다. 결과는 `FAILURES: 0`, 표준 오류 출력 없음.

## 재발 방지

- 같은 방식의 경로 제한 훅(`guard_paths.py`)도 처음부터 ASCII 출력과 "예외 = deny" 구조로 작성했고, 9건 테스트로 확인했다.
- 교훈: **보안 장치의 실패 경로는 그 장치가 지키는 시스템과 같은 기준(fail-closed)으로 설계하고 테스트한다.** 게이트웨이에서 OPA 연결 실패 테스트를 먼저 쓰는 것과 같은 이유다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [하네스 구성](../work-items/20260924-harness-setup/index.md) · [테스트 기록](../work-items/20260924-harness-setup/testing.md)
