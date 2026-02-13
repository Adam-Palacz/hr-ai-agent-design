"""Shared helpers for routes."""

from database.schema import RecruitmentStage


def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def get_next_stage(current_stage: RecruitmentStage) -> RecruitmentStage:
    """Get next recruitment stage."""
    stage_order = [
        RecruitmentStage.INITIAL_SCREENING,
        RecruitmentStage.HR_INTERVIEW,
        RecruitmentStage.TECHNICAL_ASSESSMENT,
        RecruitmentStage.FINAL_INTERVIEW,
        RecruitmentStage.OFFER,
    ]
    try:
        current_index = stage_order.index(current_stage)
        if current_index < len(stage_order) - 1:
            return stage_order[current_index + 1]
        return current_stage
    except ValueError:
        return RecruitmentStage.HR_INTERVIEW
