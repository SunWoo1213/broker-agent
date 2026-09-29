"""테스트 · 검증 명령을 실행하고 그 흔적을 증거 파일로 남긴다.

사용법 (저장소 루트에서):
    sh .claude/tools/python.sh .claude/tools/evidence.py <run 폴더> <라벨> "<명령>"
    sh .claude/tools/python.sh .claude/tools/evidence.py <run 폴더> --verify

예:
    sh .claude/tools/python.sh .claude/tools/evidence.py .claude/runs/20260924-pytest-ci ac1-pytest "sh .claude/tools/python.sh -m pytest -q"

python 을 부를 때는 `.claude/tools/python.sh` 를 거친다. 맥에는 `python` 이라는 이름이 없고
(있는 것은 `python3`), venv 경로도 `.venv/bin` 과 `.venv/Scripts` 로 갈리기 때문이다.
이렇게 해야 증거 로그에 남는 명령 원문이 두 OS에서 같다.

명령은 bash 로 실행한다 (맥 · 리눅스는 시스템 bash, 윈도우는 Git Bash). 결과는 <run 폴더>/evidence/ 아래에 쌓인다.
- NN-<라벨>.log : 실행 시각(시작 · 끝), 작업 폴더, git HEAD · 변경 파일 수, 명령 원문, 종료 코드, stdout · stderr 전체
- MANIFEST.tsv  : 로그마다 순번 · 라벨 · 종료 코드 · 시작 시각 · sha256 (한 줄씩 추가만 함)

로그는 OS와 상관없이 항상 LF로 쓴다(`newline=""`). 윈도우 기본 동작대로 CRLF로 저장하면
`.gitattributes`가 커밋 때 LF로 되돌려 MANIFEST의 sha256과 어긋나고, 증거 검증이 기록한
기계에서만 통과하게 된다.

--verify 는 MANIFEST의 sha256과 실제 로그 파일을 대조해, 나중에 로그가 고쳐졌는지 보여 준다.
마지막 줄에 `합계 N  일치 A  변조됨 B  없음 C` 요약을 출력한다(증거 개수는 이 줄을 인용한다).
이 도구는 명령의 종료 코드를 그대로 돌려준다. 판정은 사람이 아니라 로그 원문으로 한다.

비밀 마스킹: 로그를 파일에 쓰기 **전에** 비밀번호로 보이는 조각(libpq `password=`,
psycopg kwargs repr의 `'password': '...'`, 접속 URL의 `://사용자:비밀번호@`)을 `***` 로 바꾼다.
치환한 내용으로 sha256을 계산하므로 파일과 해시가 같은 것을 가리키고 `--verify` 와 충돌하지 않는다.
따라서 **로그는 명령의 출력과 글자 단위로 같지 않을 수 있다.** 마스킹 범위는 위 세 패턴으로만
좁게 유지한다(증거를 임의로 줄이지 않는다). 이미 만들어진 로그는 다시 쓰지 않는다 —
기록 뒤에 고치는 것은 증거의 의미를 무너뜨린다. 계기는 작업 C에서 pytest의 긴 트레이스백이
psycopg 연결 프레임의 지역 변수를 repr로 찍어 개발용 DB 비밀번호가 평문으로 남은 일이다
(`docs/wiki/troubleshooting/pytest-traceback-leaked-db-password-into-evidence-log.md`, 개선안 작업 C H1).

권한 규칙 보호: Claude Code의 ask · deny 규칙은 명령 앞부분만 본다. 이 도구로 감싸면
안쪽 명령이 규칙을 비껴갈 수 있으므로, `.claude/settings*.json`의 Bash · PowerShell
ask · deny 규칙에 해당하는 명령은 **실행하지 않고 거부한다**(종료 코드 126).
그런 명령은 이 도구 없이 직접 실행해 사람 확인을 받고, 출력 파일을 이 도구로 `cat` 해 기록한다.
설정 파일을 읽지 못하면 역시 거부한다 (fail-closed).
"""

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KST = dt.timezone(dt.timedelta(hours=9))


def now() -> str:
    return dt.datetime.now(KST).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=15)
        return out.stdout.strip() or out.stderr.strip()
    except Exception as exc:  # 증거 기록은 git 없이도 계속한다
        return f"(git 실행 실패: {exc})"


REPO = Path(__file__).resolve().parents[2]
SETTINGS = [REPO / ".claude" / "settings.json", REPO / ".claude" / "settings.local.json"]
RULE = re.compile(r"^(Bash|PowerShell)\((.*)\)$")


def guarded_prefixes() -> list[str]:
    """ask · deny 규칙에서 명령 조각을 뽑는다. 'Bash(git push *)' → 'git push'."""
    prefixes = set()
    for path in SETTINGS:
        if not path.exists():
            continue  # settings.local.json은 없을 수 있다
        perms = json.loads(path.read_text(encoding="utf-8")).get("permissions", {})
        for rule in perms.get("ask", []) + perms.get("deny", []):
            m = RULE.match(rule.strip())
            if not m:
                continue
            core = m.group(2).strip()
            core = re.sub(r"^\*\s*", "", core)   # '* .env.*' → '.env.*'
            core = re.sub(r"\s*\*$", "", core)   # 'git push *' → 'git push'
            core = core.rstrip("*").strip()      # '.env.*' → '.env.', 'rm -rf /*' → 'rm -rf /'
            if core:
                prefixes.add(core)
    if not prefixes:
        raise RuntimeError("ask · deny 규칙을 하나도 읽지 못했다")
    return sorted(prefixes)


def blocked_by(command: str) -> str | None:
    """명령 어디에든 규칙 조각이 단어 경계로 들어 있으면 그 조각을 돌려준다."""
    try:
        prefixes = guarded_prefixes()
    except Exception as exc:
        return f"(권한 규칙 확인 실패: {exc})"
    for core in prefixes:
        pattern = r"(?<![\w-])" + r"\s+".join(re.escape(tok) for tok in core.split()) + r"(?![\w-])"
        if core.endswith((".", "/")):  # '.env.' 처럼 뒤에 무엇이 와도 막아야 하는 조각
            pattern = pattern[: -len(r"(?![\w-])")]
        if re.search(pattern, command, flags=re.IGNORECASE):
            return core
    return None


# 로그에 쓰기 전에 가릴 비밀 패턴. 좁게 유지한다(증거를 임의로 줄이지 않기 위해).
SECRET_PATTERNS = [
    (re.compile(r"(password=)[^\s'\"]+"), r"\1***"),                 # libpq conninfo
    (re.compile(r"('password':\s*')[^']*(')"), r"\1***\2"),          # psycopg kwargs repr
    (re.compile(r"(://[^:\s'\"/@]+:)[^@\s'\"]+(@)"), r"\1***\2"),    # 접속 URL의 userinfo
]


def mask_secrets(text: str) -> str:
    """비밀번호로 보이는 조각을 *** 로 바꾼다. 파일에 쓰기 전에 부른다."""
    for pattern, repl in SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def find_bash() -> str:
    for cand in (shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"):
        if cand and Path(cand).exists():
            return cand
    sys.exit("bash를 찾지 못했다. 맥 · 리눅스는 시스템 bash, 윈도우는 Git Bash가 필요하다.")


def verify(evidence_dir: Path) -> int:
    manifest = evidence_dir / "MANIFEST.tsv"
    if not manifest.exists():
        print("MANIFEST.tsv 없음")
        return 1
    bad = 0
    total = ok = tampered = missing = 0  # 요약 줄용 집계. 판정은 아래 bad로만 한다
    for line in manifest.read_text(encoding="utf-8").splitlines()[1:]:
        seq, label, code, started, digest, name = line.split("\t")
        path = evidence_dir / name
        total += 1
        if not path.exists():
            print(f"없음   {name}")
            bad += 1
            missing += 1
        elif sha256(path) != digest:
            print(f"변조됨 {name}")
            bad += 1
            tampered += 1
        else:
            print(f"일치   {name}  (exit={code}, {started})")
            ok += 1
    print(f"합계 {total}  일치 {ok}  변조됨 {tampered}  없음 {missing}")
    return 1 if bad else 0


def main() -> int:
    # 윈도우 콘솔(cp949)에서도 한글 출력이 깨지거나 예외로 죽지 않게 한다 (맥 · 리눅스에서는 무해)
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) == 3 and sys.argv[2] == "--verify":
        return verify(Path(sys.argv[1]) / "evidence")
    if len(sys.argv) != 4:
        print(__doc__)
        return 2

    run_dir, label, command = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    hit = blocked_by(command)
    if hit:
        print(f"[evidence] 거부: 권한 규칙(ask · deny) 대상 '{hit}'이 들어 있다. "
              "이 도구로 감싸 실행하지 않는다. 직접 실행해 사람 확인을 받을 것.", file=sys.stderr)
        return 126
    if not run_dir.is_dir():
        sys.exit(f"run 폴더가 없다: {run_dir}")
    label = re.sub(r"[^0-9A-Za-z._-]+", "-", label).strip("-") or "cmd"
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    manifest = evidence_dir / "MANIFEST.tsv"
    if not manifest.exists():
        manifest.write_text("seq\tlabel\texit\tstarted\tsha256\tfile\n", encoding="utf-8")

    seq = sum(1 for _ in manifest.read_text(encoding="utf-8").splitlines())  # 헤더 포함 → 다음 번호
    name = f"{seq:02d}-{label}.log"

    started = now()
    # 자식 Python의 stdout · stderr가 파이프에서도 UTF-8로 쓰이게 한다(한국어 윈도우 기본은 cp949).
    # PYTHONUTF8=1보다 범위가 좁다: 표준 입출력만 바뀌고 open() 기본값은 그대로다.
    proc = subprocess.run([find_bash(), "-lc", command], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    finished = now()

    dirty = git("status", "--porcelain")
    body = "\n".join([
        f"# 증거 {name}",
        f"시작: {started}",
        f"끝:   {finished}",
        f"작업 폴더: {os.getcwd()}",
        f"git HEAD: {git('rev-parse', '--short', 'HEAD')}",
        f"변경 파일 수(git status --porcelain): {len(dirty.splitlines()) if dirty else 0}",
        f"명령: {command}",
        f"종료 코드: {proc.returncode}",
        "",
        "## stdout",
        proc.stdout.rstrip(),
        "",
        "## stderr",
        proc.stderr.rstrip(),
        "",
    ])
    # 파일에 쓰기 전에 마스킹한다. 해시는 이 내용으로 계산되므로 --verify 와 어긋나지 않는다.
    body = mask_secrets(body)
    path = evidence_dir / name
    # newline="" 로 줄바꿈 변환을 끈다. 기본값이면 윈도우에서 "\n" 이 "\r\n" 으로 바뀌어
    # 로그가 CRLF 로 저장되는데, .gitattributes(* text=auto eol=lf)가 커밋할 때 LF 로
    # 되돌리므로 MANIFEST 의 sha256(CRLF 기준)과 저장소 안의 파일이 어긋난다.
    # 그러면 증거 무결성 검증이 기록한 기계에서만 통과하고 다른 기계 · CI 에서는 실패한다.
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(body)
    with manifest.open("a", encoding="utf-8") as f:
        f.write(f"{seq}\t{label}\t{proc.returncode}\t{started}\t{sha256(path)}\t{name}\n")

    # 호출한 쪽도 결과를 바로 볼 수 있게 흘려 보낸다. 터미널 출력을 그대로 복사해
    # 붙이는 일이 있으므로 여기에도 같은 마스킹을 적용한다.
    sys.stdout.write(mask_secrets(proc.stdout))
    sys.stderr.write(mask_secrets(proc.stderr))
    print(f"\n[evidence] {path} (exit={proc.returncode})")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
