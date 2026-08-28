# NetPulse: Regression Intelligence & Controlled Experiments

## 1. Controlled Experiment vs. Performance Regression

A critical distinction in NetPulse is separating **Intentional Degradation** from **Software Regressions**:
- **Expected Degradation (`EXPECTED_DEGRADATION`)**: When a test engineer deliberately applies a 50ms latency fault or a 2% loss fault, any observed latency increase or packet loss that aligns with that fault is classified as expected experimental behavior.
- **Unexpected Regression (`UNEXPECTED_REGRESSION`)**: When performance drops on a **clean link**, or when observed degradation significantly exceeds the configured fault bounds.

---

## 2. Regression Tolerance Thresholds

The `RegressionThresholds` model in `app/regression/thresholds.py` defines standard evaluation tolerances:
- **Throughput Drop**: $> 10.0\%$ decrease triggers a throughput regression.
- **Latency Increase**: $> 15.0\%$ increase triggers a latency regression.
- **Packet Loss Increase**: $> 1.0\%$ increase triggers a loss regression.
- **Execution Duration Growth**: $> 30.0\%$ execution time growth triggers a performance duration regression.
- **Status Change**: Any test transitioning from `PASS` $\rightarrow$ `FAIL` or `ERROR` triggers an immediate functional regression.
