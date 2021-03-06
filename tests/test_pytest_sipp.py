import pytest


@pytest.fixture
def sipp_testdir(testdir):
    testdir.makeconftest('''
        import mock
        import pytest
        from pytest_sipp import SIPpTest

        pytest_plugins = 'sipp'

        MOCK_SCRIPTS = [
            'refer/attended_2call_multi_xfer',
            'refer/attended_2call_xfer_callee_refer',
            'siprelay/notify_option_disabled',
        ]

        def mock_walk(scen_path, **kwargs):
            for script in MOCK_SCRIPTS:
                if script.startswith(scen_path):
                    yield script, mock.MagicMock()

        @pytest.hookimpl(hookwrapper=True)
        def pytest_generate_tests(metafunc):
            with mock.patch('pysipp.walk', side_effect=mock_walk):
                yield

        @pytest.hookimpl(tryfirst=True)
        def pytest_run_sipp_scenario(item, sippscen, sippargs):
            if sippscen.abort:
                raise RuntimeError('Mock sipp failure')

            # Prevent sipp from actually being invoked
            return True

        @pytest.fixture
        def sippscen(request):
            sippscen = mock.MagicMock()
            sippscen.has_media = False
            sippscen.abort = False
            yield sippscen

            if isinstance(request.node, SIPpTest):
                assert run_scenario.called

        # We never actually invoke sipp for the unit tests, but
        # sipp_test won't actually run if the binary isn't found. Fake
        # it for CI.
        mock.patch('pytest_sipp.which', lambda *a, **kw: 'sipp').start()
    ''')

    return testdir


def test_direct_decoration(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        @pytest.sipp_test
        def test_sipp():
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] PASSED',
    ])


def test_indirect_decoration(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        @pytest.sipp_test()
        def test_sipp():
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] PASSED',
    ])


def test_with_scen_node(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        # TODO: scen_root needs to be overridden here or ids aren't
        # generated correctly
        pytestmark = pytest.mark.sipp_conf(scen_root='')

        @pytest.sipp_test(scen_node='refer')
        def test_sipp():
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]attended_2call_multi_xfer] PASSED',
    ])
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]attended_2call_xfer_callee_refer] PASSED'
    ])


def test_implicit_sippscen(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        pytestmark = pytest.mark.sipp_conf(scen_root='')

        def test_sipp(sippscen):
            pass
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] PASSED',
    ])


def test_sippscen_with_scen_node(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        pytestmark = pytest.mark.sipp_conf(scen_root='')

        @pytest.mark.sipp_conf(scen_node='refer')
        def test_sipp(sippscen):
            pass
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]attended_2call_multi_xfer] PASSED',
    ])
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]attended_2call_xfer_callee_refer] PASSED'
    ])


def test_conf_mixed_with_test(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        pytestmark = pytest.mark.sipp_conf(scen_root='')

        @pytest.mark.sipp_conf(scen_node='siprelay')
        @pytest.sipp_test
        def test_mark_inside():
            yield

        @pytest.sipp_test
        @pytest.mark.sipp_conf(scen_node='siprelay')
        def test_mark_outside():
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_mark_inside[[]notify_option_disabled] PASSED',
    ])
    result.stdout.fnmatch_lines([
        '*::test_mark_outside[[]notify_option_disabled] PASSED',
    ])


def test_raise_exception(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        @pytest.sipp_test
        def test_sipp(sippscen):
            sippscen.abort = True
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] FAILED',
    ])


def test_raise_expected_exception(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        @pytest.sipp_test
        def test_sipp(sippscen):
            sippscen.abort = True
            yield RuntimeError
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] PASSED',
    ])


def test_raise_wrong_expected_exception(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        @pytest.sipp_test
        def test_sipp():
            sippscen.abort = True
            yield AssertionError
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] FAILED',
    ])


def test_under_class(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest

        class TestSIPpClass:
            @pytest.sipp_test
            def test_sipp(self):
                yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*::test_sipp[[]default_sippscen] PASSED',
    ])


def test_sipp_missing(sipp_testdir):
    sipp_testdir.makepyfile('''
        import pytest
        import mock

        mock.patch('pytest_sipp.which', lambda *a, **kw: None).start()

        @pytest.sipp_test
        def test_sipp():
            yield
    ''')

    result = sipp_testdir.runpytest('-v')
    result.stdout.fnmatch_lines([
        '*Could not find a suitable SIPp binary. Is it installed properly?'
    ])
