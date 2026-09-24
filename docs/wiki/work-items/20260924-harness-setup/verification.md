# 검증 기록 — 개발 하네스 구성

> 요약
> - 결론: 독립 reviewer 없이, 사용자 설계 검토 3차 + 파이프 테스트 2차로 검증됐다.
> - 바뀐 것: 사용자 요청에 따라 7단계 관문 · 모델 배치(reviewer=Fable, planner·eval-runner=Opus, builder·test-verifier=Sonnet) · 위키 기록 구조가 확정됐다.
> - 다음에 알아야 할 것: 하네스 파일(Agent·Skill 문서) 자체는 독립 검토자가 본 적이 없다. 첫 `/work-item` 실행이 사실상 첫 검증이다.

> 이 작업은 하네스 자체를 만드는 작업이라 ②④⑦ 관문(reviewer)을 거치지 않았다. 대신 실제로 이뤄진 검증을 그대로 남긴다.
> **한계:** 독립된 검토자가 하네스 파일(Agent · Skill 문서)을 검토하지 않았다. 첫 `/work-item` 실행이 사실상 하네스에 대한 첫 검증이 된다.

## 요약

| 검증 | 검증자 | 차수 | 결과 | 주요 내용 |
|---|---|---|---|---|
| 설계(청사진) 검토 | 사용자 | 3 | 승인 | 단계별 검증 추가 → 모델 배치 · 승인 훅 추가 → 위키 · 검증 · 테스트 기록 추가 |
| 훅 동작 검증 | 파이프 테스트 (자동) | 2 | 통과 | 1차에서 fail-open 결함 발견 → 수정 후 통과 |
| 설정 파일 형식 | JSON 파싱 | 1 | 통과 | `.claude/settings.json` 파싱, matcher · args 확인 |
| 모델 · 필드 사양 확인 | claude-code-guide 조사 | 1 | 확인 | Agent `model`에 `fable` 사용 가능, 훅 `ask`는 auto 모드 · subagent에도 적용, `Bash\|PowerShell` matcher 지원 |

## 설계 검토 (사용자)

### 1차 — 수정 요청

- 제안: Agent 4개(builder, policy-author, invariant-reviewer, eval-runner), 작성-검토 1회
- 요청: "계획, 계획 검증, 구현, 구현 검증, 테스트, 개선사항 계획 검증과 같이 매 프로세스마다 검토하고 검증하는 단계"
- 반영: 7단계 관문, `VERDICT` 판정 형식, 반복 제한, 검증자 분리(reviewer 읽기 전용)

### 2차 — 수정 요청

- 요청: 프로세스에 맞는 모델 배치, 커밋 · 푸시 같은 중요 작업에 사람 승인 훅
- 추가 요청(작업 중): 모델은 Fable · Opus · Sonnet만 사용
- 반영: reviewer=Fable, planner · eval-runner=Opus, builder · test-verifier=Sonnet. `guard_critical.py` 훅 + `permissions.ask`

### 3차 — 수정 요청

- 요청: 개발 과정을 위키 형식으로 기록, 문제 상황 · 문제 해결 기록, 검증 · 테스트 과정 기록
- 반영: `wiki-writer`(Sonnet), `dev-wiki` Skill, `docs/wiki/` 구조(index · verification · testing · troubleshooting), `process.md`

## 사양 확인

| 확인한 것 | 결과 | 설계에 준 영향 |
|---|---|---|
| Agent frontmatter `model` 값 | `sonnet` · `opus` · `haiku` · `fable` · `inherit` · 전체 모델 ID | 세 모델 별칭 사용 |
| 훅 `permissionDecision: "ask"` | auto 모드에서도 승인 창, subagent 호출에도 적용 | 승인 훅을 PreToolUse로 구현 |
| Windows에서 훅 실행 셸 | Git Bash가 있으면 Git Bash | `args` 실행형(셸 없이 python 직접 실행)으로 셸 차이 회피 |
| Agent frontmatter `hooks` | Agent별 PreToolUse 훅 가능 | 검증 담당 쓰기 경로 제한에 사용 |
