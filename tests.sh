#!/bin/sh
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2017, deadc0de6
# vim:sw=2 ts=2 sts=2 expandtab:

# stop on first error
#set -ev
set -e

# versions
echo "pylint version:"
pylint --version
echo "pycodestyle version:"
pycodestyle --version
echo "pyflakes version:"
pyflakes --version

# PEP8 tests
if ! command -v pycodestyle >/dev/null 2>&1; then
  echo "pycodestyle not found"
  exit 1
fi
echo "testing with pycodestyle"
pycodestyle --ignore=W503,W504,W605 dotdrop/
pycodestyle tests/
pycodestyle scripts/

# pyflakes tests
echo "testing with pyflakes"
pyflakes dotdrop/
pyflakes tests/

# pylint
echo "testing with pylint"
pylint \
  --disable=R0902 \
  --disable=R0913 \
  --disable=R0903 \
  --disable=R0914 \
  --disable=R0915 \
  --disable=R0912 \
  --disable=R0911 \
  --disable=R1732 \
  --disable=C0209 \
  dotdrop/

# coverage file location
rl="readlink -f"
if ! ${rl} "${0}" >/dev/null 2>&1; then
  rl="realpath"

  if ! hash ${rl}; then
    echo "\"${rl}\" not found!"
    exit 1
  fi
fi

# NOTE: this will fail if the script is run as `/bin/sh tests.sh`
SCRIPT_DIRECTORY="${0%/*}"
if [ -z "${SCRIPT_DIRECTORY}" ]; then
  SCRIPT_DIRECTORY="."
fi
export SCRIPT_DIRECTORY
if ! cur="$(cd "${SCRIPT_DIRECTORY}" && pwd -P)"; then
  echo "can't cd to the directory that '${0}' is in"
  exit 1
fi
unset -v SCRIPT_DIRECTORY

if [ -n "${DOTDROP_WORKERS+'is set'}" ]; then
  workers="${DOTDROP_WORKERS}"
  unset -v DOTDROP_WORKERS
  echo "DISABLE workers"
fi

# execute tests with coverage
if [ -z "${GITHUB_WORKFLOW}" ]; then
  ## local
  export COVERAGE_FILE=
  # do not print debugs when running tests (faster)
  unset -v DOTDROP_DEBUG
  export DOTDROP_FORCE_NODEBUG=yes
  # tests
  PYTHONPATH="dotdrop" nose2 \
    --with-coverage \
    --coverage dotdrop \
    --plugin=nose2.plugins.mp \
    -N0
else
  ## CI/CD
  export COVERAGE_FILE="${cur}/.coverage"
  # tests
  PYTHONPATH="dotdrop" nose2 \
    --with-coverage \
    --coverage dotdrop
fi
#PYTHONPATH="dotdrop" python3 -m pytest tests

### converted to here

DOTDROP_WORKDIR="$(mktemp -d)"
export DOTDROP_WORKDIR

if [ -n "${workers:+'is set and not empty'}" ]; then
  DOTDROP_WORKERS="${workers}"
  echo "ENABLE workers: ${DOTDROP_WORKERS}"
fi

# run bash tests
export DOTDROP_DEBUG="yes"
unset -v DOTDROP_FORCE_NODEBUG
if [ -z "${GITHUB_WORKFLOW+'is set'}" ]; then
  ## local
  export COVERAGE_FILE=
  tests-ng/tests-launcher.py
else
  ## CI/CD
  export COVERAGE_FILE="${cur}/.coverage"
  tests-ng/tests-launcher.py 1
fi

# clear workdir
if [ -d ~/.config/dotdrop/tmp ]; then
  rm -rf ~/.config/dotdrop/tmp
fi
# clear temp workdir
rm -rf "${DOTDROP_WORKDIR}"

## test the doc with remark
## https://github.com/remarkjs/remark-validate-links
if ! command -v remark >/dev/null 2>&1; then
  echo "[WARNING] install \"remark\" to test the doc"
else
  remark -f -u validate-links docs/
  remark -f -u validate-links *.md
fi

### test the doc with markdown-link-check
### https://github.com/tcort/markdown-link-check
#set +e
#which markdown-link-check >/dev/null 2>&1
#r="$?"
#set -e
#if [ "$r" != "0" ]; then
#  echo "[WARNING] install \"markdown-link-check\" to test the doc"
#else
#  for i in `find docs -iname '*.md'`; do markdown-link-check $i; done
#  markdown-link-check README.md
#fi

## done
echo "All test finished successfully"
