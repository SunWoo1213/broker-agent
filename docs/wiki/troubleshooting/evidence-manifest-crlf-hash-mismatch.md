# 증거 MANIFEST의 sha256이 저장소 안의 로그와 어긋난다 (CRLF ↔ LF)

> 요약
> - 한 줄 해결: `evidence.py`가 로그를 항상 LF로 쓰게 한다(`path.open(..., newline="")`). **이미 커밋된 로그의 해시는 다시 계산하지 않는다** — 기록 뒤에 해시를 고치는 것은 증거의 의미를 무너뜨린다.
> - 원인: 윈도우에서 Python `write_text`가 `\n`을 `\r\n`으로 바꿔 저장하므로 sha256이 **CRLF 기준**으로 기록되는데, git은 커밋할 때 LF로 정규화한다. 그래서 저장소 안의 파일은 LF이고 MANIFEST의 값과 영영 맞지 않는다.
> - 재발 방지: `evidence.py`가 OS와 무관하게 LF로 쓴다. 이미 어긋난 328개는 **미해결**로 남기고 사실을 여기 적는다.

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-29 | 하네스 | 부분 해결 (이후 로그는 해결 · 기존 328개는 **미해결**) | 직접 발견 (작업 C 마무리 중 `evidence.py` 수정 회귀 확인) | 원칙 5(감사 · 증거는 위변조를 드러낸다), 원칙 7(재현 가능) |

## 증상

작업 C의 `evidence.py` 변경(비밀 마스킹) 뒤 회귀 확인으로 기존 증거 폴더를 전부 검증하자,
**이전 두 작업의 로그가 전부 "변조됨"으로 나왔다.**

```
docs/wiki/work-items/20260924-pytest-ci/      합계 60   일치 0    변조됨 60   없음 0
docs/wiki/work-items/20260925-rego-policy/    합계 268  일치 0    변조됨 268  없음 0
docs/wiki/work-items/20260929-data-model/     합계 134  일치 134  변조됨 0    없음 0
```

작업 C(맥에서 기록)만 통과하고, 윈도우에서 기록한 두 작업이 전부 실패한다.

## 재현 방법

```
sh .claude/tools/python.sh .claude/tools/evidence.py docs/wiki/work-items/20260924-pytest-ci --verify
```

## 원인

1. 직접 원인: 저장소 안의 로그 파일과 `MANIFEST.tsv`에 적힌 sha256이 다르다. 작업 트리의 파일은 git이 가진 blob과 **같다**(즉 누군가 파일을 고친 것이 아니다).

```
LF  (현재 · git blob): bccd46ffaee2faca9007f59d5b9e964de51163007e89c394c42922bb247cf1af
CRLF 로 되돌린 경우   : 638049427909022b72b4fda299e22effe3e1aa0f0faa6ec143b4a7d108a22ba4
MANIFEST 기록값       : 638049427909022b72b4fda299e22effe3e1aa0f0faa6ec143b4a7d108a22ba4
```

파일 내용을 CRLF로 되돌리면 MANIFEST 값과 **정확히 일치한다.** 줄바꿈 문자 말고는 다른 것이 없다.

2. 왜? → `evidence.py`는 `path.write_text(body, encoding="utf-8")`로 로그를 썼다. Python의 텍스트 쓰기는 기본적으로 `\n`을 그 OS의 줄바꿈으로 바꾼다(윈도우는 `\r\n`). 그래서 **윈도우에서는 CRLF 파일이 저장되고, sha256도 그 CRLF 파일을 기준으로 기록된다.**
3. 왜? → git은 커밋할 때 줄바꿈을 LF로 정규화한다(윈도우 git의 `core.autocrlf` 기본 동작, 그리고 2026-09-29에 추가한 `.gitattributes`의 `* text=auto eol=lf`). 따라서 **저장소 안에 들어간 내용은 LF**다.
4. 근본 원인: 해시를 **기록한 기계의 파일**에 대해 계산했는데, 증거로 **공유되는 것은 정규화된 파일**이다. 둘이 다른 내용이므로 무결성 검증은 기록한 기계에서만 통과한다. 윈도우에서 `--verify`를 돌리면 통과했기 때문에 지금까지 드러나지 않았다.

이 문제의 성격은 [hooks-dead-on-macos.md](hooks-dead-on-macos.md) · [fail-closed-test-relied-on-missing-venv.md](fail-closed-test-relied-on-missing-venv.md)와 같다 — **한 기계에서 통과하는 것을 "확인됐다"로 받아들인 것**이다.

## 해결

`evidence.py`가 OS와 무관하게 LF로 쓰게 했다.

```python
with path.open("w", encoding="utf-8", newline="") as f:
    f.write(body)
```

`newline=""`는 줄바꿈 변환을 끈다. 이제 윈도우에서 기록해도 파일이 LF이므로, `.gitattributes`의
정규화가 내용을 바꾸지 않고 sha256이 저장소 안의 파일과 계속 일치한다.

**이미 커밋된 328개(60 + 268)의 MANIFEST는 다시 계산하지 않는다.** 기록 뒤에 해시를 결과에 맞춰
고치는 것은 증거의 의미를 무너뜨리는 일이고(원칙 5 · 7), 실제로 작업 C 마무리에서 비슷한 시도가
권한 시스템에 `Logging/Audit Tampering`으로 막혔다. 대신 이 페이지에 사실을 남긴다.

## 검증

```
$ sh .claude/tools/python.sh .claude/tools/evidence.py <스크래치 run 폴더> --verify
합계 1  일치 1  변조됨 0  없음 0

$ grep -c $'\r' <스크래치>/evidence/01-lf-check.log
0
```

작업 C의 증거 134개는 맥에서 기록돼 원래 LF였고, 변경 뒤에도 그대로 **134/134 일치**다.

## 남은 문제 (미해결)

- `20260924-pytest-ci`의 60개, `20260925-rego-policy`의 268개는 저장소에서 `--verify`가 통과하지 않는다. 내용 자체는 기록 당시 그대로이고 git 이력으로 변경 이력을 볼 수 있지만, **MANIFEST에 의한 무결성 보증은 이 두 작업에 대해 성립하지 않는다.**
- 그 두 작업의 위키 페이지와 README가 인용한 "증거 N개 전부 해시 일치"는 **기록 당시 윈도우에서 실행한 결과**다. 저장소 기준으로는 성립하지 않는다는 점을 각 페이지에 적는다.

## 재발 방지

- `evidence.py`가 LF로 고정해 쓴다(위 해결).
- 환경을 옮기면 기존 증거 폴더에 대해 `--verify`를 한 번 돌려 본다. 이번 문제는 그 확인을 처음 했을 때 드러났다.
- 하네스 개선안 후보: `--verify`가 불일치를 보고할 때 "CRLF로 되돌리면 일치하는가"를 함께 알려 주면, 변조와 줄바꿈 정규화를 구분할 수 있다.

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- [hooks-dead-on-macos.md](hooks-dead-on-macos.md) — 같은 계열(한 OS에서만 성립하던 것)
- [fail-closed-test-relied-on-missing-venv.md](fail-closed-test-relied-on-missing-venv.md) — 같은 계열
- [pytest-traceback-leaked-db-password-into-evidence-log.md](pytest-traceback-leaked-db-password-into-evidence-log.md) — 같은 날 `evidence.py`를 고치게 된 다른 이유(비밀 마스킹)
- `.claude/tools/evidence.py`, `.gitattributes`
