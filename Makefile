all: format check

install-tools:
	pip3 install flake8
	pip3 install yapf

check:
	flake8 pg_cloudconfig

format:
	yapf --style pep8 -i -r .
