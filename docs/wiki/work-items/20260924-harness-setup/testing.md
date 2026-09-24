# 테스트 기록 — 개발 하네스 구성

## 요약

| 회차 | 대상 | 결과 | 비고 |
|---|---|---|---|
| 1 | `guard_critical.py` | **실패** | 걸려야 할 명령 전부에서 훅이 예외 종료 → fail-open |
| 2 | `guard_critical.py` | 통과 (55/55) | 인코딩 수정 후 |
| 1 | `guard_paths.py` | 통과 (9/9) | 처음부터 fail-closed 구조로 작성 |
| — | Claude Code 세션 안 실제 발동 | **미확인** | 세션 재시작 또는 `/hooks` 후 확인 필요 |

## 테스트 설계

| 테스트 | 종류 | 검증하는 것 |
|---|---|---|
| 명령 판정표 | 단위 (파이프) | 중요 명령 → `ask`, 일반 명령 → 판정 없음(평소 권한 흐름) |
| 도구 2종 반복 | 단위 | 같은 명령이 Bash · PowerShell 입력 모두에서 같은 판정 |
| 잘못된 입력 | 실패 경로 | JSON 아님, command가 문자열 아님, 한글 UTF-8 → 전부 `ask` (fail-closed) |
| 표준 오류 없음 | 실패 경로 | 판정 과정에서 예외 출력이 없어야 함 (예외 = 훅 오류 = 통과 위험) |
| 경로 우회 | 실패 경로 | `..`, 접두사 유사 경로(`.claude/runsX`), 절대 경로 |

## 환경

- Windows 11, Git Bash, Python 3.13.7
- 테스트 스크립트: 세션 임시 폴더의 `hooktest.py`, `pathtest.py` (저장소에 포함하지 않음)

## guard_critical.py — 회차 1: 실패

실행: 명령마다 `{"tool_name":"Bash","tool_input":{"command":...}}`를 표준 입력으로 넣고 출력 판정 확인.

```
git commit -m 'x'  -> Traceback (most recent call last):
  ...
UnicodeEncodeError: 'cp949' codec can't encode character '—' in position 142: illegal multibyte sequence
(pass)
```

- `git commit`, `git push`, `reset --hard`, `clean -f`, `branch -D`, `terraform apply/destroy`, `down -v`, `volume rm`, `prune`, `gh pr create` **전부** 같은 예외
- 일반 명령(`git status`, `pytest` 등)은 정상 판정 없음 → 즉 판정 로직(정규식)은 맞았고 **출력 단계**에서만 죽었다
- 분석과 해결: [문제 해결 페이지](../../troubleshooting/hook-cp949-fail-open.md)

## guard_critical.py — 회차 2: 통과

### 명령 판정표 (Bash · PowerShell 각각 실행, 두 도구 결과 동일)

| 명령 | 기대 | 결과 |
|---|---|---|
| `git status` | 없음 | 없음 |
| `git add docs/plan.md` | 없음 | 없음 |
| `git log --oneline` | 없음 | 없음 |
| `git diff --stat` | 없음 | 없음 |
| `git commit -m '정책 추가'` | ask | ask |
| `git -C . push origin main` | ask | ask |
| `git add a && git commit -m x` | ask | ask |
| `git push --force` | ask | ask |
| `git reset HEAD f` | 없음 | 없음 |
| `git reset --hard` | ask | ask |
| `git clean -fd` | ask | ask |
| `git branch -D feat` | ask | ask |
| `terraform plan` | 없음 | 없음 |
| `terraform -chdir=infra/terraform apply` | ask | ask |
| `terraform destroy` | ask | ask |
| `docker compose up -d` | 없음 | 없음 |
| `docker compose down` | 없음 | 없음 |
| `docker compose down -v` | ask | ask |
| `docker-compose down --volumes` | ask | ask |
| `docker volume rm pgdata` | ask | ask |
| `docker system prune -a` | ask | ask |
| `gh pr create --fill` | ask | ask |
| `gh pr view 1` | 없음 | 없음 |
| `echo committed` | 없음 | 없음 |
| `pytest -q tests` | 없음 | 없음 |
| `opa test policies` | 없음 | 없음 |

### 잘못된 입력

| 입력 | 기대 | 결과 |
|---|---|---|
| `garbage` (JSON 아님) | ask | ask |
| `{"tool_input":{"command":123}}` | ask | ask |
| 한글 커밋 메시지 (UTF-8 바이트) | ask | ask |

```
FAILURES: 0
```

표준 오류 출력 없음, 종료 코드 0.

## guard_paths.py — 회차 1: 통과

| 쓰기 대상 | 허용 경로 | 기대 | 결과 |
|---|---|---|---|
| `.claude/runs/x/02-plan-review.md` | `.claude/runs` | 허용 | 허용 |
| 절대 경로 `…\.claude\runs\a.md` | `.claude/runs` | 허용 | 허용 |
| `gateway/app.py` | `.claude/runs` | deny | deny |
| `.claude/runs/../../gateway/app.py` | `.claude/runs` | deny | deny |
| `.claude/runsX/a.md` | `.claude/runs` | deny | deny |
| `tests/test_x.py` | `.claude/runs` | deny | deny |
| `eval/reports/r.md` | eval-runner 경로 3개 | 허용 | 허용 |
| `eval/scenarios/s.yaml` | eval-runner 경로 3개 | deny | deny |
| `garbage` (JSON 아님) | `.claude/runs` | deny | deny |

```
FAILURES: 0
```

## 알려진 한계 (테스트로 막지 못하는 것)

- 정규식 기반이라 명령을 난독화하면(`g''it push`, 변수에 담아 실행 등) 훅을 피할 수 있다. `permissions.ask` 규칙과 CLAUDE.md 규칙이 보조한다.
- `guard_paths.py`는 Write · Edit 도구만 막는다. Bash로 파일을 쓰는 것(`echo > file`)은 막지 못한다. 대신 ④ 구현 검증에서 `git diff`로 드러난다.
- 실제 Claude Code 세션 안에서 훅이 발동하는지는 아직 확인하지 않았다.
