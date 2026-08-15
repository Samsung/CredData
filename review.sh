#!/bin/bash

set -ex

.venv/bin/python3 review_data.py --check

.venv/bin/python3 download_data.py --clean_data --jobs $(nproc) --skip_download

find data -type f -exec chmod -x {} +

.venv/bin/python3 review_data.py meta data >review.$(date +%Y%m%d_%H%M%S).$(git rev-parse HEAD).$(git status --porcelain | grep -v '??' | wc -l).txt

.venv/bin/python3 -m benchmark --scanner credsweeper --load .ci/empty_report.json | tee .ci/benchmark.txt
