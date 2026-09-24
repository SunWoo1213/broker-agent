# 에이전트 권한 브로커 — 프로젝트 규칙

> Claude Code가 매 세션 읽는 파일이다. 범위와 불변 원칙을 여기서 관리한다.

## 이 프로젝트가 만드는 것

AI 에이전트가 사람 대신 사내 시스템(경비, 메일, 고객 DB)을 호출할 때 **반드시 거쳐 가는 검문소**.
에이전트는 실제 API 키를 가지지 않고, 모든 도구 호출을 브로커(MCP 게이트웨이)에 요청한다.
브로커는 요청마다 **허용 / 거부 / 사람 승인 필요** 중 하나로 판단하고 근거를 감사 로그로 남긴다.

포트폴리오 안에서의 위치: AI Invest("LLM의 **결과**를 코드로 검증") → 이 프로젝트("에이전트의 **행동**을 코드로 통제").
목표 직군은 AI 에이전트 · AX 개발이고, 이 프로젝트로 **백엔드 · 인프라 역량**을 보강한다.

설계 전체: `docs/architecture.md` · 결정 기록: `docs/decisions.md` · 진행 계획: `docs/plan.md`
**현재 진행 상황 · 다음 할 일: `docs/stage1-plan.md` 2장(현재 상태) · 4장 표의 "상태" 열** — 세션을 시작하면 여기부터 읽는다. 작업별 상세 기록은 `docs/wiki/Home.md`.

## 불변 원칙

1. **문제가 생기면 전부 막는다 (fail-closed).** 정책 엔진 · DB · Redis에 닿지 않거나 판단이 모호하면 결과는 "거부"다. 어떤 코드 경로도 기본값이 "허용"이면 안 된다.
2. **에이전트는 실제 자격 증명을 보지 못한다.** 도구 호출은 브로커가 발급한 임시 토큰(작업 하나, 인자 해시 포함, 5분)으로만 한다. 도구는 이 토큰만 받아들인다.
3. **승인은 인자 해시에 묶인다.** 승인 뒤 인자가 한 글자라도 바뀌면 실행하지 않는다.
4. **누적 한도는 예약 → 확정 / 해제로 관리한다.** "잔여 한도 확인 후 실행"처럼 확인과 차감이 분리된 구현은 금지한다.
5. **모든 판단은 감사 로그에 남는다.** 판단 결과와 아웃박스 기록은 같은 트랜잭션이다. 감사 로그는 해시 체인으로 위변조를 드러낸다.
6. **취소는 즉시 반영된다.** 캐시를 쓰더라도 위임 버전 번호 + Pub/Sub로 취소를 전파하고, 반영 시간을 측정한다.
7. **평가 수치는 재현 가능해야 한다.** 공격 시나리오 · 채점 기준을 결과에 맞춰 바꾸지 않는다. 막지 못한 시나리오도 결과로 남기고 원인을 분석한다.

## 범위

- **만든다:** MCP 게이트웨이, 관리 API, OPA 정책, 한도 관리, 승인 흐름, 임시 토큰, 감사 워커, 취소 전파, 모의 도구 3종, 데모 에이전트(LangGraph), 공격 시나리오 평가, AWS 배포
- **만들지 않는다:** 사람 로그인 시스템 자체(Keycloak 사용), LLM 대화 내용 필터(유해 발화 등). 이 프로젝트는 무엇을 **말하느냐**가 아니라 무엇을 **실행하느냐**를 통제한다.
- 화면은 최소한으로: 승인 화면, 관리자 화면(정책 · 위임 · 감사 로그 조회). UI에 시간을 쓰지 않는다.

## 기술 스택

- Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, pytest
- MCP Python SDK (Streamable HTTP), LangGraph(데모 에이전트)
- PostgreSQL 16, Redis 7, OPA(Rego)
- AWS: ECS Fargate, RDS, ElastiCache, S3, KMS, Secrets Manager, CloudWatch — Terraform으로 관리
- 로컬: Docker Compose (+ LocalStack으로 S3 · KMS 흉내)

## 폴더

| 폴더 | 내용 |
|---|---|
| `gateway/` | 데이터 플레인. 요청마다 ①서명 검증 ②위임 확인 ③정책 판단 ④한도 예약 ⑤승인 대기 ⑥토큰 발급 ⑦도구 호출 · 응답 필터 ⑧감사 이벤트 |
| `control/` | 컨트롤 플레인. 에이전트 · 도구 등록, 위임 · 취소, 승인 처리, 정책 버전 |
| `audit/` | 감사 워커(아웃박스 → 해시 체인), 체인 검증 도구 |
| `policies/` | Rego 정책과 `opa test` 단위 테스트 |
| `tools/` | 모의 경비 · 메일 · 고객 DB (MCP 서버, 브로커 토큰만 받음) |
| `demo_agent/` | LangGraph 경비 정산 에이전트 (브로커를 통해서만 도구 사용) |
| `eval/` | 공격 시나리오, 채점, 결과 리포트 |
| `load/` | k6 부하 테스트 |
| `infra/terraform/` | AWS 모듈 (network · data · compute · security) |
| `tests/` | pytest |

## 작업 방식

- 계획 → 구현 → 검증 순서로 진행하고, 작업 단위마다 `docs/plan.md` 체크리스트를 갱신한다.
- 설계를 바꾸는 결정은 코드보다 먼저 `docs/decisions.md`에 이유와 함께 적는다.
- **커밋 · 푸시는 사용자가 승인한 뒤에만** 한다. `git add`는 명시한 경로만.
- 비밀(.env, 키 파일)은 읽지도 쓰지도 않는다. 필요한 값은 `env.example`에 이름만 둔다 (`.env.*`는 전부 비밀로 보고 권한에서 막는다).
- AWS 리소스 생성(`terraform apply`) · 삭제(`destroy`)는 사용자가 직접 실행한다. 비용이 나는 리소스(NAT Gateway, RDS, ElastiCache)는 측정 · 시연 때만 띄운다.
- `docker compose down -v`, 볼륨 삭제, `prune`은 사용자만 실행한다.

## 하네스 (Claude Code 개발 팀)

- 작업 하나는 `/work-item <plan.md 항목>`으로 진행한다: ①계획 → ②계획 검증 → 🧑승인 → ③구현 → ④구현 검증 → ⑤테스트 → ⑥개선사항 계획 → ⑦개선 계획 검증 → 📝위키 기록 → 🧑커밋 승인
- 팀원: `.claude/agents/` (planner=opus · reviewer=fable · broker-builder=sonnet · test-verifier=sonnet · eval-runner=opus · wiki-writer=sonnet), 작업 매뉴얼: `.claude/skills/`
- 산출물은 `.claude/runs/<날짜>-<항목>/01~07`(git 제외), 하네스 규칙 변경 기록은 `.claude/harness-notes.md`
- 개발 기록은 `docs/wiki/`에 남긴다: 작업마다 `work-items/<항목>/`(index · verification · testing), 문제마다 `troubleshooting/`. 절차 설명은 `docs/wiki/process.md`. `/work-item` 밖에서 생긴 문제는 `/dev-wiki <내용>`으로 기록
- 커밋 · 푸시 · `terraform apply/destroy` · 볼륨 삭제는 훅(`.claude/hooks/guard_critical.py`)이 항상 사람 승인을 요구한다
