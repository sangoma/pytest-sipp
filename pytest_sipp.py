import os.path
import re
import pytest
import pysipp
from pytest_exceptional import PytestException
from _pytest import fixtures
from _pytest.python import transfer_markers, Metafunc, PyobjMixin

try:
    from shutil import which
except ImportError:
    from backports.shutil_which import which


_DEFAULT_ROOT = None


def default_root(config):
    global _DEFAULT_ROOT

    if _DEFAULT_ROOT is None:
        _DEFAULT_ROOT = config.hook.pytest_sipp_collect_scripts(config=config)

    return _DEFAULT_ROOT


class SIPpNotFound(PytestException):
    """Missing dependencies error.
    """
    def toterminal(self, longrepr, tw):
        markup = dict(red=True, bold=True)

        tw.line()
        tw.write("    Could not find a suitable SIPp binary.", **markup)
        tw.line(" Is it installed properly?")
        tw.line("    See http://avina.qa.sangoma.local/sng_qa/sipp.html "
                "for instructions.")
        tw.line()


class SIPpTest(PyobjMixin, pytest.Item):
    def __init__(self, name, parent, obj, config=None, callspec=None,
                 keywords=None, session=None, fixtureinfo=None,
                 description=None):
        super(SIPpTest, self).__init__(name, parent, config=config,
                                       session=session)

        self.obj = obj
        self._obj = obj
        self.function = obj.function
        self.fixturenames = fixtureinfo.names_closure
        self._fixtureinfo = fixtureinfo
        self.funcargs = {}

        self.keywords.update(self.obj.__dict__)
        if callspec:
            self.callspec = callspec
            self.keywords.update(callspec.keywords)
            self._genid = callspec.id
            if hasattr(callspec, 'param'):
                self.param = callspec.param
        if keywords:
            self.keywords.update(keywords)

        self._request = fixtures.FixtureRequest(self)

    def runtest(self):
        self.ihook.pytest_pyfunc_call(pyfuncitem=self)

    def setup(self):
        super(SIPpTest, self).setup()
        fixtures.fillfixtures(self)


def generate_sipp_tests(metafunc, scen_node, **kwargs):
    sipp_conf = getattr(metafunc.function, 'sipp_conf', None)
    if sipp_conf:
        settings = dict(sipp_conf.kwargs)
        if not scen_node:
            scen_node = settings.pop('scen_node', None)
        settings.update(kwargs)
    else:
        settings = kwargs

    scripts_root = settings.get('scen_root', default_root(metafunc.config))
    plugins = settings.get('pysipp_plugins', [])
    exclude_expr = settings.get('exclude_expr')

    if not scen_node:
        metafunc.parametrize('sippscen',
                             [pysipp.scenario(autolocalsocks=False)],
                             ids=['default_sippscen'],
                             indirect=True)
        return
    elif os.path.isdir(scen_node):
        scen_path = scen_node
    else:
        scen_path = os.path.join(scripts_root, scen_node)

    if exclude_expr:
        class reject_by_pattern(object):
            def pysipp_load_scendir(self, path, xmls, confpy):
                if re.match(exclude_expr, path):
                    return False

        plugins.append(reject_by_pattern())

    # This walks the file system every time we want some
    # scenarios, and probably should be doing some caching, but
    # this is not the layer to put it.
    #
    # The problem is we want different scenario objects for every
    # test. Caching them will mean we end up sharing.
    with pysipp.plugin.register(plugins):
        scripts = list(pysipp.walk(scen_path, delay_conf_scen=True,
                                   autolocalsocks=False))

    try:
        paths, scenarios = zip(*scripts)
    except ValueError:
        fname = metafunc.function.__name__
        raise ValueError(
            "No SIPp scenarios could be found under {}\n"
            "The test '{}' has asked for scen_node '{}' under "
            "scen_root '{}'".format(
                scen_path, fname, scen_node, scripts_root
            )
        )

    metafunc.parametrize('sippscen',
                         scenarios,
                         ids=[path[len(scen_path)+1:] for path in paths],
                         indirect=True)


class SIPpTestDescription(object):
    def __init__(self, scen_node=None, **kwargs):
        self.function = None
        self.scen_node = scen_node
        self.kwargs = kwargs

    def __call__(self, function):
        self.function = function
        return self

    def __getattr__(self, key):
        # Pass through attribute access to the underlying method to
        # when necessary to keep pytest's introspection happy
        if self.function:
            return getattr(self.function, key)
        raise AttributeError(key)

    def generate_tests(self, metafunc):
        generate_sipp_tests(metafunc, self.scen_node, **self.kwargs)


@pytest.hookimpl
def pytest_pyfunc_call(pyfuncitem):
    testdescription = pyfuncitem.obj
    if not isinstance(testdescription, SIPpTestDescription):
        return

    config = pyfuncitem.config
    funcargs = pyfuncitem.funcargs
    argnames = pyfuncitem._fixtureinfo.argnames
    testargs = {arg: funcargs[arg] for arg in argnames}

    sippargs = dict(funcargs)
    sippargs.update(testdescription.kwargs)
    sippscen = sippargs.pop('sippscen')

    # TODO: Hack to get tests inside classes to work. I'm doing
    # something wrong if this isn't being handled for me.
    func_code = None
    func_code = getattr(testdescription.function, 'func_code', func_code)
    func_code = getattr(testdescription.function, '__code__', func_code)
    if 'self' in func_code.co_varnames:
        testargs['self'] = None

    testwrapper = testdescription.function(**testargs)
    try:
        excinfo = next(testwrapper)
    except StopIteration:
        raise RuntimeError("generator didn't yield")

    def run_sippscen():
        config.hook.pytest_run_sipp_scenario(item=pyfuncitem,
                                             sippscen=sippscen,
                                             sippargs=sippargs)

    try:
        if excinfo:
            with pytest.raises(excinfo):
                run_sippscen()
        else:
            run_sippscen()
    finally:
        try:
            next(testwrapper)
        except StopIteration:
            pass
        else:
            raise RuntimeError("generator didn't stop")

    config.hook.pytest_run_sipp_scenario_post(item=pyfuncitem,
                                              sippscen=sippscen)

    return True


@pytest.hookimpl
def pytest_run_sipp_scenario(item, sippscen, sippargs):
    pytest.log.info('Launching SIPp scenario {}...'.format(sippscen.dirpath))
    pytest.log.info('Running commands:\n{}'.format(sippscen.pformat_cmds()))

    timeout = sippargs.pop('timeout', 180)
    sippscen(timeout=timeout, **sippargs)


def gensipptests(collector, name, testdescription):
    funcobj = testdescription.function
    assert funcobj is not None

    module = collector.getparent(pytest.Module).obj
    clscol = collector.getparent(pytest.Class)
    cls = clscol and clscol.obj or None
    transfer_markers(testdescription, cls, module)

    fm = collector.session._fixturemanager
    fixtureinfo = fm.getfixtureinfo(collector, testdescription, cls)
    if 'sippscen' not in fixtureinfo.names_closure:
        fixtureinfo.names_closure.extend(['sippscen'])

    metafunc = Metafunc(testdescription, fixtureinfo, collector.config,
                        cls=cls, module=module)

    methods = [testdescription.generate_tests]
    if hasattr(module, "pytest_generate_tests"):
        methods.append(module.pytest_generate_tests)
    if hasattr(cls, "pytest_generate_tests"):
        methods.append(cls().pytest_generate_tests)

    # SIPp tests will always be parameterized
    collector.ihook.pytest_generate_tests.call_extra(methods,
                                                     dict(metafunc=metafunc))

    fixtures.add_funcarg_pseudo_fixture_def(collector, metafunc, fm)
    for callspec in metafunc._calls:
        subname = "%s[%s]" % (name, callspec.id)
        yield SIPpTest(name=subname,
                       parent=collector,
                       obj=testdescription,
                       callspec=callspec,
                       fixtureinfo=fixtureinfo,
                       keywords={callspec.id: True})


def sipp_test(scen_node=None, **kwargs):
    # Support direct decoration
    if callable(scen_node) and not kwargs:
        return SIPpTestDescription()(scen_node)

    return SIPpTestDescription(scen_node, **kwargs)


def issipptest(obj):
    # Depending on when this is run, either we still have the test
    # description class or we have a pytest item
    return (isinstance(obj, SIPpTest)
            or isinstance(obj, SIPpTestDescription))


@pytest.hookimpl
def pytest_namespace():
    return {'sipp_test': sipp_test,
            'issipptest': issipptest}


@pytest.hookimpl
def pytest_addoption(parser):
    group = parser.getgroup('sipp')
    group.addoption('--sipp-scen', '--sippscen', action='append', default=None,
                    help='path to the sipp scenario/script directory')
    group.addoption(
        '--sip-port', action='store', default=5060,
        help="default port the dut listen's on for sip requests"
             " (eg. default sip profile port)"
    )


@pytest.hookimpl
def pytest_pycollect_makeitem(collector, name, obj):
    if collector.funcnamefilter(name) and isinstance(obj, SIPpTestDescription):
        return list(gensipptests(collector, name, obj))


@pytest.hookimpl
def pytest_generate_tests(metafunc):
    # Handle parameterization of regular tests that use the sippscen
    # fixture directly, instead of the sipp_test wrapper
    if (not isinstance(metafunc.function, SIPpTestDescription)
            and 'sippscen' in metafunc.funcargnames):
        generate_sipp_tests(metafunc, None)


@pytest.fixture(scope='session')
def sipp_proxyaddr(request, dut_ip):
    '''Return the dut's default sip profile socket.
    (can be overridden from 5060 using --sip-port option)
    '''
    return dut_ip, request.config.getoption('--sip-port')


@pytest.fixture
def scen_db_path(request):
    """The path to the root of the SIPp scenario database
    """
    sipp_conf = request.node.get_marker('sipp_conf')
    if sipp_conf:
        return sipp_conf.kwargs.get('scen_root', default_root(request.config))
    return default_root(request.config)


@pytest.fixture
def sippscen(request):
    return request.param


@pytest.hookimpl
def pytest_runtest_protocol(item, nextitem):
    if issipptest(item.obj) and not which('sipp'):
        SIPpNotFound.makereport(item, when='setup')
        return True  # Do not continue with this test


@pytest.hookimpl
def pytest_addhooks(pluginmanager):
    class SIPpHook:
        @pytest.hookspec(firstresult=True)
        def pytest_sipp_collect_scripts(config):
            """Specify the default root for sipp scripts"""

        @pytest.hookspec(firstresult=True)
        def pytest_run_sipp_scenario(item, sippscen, sippargs):
            """Control how sippscen is called"""

        def pytest_run_sipp_scenario_post(item, sippscen):
            """Post test hook"""

    pluginmanager.add_hookspecs(SIPpHook())
