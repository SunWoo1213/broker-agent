# 개발 프로세스

> 이 프로젝트의 코드는 Claude Code 에이전트 팀이 아래 절차로 만든다. 절차 정의의 원본은 `.claude/skills/work-item/SKILL.md`이고, 이 페이지는 사람이 읽기 위한 설명이다.

## 왜 이런 절차인가

브로커는 "에이전트가 무엇을 실행하느냐"를 통제하는 시스템이다. 그 코드를 에이전트와 함께 만들 때도 같은 원리를 적용했다.

- **만드는 쪽과 검증하는 쪽을 나눈다.** 자기 결과물을 스스로 검증하면 같은 맹점을 통과시킨다.
- **판단이 모호하면 통과시키지 않는다.** 검증 문서의 판정 줄이 없거나 형식이 틀리면 BLOCK으로 처리한다 (원칙 1).
- **되돌릴 수 없는 일은 사람이 승인한다.** 커밋 · 푸시 · 인프라 생성 · 삭제는 훅이 항상 승인 창을 띄운다.
- **실패도 기록한다.** 막힌 관문, 실패한 테스트, 미해결 문제를 빼지 않고 위키에 남긴다 (원칙 7).

## 흐름

```
① 계획 ─▶ ② 계획 검증 ─▶ 🧑 계획 승인 ─▶ ③ 구현 ─▶ ④ 구현 검증 ─▶ ⑤ 테스트
            │ REVISE → ①                             │ REVISE → ③      │
                                                                       ▼
                         ┌──── 코드 수정 필요 ◀── ⑦ 개선 계획 검증 ◀── ⑥ 개선사항 계획
                         ▼                               │ 수정 없음
                     ③ 구현 (최대 2사이클)                 ▼
                                               📝 위키 기록 ─▶ 🧑 커밋 승인
```

- REVISE는 같은 관문에서 최대 2회, 개선 사이클도 최대 2회. 넘으면 멈추고 사람에게 보고한다.
- BLOCK이 나오면 즉시 멈추고, 그 시점까지의 기록을 위키에 `중단`으로 남긴다.

## 단계별 담당과 기준

| 단계 | 담당 (모델) | 산출물 | 통과 기준 (체크리스트) |
|---|---|---|---|
| ① 계획 | planner (Opus) | `01-plan.md` | — |
| ② 계획 검증 | reviewer (Fable) | `02-plan-review.md` | P1–P9: 선행 조건, 범위, 결정 충돌, 실패 경로 테스트, 원칙 명시, 테스트 가능한 완료 조건 등 |
| ③ 구현 | broker-builder (Sonnet) | 코드 · 테스트 · `03-build-notes.md` | 테스트 먼저 작성 → 실패 확인 → 구현 |
| ④ 구현 검증 | reviewer (Fable) | `04-code-review.md` | A 계획 일치, B 불변 원칙 1–7 금지 패턴, C 기본 정확성 |
| ⑤ 테스트 | test-verifier (Sonnet), 3단계부터 eval-runner (Opus) | `05-test-report.md` | 전체 통과, 모든 완료 조건에 대응 테스트, 새 테스트 3회 반복 안정, skip 증가 없음 |
| ⑥ 개선사항 계획 | planner (Opus) | `06-improvement-plan.md` | — |
| ⑦ 개선 계획 검증 | reviewer (Fable) | `07-improvement-review.md` | 기준 완화 탐지 + I1–I7 |
| 📝 위키 기록 | wiki-writer (Sonnet) | `docs/wiki/` | 사실만, 실패 · 미해결 포함 |

체크리스트 원문: `.claude/skills/plan-review`, `code-review-invariants`, `test-gate`, `improvement-review`

## 검증과 테스트는 어떻게 다른가

| | ④ 구현 검증 | ⑤ 테스트 |
|---|---|---|
| 방법 | 코드를 **읽는다** (`git diff`) | 코드를 **돌린다** (pytest, opa test) |
| 잡는 것 | 테스트가 없는 위반 (확인 후 차감, 트랜잭션 분리, 자격 증명 노출) | 실제 동작 오류, 불안정한 테스트, 빠진 완료 조건 |
| 권한 | 읽기 전용 | 명령 실행 가능, 소스 수정 불가 |

둘 다 통과해야 다음으로 간다. 테스트가 전부 통과해도 ④에서 원칙 위반이 나오면 막힌다.

## 모델 배치 이유

| 모델 | 담당 | 이유 |
|---|---|---|
| Fable | reviewer | 관문이 놓친 실수는 아무도 잡지 못한다. 가장 강한 모델을 막는 쪽에 둔다 |
| Opus | planner, eval-runner | 선행 조건 판단, 근본 원인 분석, 공격 경로 분석 |
| Sonnet | broker-builder, test-verifier, wiki-writer | 실수는 뒤의 관문에서 잡힌다. 반복이 많은 곳에 비용 효율 |

## 안전장치

| 장치 | 동작 | 위치 |
|---|---|---|
| 중요 명령 승인 훅 | commit · push · reset --hard · terraform apply/destroy · 볼륨 삭제 등 → 사람 승인. 훅이 오류가 나도 승인 요청 | `.claude/hooks/guard_critical.py` |
| 권한 규칙 | 훅이 아예 못 돌 때를 대비한 두 번째 승인 규칙, `.env` 접근 금지 | `.claude/settings.json` |
| 쓰기 경로 제한 | 검증 · 기록 담당은 지정 폴더에만 쓸 수 있음 | `.claude/hooks/guard_paths.py` + 각 Agent의 hooks |

## 위키에 남는 것 (작업 하나당)

```
docs/wiki/work-items/<날짜>-<항목>/
├── index.md         개요 · 설계 결정 · 구현 요약 · 문제 목록 · 배운 점
├── verification.md  ②④⑦ 관문별 체크리스트 결과 (차수별)
└── testing.md       ⑤ 테스트 설계 · 실행 명령 · 결과 · 완료 조건 대조 (회차별)
docs/wiki/troubleshooting/<문제>.md   증상 → 원인 → 해결 → 검증 → 재발 방지
```
