Installation
============

Requirements
------------

- Python 3.13+

Install from PyPI
-----------------

.. code-block:: bash

   python -m venv .venv
   source .venv/bin/activate
   pip install tseda

Run
---

.. code-block:: bash

   tseda

Build docs locally
------------------

.. code-block:: bash

   pip install -r docs/requirements.txt
   sphinx-build -b html docs/source docs/_build/html

Building and publishing
-----------------------

The project uses ``uv`` for building and publishing to PyPI.

Build the distribution artifacts:

.. code-block:: bash

   uv build

This produces a source distribution and a wheel under ``dist/``.

Publish to PyPI:

.. code-block:: bash

   uv publish --token YOUR_PYPI_TOKEN

Or set the token as an environment variable and publish:

.. code-block:: bash

   export UV_PUBLISH_TOKEN=pypi-...
   uv publish

To generate a PyPI API token, visit `https://pypi.org/manage/account/token/
<https://pypi.org/manage/account/token/>`_. Use *Entire account* scope for the
first upload of a new package, then narrow it to the specific project.
