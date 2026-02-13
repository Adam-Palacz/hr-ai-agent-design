"""Model response CRUD operations."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import get_db
from database.schema import ModelResponse


def save_model_response(
    agent_type: str,
    model_name: str,
    input_data: Optional[Any] = None,
    output_data: Optional[Any] = None,
    candidate_id: Optional[int] = None,
    feedback_email_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ModelResponse:
    """Save model response to database."""
    conn = get_db()
    cursor = conn.cursor()
    input_str = None
    if input_data is not None:
        input_str = (
            json.dumps(input_data, ensure_ascii=False, indent=2)
            if isinstance(input_data, (dict, list))
            else str(input_data)
        )
    output_str = None
    if output_data is not None:
        output_str = (
            json.dumps(output_data, ensure_ascii=False, indent=2)
            if isinstance(output_data, (dict, list))
            else str(output_data)
        )
    metadata_str = json.dumps(metadata, ensure_ascii=False, indent=2) if metadata else None
    cursor.execute(
        """
        INSERT INTO model_responses (agent_type, model_name, candidate_id, feedback_email_id, input_data, output_data, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (
            agent_type,
            model_name,
            candidate_id,
            feedback_email_id,
            input_str,
            output_str,
            metadata_str,
        ),
    )
    response_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ModelResponse(
        id=response_id,
        agent_type=agent_type,
        model_name=model_name,
        candidate_id=candidate_id,
        feedback_email_id=feedback_email_id,
        input_data=input_str,
        output_data=output_str,
        metadata=metadata_str,
        created_at=datetime.now(),
    )


def get_model_responses_for_candidate(candidate_id: int) -> List[ModelResponse]:
    """Get all model responses for a candidate."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM model_responses WHERE candidate_id = ? ORDER BY created_at DESC",
        (candidate_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        ModelResponse(
            id=row["id"],
            agent_type=row["agent_type"],
            model_name=row["model_name"],
            candidate_id=row["candidate_id"],
            feedback_email_id=(
                row["feedback_email_id"] if "feedback_email_id" in row.keys() else None
            ),
            input_data=row["input_data"],
            output_data=row["output_data"],
            metadata=row["metadata"] if "metadata" in row.keys() else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]


def get_all_model_responses() -> List[ModelResponse]:
    """Get all model responses from database."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM model_responses ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [
        ModelResponse(
            id=row["id"],
            agent_type=row["agent_type"],
            model_name=row["model_name"],
            candidate_id=row["candidate_id"],
            feedback_email_id=(
                row["feedback_email_id"] if "feedback_email_id" in row.keys() else None
            ),
            input_data=row["input_data"],
            output_data=row["output_data"],
            metadata=row["metadata"] if "metadata" in row.keys() else None,
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
        )
        for row in rows
    ]
