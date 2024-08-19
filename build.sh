#!/usr/bin/env bash
set -e
set -x

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"

VENVDIR=.venv

if [ -z "${VIRTUAL_ENV}" ]; then
    echo "Virtual environment has been not activated"
    if ! [ -d "${THISDIR}/${VENVDIR}" ]; then
        echo "Create new virtual environment"
        python3.10 -m virtualenv -v --copies "${THISDIR}/${VENVDIR}"
    fi
fi

if [ -z "${VIRTUAL_ENV}" ]; then
    . "${THISDIR}/${VENVDIR}/bin/activate"
fi

python download_data.py --clean_data --jobs $(nproc)
