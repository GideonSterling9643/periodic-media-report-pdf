from pathlib import Path

import pytest

from src.report_service import MediaAsset, render_markdown


def test_report_totals_streaming_minutes_and_rows():
    assets = [MediaAsset("a1", "Ledger cast", 12, "EU"), MediaAsset("a2", "Risk notes", 8, "US")]
    report = render_markdown("2026-08", assets)
    assert "Total streamed minutes: **20**" in report
    assert "| a1 | Ledger cast | EU | 12 |" in report


def test_empty_period_is_rejected_by_business_rule():
    from src.report_service import archive_period
    with pytest.raises(ValueError, match="at least one asset"):
        archive_period("2026-08", [], object(), Path("archive"), "bucket")
