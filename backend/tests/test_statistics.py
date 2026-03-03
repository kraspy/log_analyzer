"""Tests for statistics — _calculate_percentiles function.

The percentile function is a pure function with no DB dependency,
so it's easy to test in isolation.
"""

from log_analyzer.services.statistics import _calculate_percentiles


class TestCalculatePercentiles:
    """Tests for _calculate_percentiles."""

    def test_empty_list(self) -> None:
        """Empty input → all None."""
        avg, med, p95, p99 = _calculate_percentiles([])
        assert avg is None
        assert med is None
        assert p95 is None
        assert p99 is None

    def test_single_value(self) -> None:
        """Single value → all percentiles equal that value (in ms)."""
        avg, med, p95, p99 = _calculate_percentiles([0.1])
        assert avg == 100.0  # 0.1s = 100ms
        assert med == 100.0
        assert p95 == 100.0
        assert p99 == 100.0

    def test_two_values(self) -> None:
        """Two values → avg is mean, median is first (ceil-based)."""
        avg, med, p95, p99 = _calculate_percentiles([0.1, 0.3])
        assert avg == 200.0  # (100 + 300) / 2 = 200ms
        assert med == 100.0  # ceil(2 * 50/100) - 1 = 0 → index 0
        assert p95 == 300.0  # ceil(2 * 95/100) - 1 = 1 → index 1
        assert p99 == 300.0

    def test_known_distribution(self) -> None:
        """10 values → predictable percentile values.

        Response times (seconds): [0.01, 0.02, ..., 0.10]
        In milliseconds: [10, 20, 30, ..., 100]
        """
        values = [i / 100 for i in range(1, 11)]  # 0.01 to 0.10
        avg, med, p95, p99 = _calculate_percentiles(values)

        # Average: (10 + 20 + ... + 100) / 10 = 550 / 10 = 55ms
        assert avg == 55.0
        # Median (p50): ceil(10 * 0.5) - 1 = 4 → 0.05 → 50ms
        assert med == 50.0
        # P95: ceil(10 * 0.95) - 1 = 9 → 0.10 → 100ms
        assert p95 == 100.0
        # P99: ceil(10 * 0.99) - 1 = 9 → 0.10 → 100ms
        assert p99 == 100.0

    def test_large_spread(self) -> None:
        """Values with a long tail — p95/p99 should catch the spike."""
        # 90 normal requests + 10 slow requests = 100 total
        # Indices: 0-89 = 0.05s, 90-99 = 5.0s
        values = sorted([0.05] * 90 + [5.0] * 10)
        avg, med, p95, p99 = _calculate_percentiles(values)

        assert avg is not None
        assert med == 50.0  # Index 49 → 0.05s = 50ms
        # p95: ceil(100 * 0.95) - 1 = 94 → index 94 is in 90-99 range = 5.0s
        assert p95 == 5000.0
        # p99: ceil(100 * 0.99) - 1 = 98 → 5.0s = 5000ms
        assert p99 == 5000.0

    def test_values_converted_to_ms(self) -> None:
        """Verify results are in milliseconds (input is seconds)."""
        # 1 second → 1000ms
        avg, med, _p95, _p99 = _calculate_percentiles([1.0])
        assert avg == 1000.0
        assert med == 1000.0
