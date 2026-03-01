"""Tests for route helpers."""

from unittest.mock import MagicMock

from routes.helpers import allowed_file, get_next_stage
from database.schema import RecruitmentStage


def test_allowed_file_accepts_pdf():
    """allowed_file accepts .pdf extension."""
    assert allowed_file("cv.pdf", {"pdf"}) is True
    assert allowed_file("document.PDF", {"pdf"}) is True


def test_allowed_file_rejects_other():
    """allowed_file rejects non-PDF extensions."""
    assert allowed_file("cv.docx", {"pdf"}) is False
    assert allowed_file("cv", {"pdf"}) is False


def test_get_next_stage_order():
    """get_next_stage returns next stage in order."""
    assert get_next_stage(RecruitmentStage.INITIAL_SCREENING) == RecruitmentStage.HR_INTERVIEW
    assert get_next_stage(RecruitmentStage.HR_INTERVIEW) == RecruitmentStage.TECHNICAL_ASSESSMENT
    assert get_next_stage(RecruitmentStage.TECHNICAL_ASSESSMENT) == RecruitmentStage.FINAL_INTERVIEW
    assert get_next_stage(RecruitmentStage.FINAL_INTERVIEW) == RecruitmentStage.OFFER


def test_get_next_stage_last_stage_unchanged():
    """At OFFER stage, get_next_stage returns OFFER."""
    assert get_next_stage(RecruitmentStage.OFFER) == RecruitmentStage.OFFER


def test_get_next_stage_unknown_returns_hr_interview():
    """When stage is not in order (ValueError), get_next_stage returns HR_INTERVIEW."""
    # Passing a value not in stage_order triggers ValueError and fallback to HR_INTERVIEW
    result = get_next_stage(MagicMock())
    assert result == RecruitmentStage.HR_INTERVIEW
