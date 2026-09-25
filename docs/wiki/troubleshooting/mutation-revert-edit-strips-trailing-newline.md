# 변이 되돌림 Edit가 파일 끝 개행 문자를 함께 지움

> 요약
> - 한 줄 해결: 변이를 적용하기 전에 대상 파일의 사본을 스크래치 폴더에 두고, 되돌릴 때는 삽입 내용을 Edit로 다시 지우는 대신 그 **사본으로 덮어쓴다**. 이번에는 `printf '\n' >> policies/authz.rego`로 개행 1글자를 복원해 즉시 해결했다.
> - 원인: "역방향 Edit"(삽입한 블록을 사람이 다시 지우는 편집)은 삽입 전 파일과 바이트 단위로 같아진다는 보장이 없다 — 특히 파일 끝 개행·빈 줄이 어긋나기 쉽다.
> - 재발 방지: `agents/broker-builder.md`·`agents/planner.md`에 "변이 전 사본을 만들고 되돌릴 때는 사본으로 덮어쓴다(`cp`). 역방향 Edit·`git checkout`·`git restore`는 쓰지 않는다" 추가 제안(H11, 사용자 결정 대기).

| 발생일 | 분류 | 상태 | 발견 경로 | 관련 원칙 |
|---|---|---|---|---|
| 2026-09-25 | 구현 | 해결(자체 발견·자체 수정) | ③ 구현(개선 사이클2) 중 직접 발견 | 원칙 7 (재현 가능한 증거) |

## 증상

변이 s(`opa.runtime().env.BROKER_DEV` 개발용 우회 규칙 추가)를 되돌리는 Edit에서, 추가했던 규칙 블록 앞의 빈 줄 두 개만 지우려다 파일 끝 개행 문자(EOF newline)까지 함께 지워졌다. `build-mut-s-green`의 정책 해시가 기준선과 달랐다.

```
$ sha256sum policies/authz.rego
bdf19fdd...  policies/authz.rego   # 기대: e2acae2792224c0d3a0053e000acf2736cb3c3df0229d95bef9c38cb1e597723
$ git diff policies/authz.rego
\ No newline at end of file
```

## 재현 방법

1. 정책 파일에 여러 줄(빈 줄 포함)을 Edit으로 삽입한다(변이 적용).
2. 삽입한 텍스트를 Edit의 `old_string`/`new_string`으로 정확히 되짚어 지운다(역방향 Edit).
3. 원본에 있던 파일 끝 개행이 삽입·삭제 경계에 걸려 있으면, 되돌린 결과의 해시가 원본과 달라질 수 있다.

## 원인

1. 직접 원인: 되돌리는 Edit의 `old_string`/`new_string` 경계가 삽입한 빈 줄 두 개와 파일 끝 개행 사이를 정확히 나누지 못해, 개행 문자 하나가 함께 지워졌다.
2. 왜? → 계획(`01-plan.r2.md` 304행)은 변이 절차에 "되돌림"이라고만 적었고 **되돌리는 방법**(어떤 도구로, 어떻게 바이트 단위로 복원하는지)을 정하지 않았다.
3. 근본 원인: "역방향 Edit"은 본질적으로 사람(또는 에이전트)이 삽입한 내용을 기억해 다시 지우는 편집이라, 삽입·삭제 경계의 공백·개행이 원본과 정확히 일치한다는 보장이 없다. 반면 `sha256sum` 기반 해시 대조(green 단계에서 baseline과 비교)라는 안전장치가 이미 계획에 있었기 때문에 실수는 즉시 드러났다.

## 해결

`git diff`로 "No newline at end of file"을 확인해 원인을 특정하고, 파일 끝에 개행 한 글자만 추가해 복원했다(파일 내용 자체를 바꾸는 것이 아니라 직전 Edit이 실수로 지운 개행 한 글자를 복원하는 조치라 별도 evidence 라벨을 만들지 않고 03-build-notes.c2.md에 기록만 남겼다).

```bash
printf '\n' >> policies/authz.rego
sha256sum policies/authz.rego   # e2acae27... (기준선과 일치)
```

## 검증

- 복구 직후 `build-mut-s-green`(로그 225)에서 정책 해시가 기준선(`e2acae27…`)과 일치함을 확인.
- 이후 모든 green 로그(226–238)와 `build-green-final`(238)까지 정책 해시가 계속 기준선과 같음을 확인.
- ④(사이클2) 검토자가 "결과는 보호된 로그가 증명한다: green·green-final·현재 파일이 전부 기준선과 같은 해시"라고 확인하고 "문제없음"으로 판정(자기 발견·자기 수정으로 은폐가 아님).

## 재발 방지 (제안, 사용자 결정 대기)

- **H11** — `agents/broker-builder.md` "작업 순서": "변이를 적용하기 전에 대상 파일의 사본을 스크래치 폴더에 둔다(`cp policies/authz.rego <스크래치>/authz.rego.orig`). 되돌릴 때는 **그 사본으로 덮어쓴다**(`cp <스크래치>/authz.rego.orig policies/authz.rego`). 삽입한 내용을 Edit으로 다시 지우는 역방향 편집은 하지 않는다. `git checkout`·`git restore`로 되돌리지 않는다(커밋 전 변경까지 사라진다). 되돌린 결과는 green 로그의 해시가 기준선과 같은지로 확인한다. 사본은 지우지 않고 경로만 03에 적는다."
- `agents/planner.md` ① "변이 확인" 단락: "변이 절차에 되돌림 방법(사본 덮어쓰기)과 사본 경로를 적는다."

## 재발 기록

| 날짜 | 작업 항목 | 메모 |
|---|---|---|

## 관련

- 작업 페이지: [개요](../work-items/20260925-rego-policy/index.md) · [테스트 기록](../work-items/20260925-rego-policy/testing.md)
