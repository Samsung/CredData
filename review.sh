#!/bin/bash
set -e
set -x

THISDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" > /dev/null 2>&1 && pwd )"

.venv/bin/python3 download_data.py --clean_data --skip_download

find data -type f -exec chmod -x {} +

.venv/bin/python review_data.py meta data >review.$(date +%Y%m%d_%H%M%S).$(git rev-parse HEAD).$(git status --porcelain | grep -v '??' | wc -l).txt

.venv/bin/python -m benchmark --scanner credsweeper --load .ci/empty_report.json | tee .ci/benchmark.txt
