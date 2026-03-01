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
    pos = create_position(
        title="Test Role",
        company="Test Company",
        description="For test_create_and_get_candidate",
    )
    first_name = "Jan"
    last_name = "Testowy"
    email = "jan.test@example.com"
    candidate = create_candidate(
        first_name=first_name,
        last_name=last_name,
        email=email,
        position_id=pos.id,
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


def test_save_and_get_model_responses_for_candidate():
    """save_model_response and get_model_responses_for_candidate roundtrip."""
    from database.model_responses import save_model_response, get_model_responses_for_candidate

    pos = create_position(
        title="ModelResp Role",
        company="Test Co",
        description="For model response test",
    )
    assert pos is not None
    cand = create_candidate(
        first_name="Model",
        last_name="Resp",
        email="modelresp@test.com",
        position_id=pos.id,
        status=CandidateStatus.IN_PROGRESS,
        stage=RecruitmentStage.INITIAL_SCREENING,
    )
    assert cand is not None and cand.id is not None

    save_model_response(
        agent_type="feedback_generator",
        model_name="gpt-4o",
        candidate_id=cand.id,
        input_data={"test": "input"},
        output_data="<p>Test output</p>",
        metadata={"tokens": 10},
    )
    responses = get_model_responses_for_candidate(cand.id)
    assert isinstance(responses, list)
    assert len(responses) >= 1
    assert responses[0].agent_type == "feedback_generator"
    assert responses[0].model_name == "gpt-4o"
    assert responses[0].candidate_id == cand.id
