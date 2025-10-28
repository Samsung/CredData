#!/bin/bash
set -e
set -x

.venv/bin/python review_data.py --check

.venv/bin/python3 download_data.py --clean_data --skip_download

find data -type f -exec chmod -x {} +

.venv/bin/python review_data.py meta data --short_line >review.$(date +%Y%m%d_%H%M%S).$(git rev-parse HEAD).$(git status --porcelain | grep -v '??' | wc -l).txt

.venv/bin/python -m benchmark --scanner credsweeper --load .ci/empty_report.json | tee .ci/benchmark.txt
