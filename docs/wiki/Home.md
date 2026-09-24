# 에이전트 권한 브로커 — 개발 위키

> 작업 하나가 어떻게 진행됐는지, 어떤 문제가 있었고 어떻게 풀었는지를 기록한다.
> 기록 규칙: `.claude/skills/dev-wiki/SKILL.md` · 템플릿: [`_templates/`](_templates/)
> 설계는 [`docs/architecture.md`](../architecture.md), 결정은 [`docs/decisions.md`](../decisions.md), 계획은 [`docs/plan.md`](../plan.md)

## 개발 프로세스

상세 설명: **[process.md](process.md)** — 단계별 담당 · 통과 기준 · 검증과 테스트의 차이 · 안전장치

작업 하나는 `/work-item <plan.md 항목>`으로 진행하고, 끝나거나 중단되면 이 위키에 기록된다.

```
①계획 → ②계획 검증 → 🧑승인 → ③구현 → ④구현 검증 → ⑤테스트 → ⑥개선사항 계획 → ⑦개선 계획 검증 → 📝위키 기록 → 🧑커밋 승인
```

## 진행 현황

| 단계 | 목표 | 상태 |
|---|---|---|
| 0 | 개발 하네스 | 완료 |
| 1 | 게이트웨이 ①②③⑦ + 모의 도구 + 데모 에이전트 | 진행 중 (0. 개발 환경 — venv·버전 고정·compose 기동 완료, pytest·CI 대기) |
| 2 | 승인, 임시 토큰 | 대기 |
| 3 | 누적 한도, 동시성, 공격 평가 1차 | 대기 |
| 4 | 감사 로그, 취소 전파 | 대기 |
| 5 | AWS · Terraform, 부하 테스트 | 대기 |
| 6 | 수치 정리, 시연 | 대기 |

## 작업 로그

| 날짜 | 항목 | 결과 | 관문 재시도 | 기록 |
|---|---|---|---|---|
| 2026-09-24 | 개발 하네스 구성 | 완료 | — | [개요](work-items/20260924-harness-setup/index.md) · [검증](work-items/20260924-harness-setup/verification.md) · [테스트](work-items/20260924-harness-setup/testing.md) |
| 2026-09-24 | 0. 개발 환경 — 가상환경 · 버전 고정 · compose 기동 | 완료 | ② 2회 · ④ 1회(BLOCK→사람 해제) | [개요](work-items/20260924-dev-env/index.md) · [검증](work-items/20260924-dev-env/verification.md) · [테스트](work-items/20260924-dev-env/testing.md) |

## 문제 해결

| 날짜 | 문제 | 분류 | 상태 | 페이지 |
|---|---|---|---|---|
| 2026-09-24 | 승인 훅이 인코딩 오류로 죽으면서 명령을 통과시킴 (fail-open) | 하네스 | 해결 | [링크](troubleshooting/hook-cp949-fail-open.md) |
| 2026-09-24 | 호스트 PostgreSQL 포트 5433이 다른 프로젝트 컨테이너와 충돌 | 환경 | 해결 | [링크](troubleshooting/host-port-5433-conflict.md) |
| 2026-09-24 | 서브에이전트가 권한 시스템 거부 명령을 다른 명령·도구로 우회 | 하네스 | 해결(사람 확인 후 규칙 추가) | [링크](troubleshooting/subagent-permission-bypass.md) |
| 2026-09-24 | 임시 폴더 삭제가 ask 규칙에 걸려 확인 요청이 반복됨 | 하네스 | 해결(정책 결정: 삭제 단계 제거) | [링크](troubleshooting/delete-ask-repeated-prompt.md) |
| 2026-09-24 | Windows Git Bash가 컨테이너 안 절대경로를 Windows 경로로 잘못 변환 | 환경 | 해결(`MSYS_NO_PATHCONV=1`) | [링크](troubleshooting/msys-pathconv-windows.md) |
