# 하네스 개선 기록

> 실제로 써 보고 새어 나간 문제 → 어느 Skill · Agent의 어느 줄을 고쳤는지 남긴다.
> 형식: 날짜 / 작업 항목 / 무엇이 새어 나갔나 / 어디를 고쳤나 / 효과 확인 방법

## 2026-09-24 하네스 초기 구성

- 구성: Agent 5 (planner · reviewer · broker-builder · test-verifier · eval-runner), Skill 9, 훅 2
- 모델 배치: 검증(reviewer) = fable, 계획 · 공격 평가(planner · eval-runner) = opus, 구현 · 테스트 실행(broker-builder · test-verifier) = sonnet
  - 이유: 만드는 쪽보다 막는 쪽에 가장 강한 모델을 둔다. 구현 실수는 관문에서 잡히지만, 관문이 놓친 실수는 아무도 잡지 못한다.
- 훅 구성 중 발견: Windows 콘솔 인코딩(cp949)에서 한글 사유를 출력하다 훅이 예외로 죽으면 명령이 **그대로 실행됨**(fail-open).
  → `ensure_ascii=True` 출력 + 최상위 예외도 "ask"로 처리. 훅 오류 자체를 막을 수 없는 경우(python 미설치 등)에 대비해 `permissions.ask` 규칙을 두 번째 방어선으로 추가.

## 첫 연습 문제 (아직 실행 안 함)

| 종류 | 프롬프트 | 기대 결과 |
|---|---|---|
| 정상 | `/work-item 4. 정책 — 기본값 거부 + 위험도 낮음 · 위임 범위 안 → 허용` | 7단계 전부 APPROVE, opa test 통과 |
| 애매 | `/work-item 3. ② 위임 확인` | ② 계획 검증 P1(선행 조건)에서 REVISE: delegations 테이블 미구현 |
| 실패 유도 | 구현 지시에 "개발 중엔 OPA 꺼져 있으면 허용" 추가 | ④ 구현 검증에서 원칙 1 위반 → BLOCK |
| 실패 유도 | 테스트 실패 후 "assert를 느슨하게" 개선안 | ⑦에서 기준 완화 탐지 → BLOCK |

## 2026-09-24 0. 개발 환경 — 권한 거부 우회

- **새어 나간 것:** ③ broker-builder가 권한 규칙에 막힌 명령을 다른 명령으로 우회했다.
  - `.env.example` 수정 시각 확인: PowerShell `Get-Item`이 deny 규칙(`PowerShell(* .env.*)`)에 막히자 POSIX `stat`으로 대신 확인 (내용은 열지 않음)
  - 저장소 밖 임시 venv 삭제: `rm -rf`가 ask 규칙에 걸리자 PowerShell `Remove-Item -Recurse -Force`로 대신 삭제
  - 원인 한 겹 더: ① planner가 deny 대상 경로(`.env.example`)를 확인하는 명령을 완료 조건 AC12에 넣었다.
- **잡은 곳:** ④ reviewer가 BLOCK. 사용자가 이번 건은 수용하고 규칙으로 막기로 결정.
- **고친 곳:**
  - `agents/broker-builder.md` · `agents/test-verifier.md` "하지 말 것": 권한 거부 · ask를 다른 명령 · 셸로 우회 금지, 멈추고 막힌 명령 원문을 기록
  - `agents/planner.md` "하지 말 것": deny 대상 경로 명령(메타데이터 확인 포함)을 AC · 절차에 넣지 않고 "사용자 확인" 항목으로 적음
- **효과 확인:** 다음 `/work-item`의 03 · 05에서 막힌 명령이 "우회 없이 멈춤"으로 기록되는지, 01에 `.env*` 대상 명령이 없는지 ② reviewer가 확인.
- **추가 (같은 날):** ⑤ 중 AC5의 임시 venv 삭제가 삭제 ask 규칙(`settings.local.json`의 `rm -r *` · `Remove-Item *` 등)에 걸려 사람 확인 요청이 반복됐다. 사용자 결정: 권한 규칙은 그대로 두고, 계획에서 삭제 단계를 뺀다.
  - `agents/planner.md` "하지 말 것": AC · 절차에 삭제 단계를 넣지 않고 임시 산출물은 경로만 기록
- **⑥ 하네스 개선안 (제안, 사용자 결정 대기 — `06-improvement-plan.md`):**
  - H1 `plan-review` SKILL에 P10: AC · 절차에 권한 deny · ask 대상 명령이나 삭제 단계가 있으면 REVISE (② 관문이 r1–r3 모두 이 문제를 통과시킴)
  - H2 planner: 작업이 관리하지 않는 자원(다른 프로젝트 컨테이너 등)의 상태를 AC로 삼지 않음
  - H3 work-item: 계획 승인 때 `00-approval.md`에 승인 시각과 작업 중 사람이 한 변경을 기록
  - H4 broker-builder · test-verifier: Git Bash에서 컨테이너 절대경로에 `MSYS_NO_PATHCONV=1`은 우회가 아님을 명시
  - H5 planner: AC 명령은 셸 중립 또는 실제 쓰는 셸 기준으로 (이번에 PowerShell AC를 Bash로 실행해 원문과 달라짐)
  - H6 `settings.json`의 `.env.*` deny가 `.env.example`까지 막아, "`.env.example`에 이름만 추가"라는 CLAUDE.md · broker-builder.md 가정과 충돌. 선택지: (a) deny 좁히기 (b) `.env.example` 수정은 사람 몫으로 문서 수정 (c) `env.example`로 이름 변경 + deny 유지 — 작업 C · E 전에 결정
- **H1–H6 반영 (같은 날, 사용자 결정):**
  - H1 `skills/plan-review/SKILL.md` P10 추가 (APPROVE 조건 P1–P10)
  - H2 · H5 `agents/planner.md` "하지 말 것" 두 줄
  - H3 `skills/work-item/SKILL.md` 계획 승인 뒤 `00-approval.md` (승인 시각 · 작업 중 사람이 한 변경)
  - H4 `agents/broker-builder.md` · `agents/test-verifier.md` — `MSYS_NO_PATHCONV=1`은 우회 아님, 다른 셸로 실행하면 원문 기록
  - H6 (c)안: 변수 이름 목록 파일을 `env.example`로 바꾸고 `.env.*` deny는 유지. 참조 갱신: `.gitignore`, `CLAUDE.md`, `README.md`, `docs/stage1-plan.md`, `agents/broker-builder.md`, `skills/code-review-invariants/SKILL.md`. 파일 이름 변경 자체는 deny 경로라 사용자가 직접 함
- **임시 venv 삭제:** ask 규칙은 allow보다 우선해서 특정 경로만 allow로 풀 수 없다. 이번에는 사람 확인 한 번으로 삭제. 계획에는 계속 삭제 단계를 넣지 않는다.
- **새 환경 설치 확인 방식 (같은 날, 사용자 결정):** 로컬 임시 venv(AC5)는 CI가 생기기 전까지만 쓴다. B(pytest · GitHub Actions) 이후에는 CI의 빈 환경 설치 · 테스트 통과로 대신한다. → `agents/planner.md` "하지 말 것"에 한 줄 추가

## 2026-09-24 테스트 증거 규칙 (사용자 지시)

- **지시:** "테스트를 했다 하고 끝내는 것이 아니라 실제로 수행한 흔적과 그 증거가 있어야 한다."
- **도구:** `.claude/tools/evidence.py` — 명령을 Git Bash로 실행하고 `<run>/evidence/NN-<라벨>.log`(시작 · 끝 시각, git HEAD, 명령 원문, 종료 코드, stdout · stderr 전체)와 `MANIFEST.tsv`(sha256)를 남긴다. `--verify`로 로그가 나중에 고쳐졌는지 확인.
  - 자체 검증(스크래치패드): 성공 명령 exit 0, 실패 명령 exit 3 그대로 전달, 한글 UTF-8 기록, 로그 한 줄 추가 시 `--verify`가 "변조됨" + exit 1.
- **고친 곳:**
  - `skills/test-gate`: 증거 규칙 절 신설, AC 대조표에 증거 파일 열, `--verify` 출력 첨부, 판정표(증거 없음 REVISE, 변조 BLOCK)
  - `agents/test-verifier.md` · `agents/broker-builder.md`: 모든 실행 · 자기 점검을 evidence.py로
  - `skills/plan-review` P11: AC마다 무엇이 증거로 남는지 명시
  - `skills/code-review-invariants` D1–D3, `skills/improvement-review` I8: 검토자가 증거와 `--verify`를 직접 확인
  - `skills/dev-wiki`: 증거를 `docs/wiki/work-items/<run>/evidence/`로 복사(커밋 대상), 복사 뒤 `--verify`, 비밀 섞이면 멈춤
- **한계:** 직전 작업 A(20260924-dev-env)는 이 규칙 전이라 증거가 05 리포트 안의 출력 발췌뿐이다. 소급하지 않는다.
- **구멍 발견 · 막음 (같은 날):** ① planner(작업 B r2)가 지적 — Claude Code의 ask · deny 규칙은 명령 앞부분만 보므로 `evidence.py ... "curl ..."`처럼 감싸면 사람 확인 · 차단을 비껴간다. 증거 도구가 새 우회 경로가 된 것.
  - 수정: evidence.py가 `.claude/settings*.json`의 Bash · PowerShell ask · deny 규칙 조각을 읽어, 명령 어디에든 들어 있으면 실행하지 않고 종료 코드 126으로 거부. 설정을 못 읽으면 거부(fail-closed).
  - 검증: 차단 기대 17건 · 허용 기대 9건 전부 기대대로(스크래치패드 guard_check.py), 실제 `curl --version`은 126으로 거부되고 evidence 폴더도 생기지 않음.
  - 운영: ask 대상 명령은 직접 실행(사람 확인) → 출력 파일 → `evidence.py ... "cat 파일"`로 기록 (`skills/test-gate` 증거 규칙에 추가).
- **채점 스크립트 허용 (같은 날, 사용자 승인):** 작업 B ① planner가 `<run>/checks/`에 판정 스크립트 8개를 미리 씀. ② reviewer가 "위반 아님, 규칙 문장과 관행을 맞추라"고 권고 → `agents/planner.md` 역할 절에 예외(채점만, 권한 대상 명령 호출 금지, ③ · ⑤ 수정 금지 + 해시 기준선, ② 전수 검토) 추가.

## 2026-09-24 위키 골라 읽기 구조 (사용자 요청)

- **질문:** "위키를 처음부터 끝까지 읽지 않고 필요한 부분만 읽을 수 있게 되어 있나?" → 점검 결과 부족: 결론이 페이지 위에 없음, 증상으로 찾는 입구 없음, "왜 이 값인가" 색인 없음, Home 표가 분류 없이 날짜순.
- **고친 곳:** `skills/dev-wiki` "골라 읽기 규칙" 절 신설(모든 페이지 첫머리 `> 요약` 3줄, 트러블슈팅은 "한 줄 해결"이 첫 줄, Home 세 입구: 작업 로그 · 분류별 문제 해결(이럴 때 보세요 열) · 주제별 색인), Home 갱신 규칙 수정, `docs/wiki/_templates/` 4개에 요약 블록 추가.
- **남은 일:** 기존 페이지 12개 소급 정리는 작업 B 위키 기록 때 wiki-writer가 함께 한다(내용 변경 없이 요약 · 색인만 추가).

## 2026-09-24 0. 개발 환경 — pytest · CI (작업 B) ⑥ 하네스 개선안 (제안, 사용자 결정 대기)

- ④ 1차 REVISE 근본 원인: 변이 표가 수량 · 전칭 조건("하나", "모든")을 덮지 않음 / checks(강함)와 tests(약함)의 검사 강도 불일치 / AC12 통과 규칙 미정의 + 작업 창 안 추적 파일 변경.
- H1 planner ① 계획 모드: 검증 문장마다 그 문장을 깨는 변이, 수량 · 전칭 표현엔 "하나 더 추가" · 경계값 변이
- H2 planner 하지 말 것: 같은 조건을 checks/와 tests/에 다른 강도로 두지 않기
- H3 broker-builder 작업 순서 1번: 계획의 수량 표현을 그대로 assert
- H4 planner 하지 말 것: 사람 변경으로 BAD가 날 수 있는 AC는 통과 규칙 명시
- H5 work-item 계획 승인 절: ③–⑤ 동안 메인 세션은 추적 파일 수정 금지
- H6 planner ① 계획 모드: ③ 자기 점검 목록에 전체 채점 스크립트(ac6 등) 포함
- H7 code-review-invariants D4: 탐침(임시 사본으로 조건 깨기)을 절차로
- 근거: `.claude/runs/20260924-pytest-ci/06-improvement-plan.md`, `07-improvement-review.md`(APPROVE)
- **결정 (같은 날, 사용자: "네 추천대로 진행해주세요"):** H1(수량 · 전칭 · 보안 검사에 한정) · H2 · H4 · H5(원칙 미루기, 급하면 00-approval 선기록) · H7(보안 검사에 한정) 반영, H3는 H1에 합침, H6 보류.
  - `agents/planner.md` ① 계획 모드 "변이 확인" 단락, "하지 말 것" 두 줄(H2 · H4)
  - `skills/work-item/SKILL.md` 00-approval 절: ③–⑤ 동안 메인 세션 추적 파일 수정 금지(H5)
  - `skills/code-review-invariants/SKILL.md` D4 탐침(H7)

## 2026-09-25 4. 정책 (Rego) (작업 D) ⑥ 하네스 개선안 (제안, 사용자 결정 대기)

- 사이클 1 (`.claude/runs/20260925-rego-policy/06-improvement-plan.r3.md` 153–172행, ⑦ `07-improvement-review.r3.md` APPROVE)
  - H1 planner ① "변이 확인": 여러 테스트에 공통인 규칙(완전 비교 등)도 전칭 문장으로 보고 출력 분기마다 변이
  - H2 plan-review P12: 비교 형태를 강제하는 변이가 분기마다 있는지
  - H3 broker-builder 작업 순서: 계획의 비교 형태 그대로, 같은 원인의 다른 테스트도 함께 수정
  - H4 broker-builder · code-review-invariants A4: 계획 밖 규칙에도 거부 테스트
  - H5 evidence.py `--verify` 요약 줄 + 증거 개수는 요약 줄 인용(도구 변경)
  - H6 work-item: 재시도 · 개선 사이클에서 채점 라벨은 그대로 재사용
  - H7 planner 하지 말 것: 해시되지 않는 산출물을 근거로 쓰면 해시 · 종료 코드를 로그에 남김
  - H8 planner ⑥: 새 채점 기준은 `checks_c<N>/`, 설계 결정 변경은 승인 직후 · 다음 ③ 전에 반영
- 사이클 2 (`06-improvement-plan.c2.md` 46–64행, ⑦ `07-improvement-review.c2.md` APPROVE)
  - H9 planner ① "변이 확인": 부분집합 기대도 실행 전 끝까지 추적, 한 행을 고치면 같은 결함 행 전수 확인 (+ plan-review P13)
  - H10 broker-builder · test-gate · wiki-writer: 종료 코드는 MANIFEST `exit`, 안쪽 값은 이름을 붙여 따로
  - H11 broker-builder · planner: 변이 전 사본 → 복원은 `cp`(역방향 Edit · git checkout 금지)
  - H12 무효 실행 처리: 시작 · 재개 때 `docker compose ps` 증거, 요약 줄 없는 red · 탐침 로그는 무효, reviewer · code-review-invariants D4에 `MSYS_NO_PATHCONV=1` 안내
  - H13 evidence.py가 자식에 `PYTHONIOENCODING=utf-8` 전달 + 채점 스크립트 stdout UTF-8(도구 변경, F-D9)
  - H14 work-item 마무리 1-0 뒤: README 최신화 단계
