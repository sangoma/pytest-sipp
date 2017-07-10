===========
pytest-sipp
===========

.. image:: https://travis-ci.org/sangoma/pytest-sipp.svg?branch=master
    :target: https://travis-ci.org/sangoma/pytest-sipp
    :alt: See Build Status on Travis CI

Automate `sipp`_ testing with `pytest_` and `pysipp`_. Orchestrate
python test code with multiple sipp processes.

Still unforuntately dependend on some of our internal pytest plugins
which we're slowly openning up. Currently still requires logging
support from our soon to be released pytest-logging plugging
(different from the one on PyPI from the saltstack guys).

Still also needs our documentation moved to here. That's coming
shortly as well.

Installation
------------

You can install "pytest-sipp" via `pip`_ from `PyPI`_::

    $ pip install pytest-sipp


Usage
-----

* TODO

Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `GNU GPL v3.0`_ license,
"pytest-sipp" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`GNU GPL v3.0`: http://www.gnu.org/licenses/gpl-3.0.txt
.. _`file an issue`: https://github.com/sangoma/pytest-sipp/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`sipp`: https://github.com/sipp/SIPp
.. _`pysipp`: https://github.com/sipp/pysipp
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.python.org/pypi/pip/
.. _`PyPI`: https://pypi.python.org/pypi
