# Directory to store auxiliary CI/CD files

The following files are used for:
  * **benchmark.txt** - template scores to compare it with empty result

To update the benchmark file, do:

```.venv/bin/python -m benchmark --scanner credsweeper --load .ci/empty_report.json | tee .ci/benchmark.txt```


  * **empty_report.json** - empty report from CredSweeper
