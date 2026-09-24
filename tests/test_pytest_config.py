"""pytest.ini 설정 자체가 실패를 삼키지 않는지 확인한다.

T1-T6은 pytester.runpytest_subprocess로, 저장소 루트의 실제 pytest.ini를
복사한 내부 세션을 띄워 확인한다. T7은 이 파일 자신이 도는 성공 경로다.
내용은 ASCII만 쓴다.
"""

import pytest


def _install_ini(pytester, request, extra_lines=None):
    """저장소 루트의 pytest.ini 내용을 pytester의 임시 폴더에 그대로 복사한다."""
    text = (request.config.rootpath / "pytest.ini").read_text(encoding="ascii")
    if extra_lines:
        text = text + "\n" + "\n".join(extra_lines) + "\n"
    pytester.makefile(".ini", pytest=text)


def test_async_test_without_marker_fails(pytester, request):
    _install_ini(pytester, request)
    pytester.makepyfile(
        test_unmarked="""
        async def test_it():
            pass
        """
    )
    result = pytester.runpytest_subprocess("test_unmarked.py")
    result.assert_outcomes(failed=1, passed=0)
    result.stdout.fnmatch_lines(["*async def functions are not natively supported*"])


def test_marked_async_test_body_actually_runs(pytester, request):
    _install_ini(pytester, request)
    pytester.makepyfile(
        test_marked="""
        import asyncio
        import pytest

        @pytest.mark.asyncio
        async def test_it():
            await asyncio.sleep(0)
            assert False, "body executed"
        """
    )
    result = pytester.runpytest_subprocess("test_marked.py")
    result.assert_outcomes(failed=1, passed=0)
    result.stdout.fnmatch_lines(["*body executed*"])


def test_unregistered_marker_is_error(pytester, request):
    _install_ini(pytester, request)
    pytester.makepyfile(
        test_bad_marker="""
        import pytest

        @pytest.mark.integraton
        def test_it():
            pass
        """
    )
    result = pytester.runpytest_subprocess("test_bad_marker.py")
    assert result.ret != 0
    result.assert_outcomes(errors=1)
    combined = result.stdout.str() + result.stderr.str()
    assert "'integraton' not found in `markers` configuration option" in combined


def test_unknown_ini_option_is_error(pytester, request):
    _install_ini(pytester, request, extra_lines=["asyncio_mod = auto"])
    pytester.makepyfile(
        test_dummy="""
        def test_it():
            pass
        """
    )
    result = pytester.runpytest_subprocess("test_dummy.py")
    assert result.ret == pytest.ExitCode.USAGE_ERROR
    combined = result.stdout.str() + result.stderr.str()
    assert "Unknown config option: asyncio_mod" in combined


def test_integration_marker_not_deselected_by_default(pytester, request):
    _install_ini(pytester, request)
    pytester.makepyfile(
        test_mix="""
        import pytest

        def test_normal():
            pass

        @pytest.mark.integration
        def test_needs_services():
            pass
        """
    )

    result = pytester.runpytest_subprocess("test_mix.py")
    result.assert_outcomes(passed=2)

    result = pytester.runpytest_subprocess("test_mix.py", "-m", "not integration")
    result.assert_outcomes(passed=1, deselected=1)

    result = pytester.runpytest_subprocess("test_mix.py", "-m", "integration")
    result.assert_outcomes(passed=1, deselected=1)


def test_pytest_ini_settings(pytester, request):
    _install_ini(pytester, request)
    pytester.makepyfile(
        test_introspect="""
        def test_settings(pytestconfig):
            assert pytestconfig.getini("asyncio_mode") == "strict"
            assert pytestconfig.getini("strict") is True
            assert pytestconfig.getini("asyncio_default_fixture_loop_scope") == "function"
            markers = pytestconfig.getini("markers")
            assert any(m.startswith("integration:") for m in markers)
        """
    )
    result = pytester.runpytest_subprocess("test_introspect.py")
    result.assert_outcomes(passed=1)


@pytest.mark.asyncio
async def test_asyncio_smoke():
    import asyncio

    assert asyncio.get_running_loop() is not None
    await asyncio.sleep(0)
