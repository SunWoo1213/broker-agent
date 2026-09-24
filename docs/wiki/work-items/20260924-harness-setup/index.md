# 개발 하네스 구성 (Claude Code 에이전트 팀)

| 날짜 | plan.md 항목 | 결과 | 관문 재시도 | 개선 사이클 |
|---|---|---|---|---|
| 2026-09-24 | 0. 개발 환경 이전 준비 작업 (plan.md 외) | 완료 | 해당 없음 (하네스 구성 전) | 해당 없음 |

## 1. 목표

브로커 코드를 Claude Code 에이전트와 함께 개발하면서도 7개 불변 원칙이 매 작업마다 지켜지게 하는 개발 절차를 만든다.
이 프로젝트가 "에이전트의 행동을 코드로 통제"하듯, 개발에 쓰는 에이전트도 관문과 승인으로 통제한다.

## 2. 설계와 결정

- **7단계 관문:** 계획 → 계획 검증 → 구현 → 구현 검증 → 테스트 → 개선사항 계획 → 개선 계획 검증. 각 검증 문서의 첫 줄 `VERDICT: APPROVE | REVISE | BLOCK`으로만 다음 단계를 정한다. 형식이 틀리면 BLOCK.
  - 이유: 자기 결과물을 스스로 검증하면 같은 맹점을 통과시킨다. 만든 팀원과 검증하는 팀원을 나눴다.
- **모델 배치:** 검증(reviewer) = Fable, 계획 · 공격 평가 = Opus, 구현 · 테스트 실행 · 기록 = Sonnet.
  - 이유: 구현 실수는 뒤의 관문에서 잡히지만, 관문이 놓친 실수는 아무도 잡지 못한다. 가장 강한 모델을 막는 쪽에 뒀다.
  - 버린 대안: 테스트 실행에 Haiku → 사용자 요청으로 Fable · Opus · Sonnet 세 모델만 사용.
- **사람 승인 두 번:** 계획 승인(② 뒤), 커밋 승인(마무리). 커밋 · 푸시 · `terraform apply/destroy` · 볼륨 삭제는 훅이 무조건 승인 창을 띄운다.
- **검증 담당은 쓰기 경로 제한:** reviewer · planner · test-verifier는 `.claude/runs/`에만 쓸 수 있다 (Agent 전용 훅).
- **개발 위키:** 작업마다 `docs/wiki/work-items/<항목>/`에 개요 · 검증 기록 · 테스트 기록을, `troubleshooting/`에 문제 해결 과정을 남긴다. 절차 설명은 [process.md](../../process.md).

> 검증 상세: [verification.md](verification.md) · 테스트 상세: [testing.md](testing.md)

## 3. 진행 기록

하네스를 만드는 작업이라 7단계 관문을 거치지 않았다. 대신 훅은 파이프 테스트로 검증했다.

| 단계 | 결과 |
|---|---|
| 청사진 (역할 · 흐름 설계) | 사용자와 두 차례 수정: 단계별 검증 추가, 모델 배치 · 승인 훅 추가 |
| 훅 파이프 테스트 1차 | 실패 — 인코딩 오류로 fail-open ([문제 해결](../../troubleshooting/hook-cp949-fail-open.md)) |
| 훅 파이프 테스트 2차 | 55건 전부 기대 판정 |
| 경로 제한 훅 테스트 | 9건 전부 기대 판정 |

## 4. 구현 요약

| 파일 | 변경 |
|---|---|
| `.claude/agents/` | planner · reviewer · broker-builder · test-verifier · eval-runner · wiki-writer |
| `.claude/skills/` | work-item(오케스트레이터), broker-invariants, fail-closed-tests, rego-policy, plan-review, code-review-invariants, test-gate, improvement-review, attack-eval, dev-wiki |
| `.claude/hooks/guard_critical.py` | 중요 명령 → 사람 승인 |
| `.claude/hooks/guard_paths.py` | Agent별 쓰기 경로 제한 |
| `.claude/settings.json` | 훅 등록, `permissions.ask` 두 번째 방어선, `.env` 읽기 · 쓰기 금지 |
| `CLAUDE.md` | 하네스 섹션 추가 |
| `docs/wiki/` | Home · process · 템플릿 4종 · 첫 기록 |

## 5. 테스트

- `guard_critical.py`: 명령 26개 × Bash · PowerShell = 52건 + 잘못된 입력 3건 → `FAILURES: 0`
- `guard_paths.py`: 허용 경로, 절대 경로, `..` 우회, 접두사 유사 경로(`.claude/runsX`), 잘못된 입력 등 9건 → `FAILURES: 0`
- 미확인: Claude Code 세션 안에서 훅이 실제로 발동하는지 (세션 재시작 또는 `/hooks` 후 확인 필요)

## 6. 문제 상황과 해결

| 문제 | 분류 | 상태 | 상세 |
|---|---|---|---|
| 승인 훅이 Windows 인코딩 오류로 죽으면서 명령을 통과시킴 | 하네스 | 해결 | [링크](../../troubleshooting/hook-cp949-fail-open.md) |

## 7. 배운 점

- 보안 장치는 판단 로직보다 **판단에 실패했을 때** 어떻게 되는지를 먼저 테스트해야 한다.
- 훅은 한 겹으로 두지 않는다: 훅(정밀한 패턴 판정) + `permissions.ask`(훅이 아예 못 돌 때).

## 8. 관련

- 커밋: (커밋 후 채움)
- 다음 항목: `docs/plan.md` 0. 개발 환경
