# Python API README

# adct-python
Application Data Collection Toolkit for Python

- This is a library-only ADCT python implementation for https://github.com/sandialabs/adct .
  - It is intended to support standard python types and numpy data types.
  - Package requirements for development of adct-python are in config/dev-requirements.txt
  - A single factory class provides interface objects.
  - Documentation is generated during the build and installed (also soon available at: https://sandialabs.github.io/adct-python/).

- This optionally depends on libldms from ldms 4.5.2 or later.

## Documentation & Testing
Development of comprehensive tutorial examples and feature tests is on-going.
- The primary functionality test is src/adctk/scripts/test\_adctk\_builder.py

Code-based documentation is built with doxygen as part of a normal install.

## Installing from github
It is recommended that users install this inside a virtual environment ([python](https://docs.python.org/3/library/venv.html), [conda](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html)).

# Requirements:

Python 3.10 or later is required for use.

## Development Workflows:

Development should be done within a python virtual environment.
The script `./dev/build_and_install.sh` demonstrates installing the package.

## CI System
Coming soon

