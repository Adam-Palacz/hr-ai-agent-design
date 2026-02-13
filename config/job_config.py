"""Job offer and HR feedback configuration loader."""

import json
from pathlib import Path
from typing import Dict, Any

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from models.job_models import JobOffer
from models.feedback_models import HRFeedback, Decision
from core.logger import logger
from core.exceptions import ConfigurationError


def load_job_config(config_path: str) -> Dict[str, Any]:
    """
    Load job configuration from JSON or YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Dictionary with configuration data

    Raises:
        ConfigurationError: If file cannot be loaded
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            if config_file.suffix.lower() == ".yaml" or config_file.suffix.lower() == ".yml":
                if not YAML_AVAILABLE:
                    raise ConfigurationError(
                        "YAML file detected but PyYAML not installed. "
                        "Install it with: pip install pyyaml"
                    )
                config = yaml.safe_load(f)
            else:
                config = json.load(f)

        logger.info(f"Loaded configuration from: {config_path}")
        return config

    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in config file: {str(e)}")
    except NameError:
        # yaml not available
        raise ConfigurationError(
            "YAML file detected but PyYAML not installed. " "Install it with: pip install pyyaml"
        )
    except Exception as e:
        if "yaml" in str(type(e)).lower():
            raise ConfigurationError(f"Invalid YAML in config file: {str(e)}")
        raise ConfigurationError(f"Error loading config file: {str(e)}")


def create_job_offer_from_config(config: Dict[str, Any]) -> JobOffer:
    """
    Create JobOffer from configuration dictionary.

    Args:
        config: Configuration dictionary

    Returns:
        JobOffer object
    """
    job_data = config.get("job_offer", {})

    # Get description - can be string or can combine multiple fields
    description = job_data.get("description", "")

    # If description is missing but other fields exist, combine them
    if not description:
        parts = []
        if job_data.get("title"):
            parts.append(f"Position: {job_data.get('title')}")
        if job_data.get("requirements"):
            parts.append("\nRequirements:")
            for req in job_data.get("requirements", []):
                if isinstance(req, str):
                    parts.append(f"- {req}")
                elif isinstance(req, dict):
                    req_text = req.get("requirement", "")
                    parts.append(f"- {req_text}")
        if job_data.get("nice_to_have"):
            parts.append("\nNice to have:")
            for item in job_data.get("nice_to_have", []):
                parts.append(f"- {item}")
        description = "\n".join(parts) if parts else ""

    # Ensure description is not empty
    if not description:
        description = job_data.get("title", "No description provided")

    return JobOffer(
        title=job_data.get("title", ""),
        company=job_data.get("company"),
        location=job_data.get("location"),
        description=description,
    )


def create_hr_feedback_from_config(config: Dict[str, Any], job_offer: JobOffer) -> HRFeedback:
    """
    Create HRFeedback from configuration dictionary.

    Args:
        config: Configuration dictionary
        job_offer: JobOffer object for reference

    Returns:
        HRFeedback object
    """
    feedback_data = config.get("hr_feedback", {})

    # Convert decision string to Decision enum
    decision_str = feedback_data.get("decision", "pending").lower()
    try:
        decision = Decision(decision_str)
    except ValueError:
        logger.warning(f"Invalid decision '{decision_str}', defaulting to 'pending'")
        decision = Decision.PENDING

    # Note: strengths and weaknesses are now extracted automatically by AI from notes
    # We only read notes from config, AI will analyze it and extract strengths/weaknesses
    return HRFeedback(
        decision=decision,
        strengths=[],  # Will be extracted by AI from notes
        weaknesses=[],  # Will be extracted by AI from notes
        notes=feedback_data.get("notes"),
        position_applied=job_offer.title,
        interviewer_name=feedback_data.get("interviewer_name"),
        missing_requirements=feedback_data.get("missing_requirements", []),
    )
