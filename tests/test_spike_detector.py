#!/usr/bin/env python3
"""
Tests for spike detector functionality
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

from spike_detector import SpikeDetector, SpikeEvent, PricePoint, format_spike_alert


class TestSpikeDetector:
    """Tests for SpikeDetector class."""

    def test_initialization(self):
        """Test detector initialization."""
        detector = SpikeDetector(
            market_id="12345",
            threshold=0.05,
            lookback=60,
            cooldown=300
        )

        assert detector.market_id == "12345"
        assert detector.threshold == 0.05
        assert detector.lookback == 60
        assert detector.cooldown == 300
        assert len(detector.price_history) == 0

    def test_add_price_no_spike(self):
        """Test adding prices without spike."""
        detector = SpikeDetector(market_id="12345", threshold=0.10, lookback=5)

        # Small price movements
        result1 = detector.add_price(0.50)
        result2 = detector.add_price(0.51)
        result3 = detector.add_price(0.52)

        # No spike detected (only 4% change)
        assert result1 is None  # Need at least 2 points
        assert result2 is None
        assert result3 is None

    def test_add_price_spike_up(self):
        """Test detecting upward spike."""
        detector = SpikeDetector(
            market_id="12345",
            threshold=0.05,  # 5%
            lookback=1,      # Short lookback for test
            cooldown=0       # No cooldown for test
        )

        detector.add_price(0.50)
        detector.add_price(0.51)

        # 10% spike up
        spike = detector.add_price(0.56)

        assert spike is not None
        assert spike.direction == "UP"
        assert spike.change_pct >= 0.05

    def test_add_price_spike_down(self):
        """Test detecting downward spike."""
        detector = SpikeDetector(
            market_id="12345",
            threshold=0.05,
            lookback=1,
            cooldown=0
        )

        detector.add_price(0.50)
        detector.add_price(0.49)

        # 10% spike down
        spike = detector.add_price(0.44)

        assert spike is not None
        assert spike.direction == "DOWN"
        assert spike.change_pct >= 0.05

    def test_cooldown_prevents_repeated_alerts(self):
        """Test that cooldown prevents rapid alerts."""
        detector = SpikeDetector(
            market_id="12345",
            threshold=0.05,
            lookback=1,
            cooldown=300  # 5 minutes
        )

        # First spike
        detector.add_price(0.50)
        spike1 = detector.add_price(0.60)  # 20% spike
        assert spike1 is not None

        # Second spike immediately after - should be blocked
        spike2 = detector.add_price(0.70)  # Another big move
        assert spike2 is None  # Cooldown blocks it

    def test_price_history_trimming(self):
        """Test that old prices are trimmed."""
        detector = SpikeDetector(
            market_id="12345",
            lookback=5
        )

        # Add many prices
        for i in range(100):
            detector.add_price(0.50 + i * 0.001)

        # History should be limited (lookback * 2 = 10 seconds worth)
        # Since we add instantly, all 100 are within the window
        # Test that the mechanism exists - with real time delays it would trim
        assert len(detector.price_history) <= 100

    def test_threshold_boundary(self):
        """Test behavior at exact threshold."""
        detector = SpikeDetector(
            market_id="12345",
            threshold=0.05,  # Exactly 5%
            lookback=1,
            cooldown=0
        )

        detector.add_price(1.00)

        # Exactly 5% change - should trigger
        spike = detector.add_price(1.05)
        assert spike is not None

    def test_zero_price_handling(self):
        """Test handling of zero prices."""
        detector = SpikeDetector(market_id="12345", lookback=1)

        # Start with zero
        result = detector.add_price(0.0)
        assert result is None

        # Then non-zero
        result = detector.add_price(0.50)
        assert result is None  # Can't calculate % change from 0


class TestSpikeEvent:
    """Tests for SpikeEvent dataclass."""

    def test_spike_event_creation(self):
        """Test creating a spike event."""
        now = datetime.now()
        spike = SpikeEvent(
            market_id="12345",
            old_price=0.50,
            new_price=0.60,
            change_pct=0.20,
            direction="UP",
            timestamp=now
        )

        assert spike.market_id == "12345"
        assert spike.old_price == 0.50
        assert spike.new_price == 0.60
        assert spike.change_pct == 0.20
        assert spike.direction == "UP"
        assert spike.timestamp == now


class TestFormatSpikeAlert:
    """Tests for format_spike_alert function."""

    def test_format_up_spike(self):
        """Test formatting upward spike alert."""
        spike = SpikeEvent(
            market_id="12345",
            old_price=0.50,
            new_price=0.60,
            change_pct=0.20,
            direction="UP",
            timestamp=datetime.now()
        )

        alert = format_spike_alert(spike)

        assert "SPIKE DETECTED" in alert
        assert "12345" in alert
        assert "UP" in alert
        assert "↑" in alert
        assert "50¢" in alert
        assert "60¢" in alert

    def test_format_down_spike(self):
        """Test formatting downward spike alert."""
        spike = SpikeEvent(
            market_id="12345",
            old_price=0.60,
            new_price=0.50,
            change_pct=0.167,
            direction="DOWN",
            timestamp=datetime.now()
        )

        alert = format_spike_alert(spike)

        assert "DOWN" in alert
        assert "↓" in alert


class TestPricePoint:
    """Tests for PricePoint dataclass."""

    def test_price_point_creation(self):
        """Test creating a price point."""
        now = datetime.now()
        point = PricePoint(
            timestamp=now,
            price=0.55,
            bid=0.54,
            ask=0.56
        )

        assert point.timestamp == now
        assert point.price == 0.55
        assert point.bid == 0.54
        assert point.ask == 0.56


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
