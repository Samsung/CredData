#!/bin/bash
set -e
set -x

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"

VENVDIR=venv

if [ -z "${VIRTUAL_ENV}" ]; then
    echo "Virtual environment has been not activated"
    if ! [ -d "${THISDIR}/${VENVDIR}" ]; then
        echo "Create new virtual environment"
        python3.8 -m virtualenv -v --copies "${THISDIR}/${VENVDIR}"
    fi
fi

if [ -z "${VIRTUAL_ENV}" ]; then
    . "${THISDIR}/${VENVDIR}/bin/activate"
fi

which pip
which python

pip install -r requirements.txt

export PYTHON_HYPERSCAN_STATIC=false
python -m benchmark --scanner credsweeper

