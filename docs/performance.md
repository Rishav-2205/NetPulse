# NetPulse: Performance Benchmarking & Statistical Methodology

## 1. High-Resolution Timing
All latency measurements in NetPulse utilize monotonic clock timestamps via Python's `time.perf_counter_ns()` to avoid wall-clock skew, NTP adjustments, or leap seconds.

---

## 2. Benchmark Metrics & Formulas

### 2.1 Throughput (Mbps)
Throughput measures the sustained transfer rate of raw payload data over a given measurement duration:
$$\text{Throughput (Mbps)} = \frac{\text{Bytes Transferred} \times 8}{\text{Duration (seconds)} \times 1,000,000}$$

### 2.2 Latency Percentiles (P50, P90, P95, P99)
Rather than relying solely on arithmetic mean latency (which obscures tail latency), NetPulse computes linear-interpolated percentiles:
$$r = \frac{p}{100} \times (n - 1)$$
$$P = S[\lfloor r \rfloor] \times (1 - (r - \lfloor r \rfloor)) + S[\lceil r \rceil] \times (r - \lfloor r \rfloor)$$

### 2.3 Statistical Variance & Baseline Stability
To prevent false-positive regression alerts, NetPulse computes the Coefficient of Variation ($CV$):
$$CV = \frac{s}{\bar{x}} = \frac{\sqrt{\frac{1}{n-1}\sum (x_i - \bar{x})^2}}{\bar{x}}$$

- **$CV < 5\%$**: Environment is **STABLE** (reliable for tight regression thresholds).
- **$5\% \le CV \le 15\%$**: Environment is **MODERATE** (normal baseline variance).
- **$CV > 15\%$**: Environment is **VOLATILE** (benchmarks should not trigger high-sensitivity regression alerts).
