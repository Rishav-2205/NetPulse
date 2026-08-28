#!/usr/bin/env bash
# NetPulse End-to-End Demonstration Script (Bash)
set -e

echo "========================================================="
echo "NetPulse: Automated Network Validation & Performance Engine"
echo "========================================================="

# 1. Check Python version
python3 --version

# 2. Run test suites
pytest tests/functional tests/regression tests/integration -v

# 3. Run performance benchmarks
python3 -m netpulse benchmark --profile quick --compare-baseline --html

# 4. Export test case catalog
python3 -m netpulse catalog

# 5. Output report status
python3 -m netpulse report

echo "========================================================="
echo "NetPulse Demo Complete! Reports saved in reports/"
echo "========================================================="
