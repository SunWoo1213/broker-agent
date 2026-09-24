---
name: work-item
description: docs/plan.md 항목 하나를 7단계(계획 → 계획 검증 → 구현 → 구현 검증 → 테스트 → 개선사항 계획 → 개선 계획 검증)로 진행하는 오케스트레이터. 사용자가 /work-item <항목>으로 호출한다.
disable-model-invocation: true
argument-hint: "<plan.md 항목, 예: 4. 정책 — 기본값 거부>"
---

# /work-item — 7단계 오케스트레이터

너(메인 세션)는 팀장이다. 직접 계획 · 구현 · 검증하지 않고 팀원(subagent)에게 맡긴 뒤, 산출물의 `VERDICT` 줄을 보고 다음 단계를 정한다.

대상 항목: `$ARGUMENTS`

## 0. 준비

1. `docs/plan.md`에서 항목을 찾는다. 없거나 여러 개와 겹치면 사용자에게 묻고 멈춘다.
2. run 폴더를 만든다: `.claude/runs/<YYYYMMDD>-<짧은-영문-slug>/`
3. 사용자에게 한 줄로 알린다: "`<항목>` 시작, 산출물은 `<run 폴더>`"

## 단계와 담당

| 단계 | subagent | 모델 | 산출물 |
|---|---|---|---|
| ① 계획 | `planner` | opus | `01-plan.md` |
| ② 계획 검증 | `reviewer` (모드: 계획 검증) | fable | `02-plan-review.md` |
| 🧑 사람 확인 | — | — | 계획 요약 + 승인 요청 |
| ③ 구현 | `broker-builder` | sonnet | 코드 + `03-build-notes.md` |
| ④ 구현 검증 | `reviewer` (모드: 구현 검증) | fable | `04-code-review.md` |
| ⑤ 테스트 | `test-verifier` (3단계부터 `eval-runner` 추가) | sonnet (eval: opus) | `05-test-report.md` |
| ⑥ 개선사항 계획 | `planner` (모드: 개선) | opus | `06-improvement-plan.md` |
| ⑦ 개선 계획 검증 | `reviewer` (모드: 개선 검증) | fable | `07-improvement-review.md` |
| 📝 위키 기록 | `wiki-writer` | sonnet | `docs/wiki/work-items/<run>/` index · verification · testing, 문제 해결 페이지, Home |
| 🧑 사람 확인 | — | — | 커밋 승인 요청 |

subagent를 부를 때 프롬프트에 **run 폴더 경로, 모드, 읽어야 할 이전 산출물 파일명**을 반드시 넣는다. 팀원은 이 대화를 보지 못한다.
재시도 차수가 있으면 파일명에 붙인다: `04-code-review.r2.md`.

## 흐름과 분기

```
① → ②
   ② APPROVE → 🧑 계획 승인 → ③
   ② REVISE  → ① (지적 사항 전달) — 최대 2회
   ② BLOCK   → 멈추고 사용자에게 보고
③ → ④
   ④ APPROVE → ⑤
   ④ REVISE  → ③ (지적 사항 전달) — 최대 2회
   ④ BLOCK   → 멈추고 보고
⑤ → ⑥ (APPROVE든 REVISE든 항상 ⑥으로 간다)
   ⑤ BLOCK   → 멈추고 보고 (환경 문제 · 기준 완화 의심)
⑥ → ⑦
   ⑦ APPROVE + "코드 수정 필요" → ③ (개선 사이클 +1, 최대 2회) → ④ → ⑤ → ⑥ → ⑦
   ⑦ APPROVE + "코드 수정 없음" → 마무리
   ⑦ REVISE  → ⑥ — 최대 2회
   ⑦ BLOCK   → 멈추고 보고
```

**반복 제한 공통 규칙:** 같은 관문에서 REVISE가 2회를 넘거나, 개선 사이클이 2회를 넘으면 멈추고 사용자에게 지금까지의 산출물 경로와 막힌 이유를 보고한다.

**멈출 때도 기록한다:** BLOCK · 반복 제한 초과로 멈추면, 보고 전에 `wiki-writer`를 결과 `중단`과 중단 사유를 넣어 호출한다. 막힌 문제는 트러블슈팅 페이지에 `미해결`로 남는다.

VERDICT 줄을 찾을 수 없거나 형식이 다르면 **BLOCK으로 취급**한다 (fail-closed).

## 🧑 사람 확인 1: 계획 승인 (② APPROVE 뒤)

사용자에게 보여줄 것: 범위, 바꿀 파일, 먼저 쓸 테스트, 완료 조건, 설계 변경 여부. 이어서 "진행할까요?"라고 묻는다.
설계 변경이 있으면 decisions.md 초안을 보여주고, 승인받으면 **메인 세션이** `docs/decisions.md`에 추가한 뒤 ③으로 간다.

승인을 받으면 **메인 세션이** run 폴더에 `00-approval.md`를 쓴다. 이후 단계의 팀원 프롬프트에 이 파일을 읽을 것으로 넣는다.

```markdown
# 승인 기록
- 승인한 계획: 01-plan<.rN>.md
- 승인 시각: YYYY-MM-DD HH:MM (+0900)
## 작업 중 사람이 한 변경
| 시각 | 무엇을 | 사용자 답 원문 |
```

작업 도중 사용자가 파일 · 컨테이너 · 설정을 직접 바꿨다고 알려 주면 이 표에 한 줄씩 추가한다. ④ · ⑤는 작업 창 안의 변경을 이 표와 대조해, 표에 있는 변경은 ③의 행동으로 보지 않는다.

## 마무리

1. `docs/plan.md`에서 해당 항목 체크박스를 `[x]`로 바꾼다.
1-1. `wiki-writer`를 호출한다 (run 폴더 경로, 결과 `완료`). 돌려받은 페이지 목록을 커밋 대상에 포함한다.
2. ⑥의 "하네스 개선안"이 있으면 `.claude/harness-notes.md`에 날짜와 함께 추가한다. Skill · Agent 파일은 바로 고치지 않고 사용자에게 제안만 한다.
3. 사용자에게 보고한다: 거친 관문과 판정(재시도 횟수 포함), 테스트 결과 요약, 바뀐 파일 목록, 위키 페이지 링크.
4. 🧑 사람 확인 2: 커밋할 파일 목록(명시 경로)과 커밋 메시지 초안을 보여주고 승인을 요청한다. 승인 전에는 `git add`도 하지 않는다. `git commit` · `git push`는 훅이 한 번 더 사람 승인을 요구한다.

## 하지 말 것

- 관문 건너뛰기. 작은 항목이면 문서를 짧게 쓰게 하되 단계는 모두 거친다
- 팀원 대신 직접 코드 수정 · 검토 판정 내리기
- REVISE 지적을 요약하면서 내용 빼기. 지적 사항은 원문 그대로 다음 팀원에게 넘긴다
