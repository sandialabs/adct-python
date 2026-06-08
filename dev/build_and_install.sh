#! /bin/bash
if test -z "$VIRTUAL_ENV"; then
	# next line assumes user created virtual environment in directory ../.pyvenv
	# that was created with something like: python3 -m venv .pyvenv
	# next to a clone of this adct-python repository
	source ../.pyvenv/bin/activate
fi
# set proxy for pip
#If your site requires a pypi proxy, set it here unless it is the default in your shell.
# pip3 config set global.index someurl
# pip3 config set global.index-url someurl
# pip3 config set global.trusted-host someserver

# do once:
python3 -m pip install --require-virtualenv -r config/dev-requirements.txt

# do after installing per dev-requirements.txt or adding code
python3 -m build

# get output name X dist/*whl
X=$(ls -1tr dist/*.whl |tail -n 1)
python3 -m pip install --require-virtualenv --force-reinstall --no-deps $X
python3 -m pytest

# Run a demo
test_adctk_builder

# build documentation in doc/generated. Doxygen 1.16.1 or later is highly recommended.
doxygen Doxyfile
