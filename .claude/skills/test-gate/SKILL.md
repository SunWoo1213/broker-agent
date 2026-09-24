---
name: test-gate
description: ⑤ 테스트 단계의 실행 절차와 합격 기준. test-verifier가 테스트를 돌리고 완료 조건과 대조할 때 사용한다.
---

# ⑤ 테스트 합격 기준

## 증거 규칙 (모든 절차에 우선)

"실행했다"는 서술은 근거가 아니다. **아래 절차의 명령은 전부 증거 도구로 실행한다.**

```bash
.venv/Scripts/python .claude/tools/evidence.py <run 폴더> <라벨> "<명령>"
```

- 로그는 `<run 폴더>/evidence/NN-<라벨>.log`에 남는다. 시작 · 끝 시각, git HEAD, 명령 원문, 종료 코드, stdout · stderr 전체가 들어간다. `MANIFEST.tsv`에는 sha256이 기록된다.
- pytest는 `--junitxml=<run 폴더>/evidence/pytest-<라벨>.xml`도 함께 남긴다.
- 리포트의 모든 숫자 · 판정 · AC 결과는 **증거 파일 이름**을 가리킨다. 증거 파일이 없는 AC는 "미확인"이고 REVISE 사유다.
- 실패한 실행의 로그도 지우거나 덮어쓰지 않는다. 재실행하면 새 번호로 쌓인다.
- 리포트를 쓰기 직전에 `python .claude/tools/evidence.py <run 폴더> --verify`를 실행하고, 그 출력도 리포트에 붙인다. "변조됨" · "없음"이 하나라도 있으면 BLOCK이다.
- 권한 규칙(ask · deny) 대상 명령(`curl`, `docker run`, 삭제 등)은 evidence.py가 거부한다(종료 코드 126). 이런 명령이 꼭 필요하면 도구 없이 직접 실행해 사람 확인을 받고, 출력을 `<run>/evidence/raw-<라벨>.txt`로 저장한 뒤 `evidence.py <run> <라벨> "cat <그 파일>"`로 기록한다. 거부를 피하려고 명령을 다른 형태로 바꾸지 않는다.
- 사람이 확인한 항목(사용자 확인)은 사용자 답 원문과 시각을 적는다. 오케스트레이터가 전달한 답이면 `00-approval.md`의 해당 줄을 가리킨다.

## 절차

1. 환경 확인: `docker compose ps`로 postgres · redis · opa 상태를 기록한다. 꺼져 있으면 `docker compose up -d`로 켠다.
2. 전체 실행 (변경 파일만이 아니라 전체):
   - `python -m pytest -q` (통합 테스트 포함 시 `-m "integration or not integration"`)
   - `opa test policies -v` (로컬 opa가 없으면 `docker compose run --rm opa test /policies -v`)
3. 불안정성 확인: 이번에 새로 추가된 테스트만 3회 반복 실행 (`python -m pytest <파일들> -q --count=3` 또는 셸 반복). 한 번이라도 결과가 다르면 flaky.
4. 의존성 중단 테스트가 계획에 있으면: `docker compose stop <서비스>` → 해당 테스트 → `docker compose start <서비스>`. **start를 빠뜨리지 않는다.**
5. 완료 조건 대조표를 만든다.

## 산출물: `05-test-report.md`

```markdown
VERDICT: APPROVE | REVISE | BLOCK
# 테스트 리포트
## 환경
- 커밋/작업 트리 상태, 서비스 상태, 실행한 명령
## 결과 요약
- pytest: 통과 N / 실패 N / 건너뜀 N
- opa test: PASS N / FAIL N
- flaky: 없음 / 목록
## 완료 조건 대조
| AC | 확인한 테스트 | 결과 | 증거 파일 (evidence/…) |
## 증거 무결성 (`evidence.py --verify` 출력 원문)
## 실패 상세 (실패한 것만, 출력 원문 발췌 + 증거 파일)
```

## 판정 기준

| 조건 | 판정 |
|---|---|
| 전부 통과 + 모든 AC에 통과한 테스트와 증거 파일이 대응 + flaky 없음 + `--verify` 전부 일치 | APPROVE |
| 증거 파일이 없는 AC가 있음 | REVISE |
| `--verify`에 "변조됨" · "없음"이 있음 | BLOCK |
| 실패 · flaky 있음, 또는 테스트가 없는 AC가 있음 | REVISE |
| 건너뜀(skip)이 이번 변경으로 늘었음, 또는 기존에 통과하던 테스트가 삭제됨 | BLOCK |
| 환경 문제로 실행 자체를 못 함 (Docker 미기동 등) | BLOCK (사람이 환경 확인) |
