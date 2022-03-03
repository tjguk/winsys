import os
import re
from setuptools import setup

#
# setup.py framework shamelessly stolen from the
# Mu editor setup
#
base_dir = os.path.dirname(__file__)

DUNDER_ASSIGN_RE = re.compile(r"""^__\w+__\s*=\s*['"].+['"]$""")
about = {}
with open(os.path.join(base_dir, "winsys", "__init__.py"), encoding="utf8") as f:
    for line in f:
        if DUNDER_ASSIGN_RE.search(line):
            exec(line, about)

TO_STRIP = set([":class:", ":mod:", ":meth:", ":func:"])
with open(os.path.join(base_dir, "README.rst"), encoding="utf8") as f:
    readme = f.read()
    for s in TO_STRIP:
        readme = readme.replace(s, "")

#~ with open(os.path.join(base_dir, "CHANGES.rst"), encoding="utf8") as f:
    #~ changes = f.read()
changes = ""

install_requires = [
    "pywin32"
]
extras_require = {
    "tests": [
        "pytest",
    ],
    "docs": ["sphinx"],
    "package": [
        # Wheel building and PyPI uploading
        "wheel",
        "twine",
    ],
}
extras_require["dev"] = (
    extras_require["tests"]
    + extras_require["docs"]
    + extras_require["package"]
)
extras_require["all"] = list(
    {req for extra, reqs in extras_require.items() for req in reqs}
)

setup(
    name=about["__title__"],
    version=about["__version__"],
    description=about["__description__"],
    long_description="{}\n\n{}".format(readme, changes),
    long_description_content_type = "text/x-rst",
    author=about["__author__"],
    author_email=about["__email__"],
    url=about["__url__"],
    license=about["__license__"],
    packages = ['winsys', 'winsys._security', 'winsys.extras'],
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True,
    zip_safe=False,
    classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Console',
      'Intended Audience :: System Administrators',
      'License :: OSI Approved :: MIT License',
      'Operating System :: Microsoft :: Windows :: Windows NT/2000',
      'Programming Language :: Python :: 3',
      'Topic :: Utilities',
    ],
    platforms='win32'
)

