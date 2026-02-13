"""Tests for database models and CRUD operations."""

# Import after conftest has patched DB
from database.models import (
    get_all_positions,
    create_position,
    get_position_by_id,
    get_all_candidates,
    create_candidate,
    get_candidate_by_id,
    RecruitmentStage,
    CandidateStatus,
)


def test_create_and_get_position():
    """Create a position and retrieve it."""
    title = "Test Engineer"
    company = "Test Co"
    description = "Test description"
    pos = create_position(title=title, company=company, description=description)
    assert pos.id is not None
    assert pos.title == title
    assert pos.company == company
    assert pos.description == description

    fetched = get_position_by_id(pos.id)
    assert fetched is not None
    assert fetched.title == title
    assert fetched.company == company


def test_create_and_get_candidate():
    """Create a candidate and retrieve by id."""
    position_id = 1
    first_name = "Jan"
    last_name = "Testowy"
    email = "jan.test@example.com"
    candidate = create_candidate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        position_id=position_id,
        status=CandidateStatus.IN_PROGRESS,
        stage=RecruitmentStage.INITIAL_SCREENING,
        consent_for_other_positions=False,
    )
    assert candidate.id is not None
    assert candidate.first_name == first_name
    assert candidate.last_name == last_name
    assert candidate.email == email
    assert candidate.stage == RecruitmentStage.INITIAL_SCREENING

    fetched = get_candidate_by_id(candidate.id)
    assert fetched is not None
    assert fetched.first_name == first_name
    assert fetched.last_name == last_name
    assert fetched.email == email


def test_get_all_positions_returns_list():
    """get_all_positions should return a list (may be empty or seeded)."""
    positions = get_all_positions()
    assert isinstance(positions, list)


def test_get_all_candidates_returns_list():
    """get_all_candidates should return a list."""
    candidates = get_all_candidates()
    assert isinstance(candidates, list)
