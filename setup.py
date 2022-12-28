# -*- coding: utf-8 -*-
"""install compile and deploy source-dist and wheel to pypi.python.org.

deps (requires up2date version):
    *) pip install --upgrade pip wheel setuptools twine
publish to pypi w/o having to convert Readme.md to RST:
    1) #> python setup.py sdist bdist_wheel
    2) #> twine upload dist/*   #<specify bdist_wheel version to upload>; #optional --repository <testpypi> or  --repository-url <testpypi-url>
"""
from setuptools import setup, find_packages
from setuptools.command.install import install
import sys
import os
import io

# Package meta-data.
NAME = "compile"
DESCRIPTION = "tool to find functions calling functions that are not implemented"
URL = "xxxx"
AUTHOR = "contract analyis"
AUTHOR_MAIL = None
REQUIRES_PYTHON = ">=3.6.0"


# What packages are required for this module to be executed?
REQUIRED = [
    
]

TESTS_REQUIRE = []

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# If version is set to None then it will be fetched from __version__.py
VERSION = None

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION


# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
    with open(os.path.join(here, project_slug, "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


# Package version (vX.Y.Z). It must match git tag being used for CircleCI
# deployment; otherwise the build will failed.
class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version."""

    description = "verify that the git tag matches our version"

    def run(self):
        """"""
        tag = os.getenv("CIRCLE_TAG")

        if tag != about["__version__"]:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, about["__version__"]
            )
            sys.exit(info)


setup(
    name=NAME,
    version=about["__version__"][1:],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",  # requires twine and recent setuptools
    url=URL,
    author=AUTHOR,
    author_mail=AUTHOR_MAIL,
    license="MIT",
    # classifiers=[
    #     "Development Status :: 3 - Alpha",
    #     "Intended Audience :: Science/Research",
    #     "Topic :: Software Development :: Disassemblers",
    #     "License :: OSI Approved :: MIT License",
    #     "Programming Language :: Python :: 3.6",
    #     "Programming Language :: Python :: 3.7",
    # ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: compile",
        "License :: None",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="contract function calls, functions not implemented",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=REQUIRED,
    tests_require=TESTS_REQUIRE,
    python_requires=REQUIRES_PYTHON,
    extras_require=EXTRAS,
    package_data={},
    include_package_data=True,
    entry_points={"console_scripts": ["compile=compile.identify_contract_calling_functionsWithNoCode:main"]},
    cmdclass={"verify": VerifyVersionCommand},
)
