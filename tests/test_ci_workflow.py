"""ci.yml이 실패를 삼키지 않는지 텍스트로 확인한다 (회귀 방지).

PyYAML은 import하지 않는다. ci.yml을 encoding="utf-8"로 텍스트만 읽는다.
"""

import re

REQUIRED_JOBS = {"pytest", "opa-test"}
JOB_HEADER_RE = re.compile(r"^  ([a-zA-Z][\w-]*):\s*$", re.M)

USES_RE = re.compile(r"uses:\s*(\S+)(.*)$", re.M)
PINNED_RE = re.compile(r"^[\w.-]+/[\w.-]+@[0-9a-f]{40}$")
TAG_COMMENT_RE = re.compile(r"^\s*#\s*v\d+\.\d+\.\d+\s*$")

EXPECTED_PYTEST_RUNS = [
    "python -m pip install -r requirements-dev.txt",
    "python -m pip check",
    "python -m pytest -q --junitxml=test-results/pytest-junit.xml",
]
EXPECTED_OPA_RUN = (
    '          out="$(docker compose run --rm opa test /policies -v)"\n'
    '          printf "%s\\n" "$out"\n'
    '          grep -Eq "^PASS: [1-9][0-9]*/[1-9][0-9]*" <<<"$out"'
)


def _ci_text(request):
    path = request.config.rootpath / ".github" / "workflows" / "ci.yml"
    return path.read_text(encoding="utf-8")


def _job_blocks(text):
    """'jobs:' 아래, 2칸 들여쓰기 job 헤더마다 그 job의 본문(다음 job 헤더 전까지)을 돌려준다."""
    jobs_idx = text.index("\njobs:\n")
    jobs_text = text[jobs_idx + len("\njobs:\n") :]
    headers = list(JOB_HEADER_RE.finditer(jobs_text))
    blocks = {}
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(jobs_text)
        blocks[m.group(1)] = jobs_text[start:end]
    return blocks


def test_ci_workflow_does_not_swallow_failures(request):
    text = _ci_text(request)
    assert "continue-on-error" not in text
    for bad in ("|| true", "|| :", "|| exit 0"):
        assert bad not in text
    assert "set +e" not in text

    if_lines = [line.strip() for line in text.splitlines() if line.strip().startswith("if:")]
    assert if_lines == ["if: always()"]

    assert "shell: bash" in text

    blocks = _job_blocks(text)
    assert blocks, "no jobs found"
    assert REQUIRED_JOBS <= blocks.keys(), f"missing required jobs: {REQUIRED_JOBS - blocks.keys()}"
    missing_timeout = [
        name
        for name, block in blocks.items()
        if not re.search(r"^\s*timeout-minutes:\s*\d+\s*$", block, flags=re.M)
    ]
    assert not missing_timeout, f"jobs without timeout-minutes: {missing_timeout}"


def test_ci_workflow_actions_pinned_to_commit_sha(request):
    text = _ci_text(request)
    uses = USES_RE.findall(text)
    assert uses, "no uses: lines found"
    for ref, rest in uses:
        assert PINNED_RE.match(ref), f"not pinned to a 40-hex commit sha: {ref}"
        assert TAG_COMMENT_RE.match(rest), f"missing '# vX.Y.Z' comment: {ref}{rest}"


def test_ci_workflow_runs_same_commands_as_local(request):
    text = _ci_text(request)
    for cmd in EXPECTED_PYTEST_RUNS:
        assert cmd in text
    assert EXPECTED_OPA_RUN in text
    assert "path: test-results/pytest-junit.xml" in text
    assert re.search(r'python-version:\s*"3\.13\.7"', text)
    assert "ubuntu-latest" not in text


def test_ci_workflow_has_no_secrets_and_read_only_token(request):
    text = _ci_text(request)
    assert "secrets." not in text

    lines = text.splitlines()
    permissions_idx = [i for i, line in enumerate(lines) if line.strip() == "permissions:"]
    assert len(permissions_idx) == 1, "expected exactly one permissions: block (no job-level permissions:)"
    idx = permissions_idx[0]
    base_indent = len(lines[idx]) - len(lines[idx].lstrip(" "))

    # permissions: 바로 아래, 더 깊이 들여쓰기된 연속 줄을 전부 모은다.
    # 한 줄이라도 더 있으면(예: pull-requests: write) 여기서 걸린다.
    block = []
    for line in lines[idx + 1 :]:
        if not line.strip():
            continue
        cur_indent = len(line) - len(line.lstrip(" "))
        if cur_indent <= base_indent:
            break
        block.append(line.strip())
    assert block == ["contents: read"], f"permissions block must be exactly ['contents: read'], got {block}"

    persist_count = len(re.findall(r"persist-credentials:\s*false", text))
    assert persist_count == 2
