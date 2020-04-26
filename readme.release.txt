Check out and install the latest version
--------------------------------------

git clone https://github.com/tjguk/winsys && cd winsys && py -3 -mvenv .venv && .venv\scripts\python -mpip install --upgrade pip && .venv\scripts\activate && pip install -e .[all]


Build the distributables
------------------------

python setup.py sdist bdist_wheel


Check and upload the distributables
-----------------------------------

twine check dist/*
twine upload --repository-url https://test.pypi.org/legacy/ -u tim.golden dist/*
twine upload -u tim.golden dist/*

