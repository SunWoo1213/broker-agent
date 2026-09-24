---
name: test-gate
description: ⑤ 테스트 단계의 실행 절차와 합격 기준. test-verifier가 테스트를 돌리고 완료 조건과 대조할 때 사용한다.
---

# ⑤ 테스트 합격 기준

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
| AC | 확인한 테스트 | 결과 |
## 실패 상세 (실패한 것만, 출력 원문 발췌)
```

## 판정 기준

| 조건 | 판정 |
|---|---|
| 전부 통과 + 모든 AC에 통과한 테스트가 대응 + flaky 없음 | APPROVE |
| 실패 · flaky 있음, 또는 테스트가 없는 AC가 있음 | REVISE |
| 건너뜀(skip)이 이번 변경으로 늘었음, 또는 기존에 통과하던 테스트가 삭제됨 | BLOCK |
| 환경 문제로 실행 자체를 못 함 (Docker 미기동 등) | BLOCK (사람이 환경 확인) |
