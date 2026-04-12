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
