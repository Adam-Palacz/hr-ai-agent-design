"""Main application entry point with job offer configuration support."""

import sys
from pathlib import Path

from config import settings
from config.job_config import (
    load_job_config,
    create_job_offer_from_config,
    create_hr_feedback_from_config,
)
from core.logger import logger, setup_logger
from core.exceptions import CVProcessingError, ConfigurationError
from agents.cv_parser_agent import CVParserAgent
from agents.feedback_agent import FeedbackAgent
from services.cv_service import CVService
from services.feedback_service import FeedbackService
from models.feedback_models import FeedbackFormat


def main():
    """Main application function."""
    # Setup logging
    setup_logger(log_level=settings.log_level)
    logger.info("Starting CV processing application")

    try:
        # Get PDF path from command line or use default
        if len(sys.argv) > 1:
            pdf_path = sys.argv[1]
        else:
            pdf_path = "cv.pdf"

        # Get config path from command line or use default
        if len(sys.argv) > 2:
            config_path = sys.argv[2]
        else:
            config_path = "config/job_config.json"

        # Validate inputs
        if not Path(pdf_path).exists():
            logger.error(f"PDF file not found: {pdf_path}")
            print(f"❌ PDF file not found: {pdf_path}")
            print("Usage: python main.py <pdf_path> [config_path]")
            return

        if not Path(config_path).exists():
            logger.error(f"Config file not found: {config_path}")
            print(f"❌ Config file not found: {config_path}")
            print("Creating example config file...")
            _create_example_config(config_path)
            return

        # Load job configuration
        logger.info(f"Loading job configuration from: {config_path}")
        try:
            config = load_job_config(config_path)
            job_offer = create_job_offer_from_config(config)
            hr_feedback = create_hr_feedback_from_config(config, job_offer)
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            print(f"❌ Configuration error: {e}")
            return

        # Display job offer info
        print("=" * 80)
        print("JOB OFFER INFORMATION")
        print("=" * 80)
        print(f"📋 Position: {job_offer.title}")
        if job_offer.company:
            print(f"🏢 Company: {job_offer.company}")
        if job_offer.location:
            print(f"📍 Location: {job_offer.location}")
        if job_offer.description:
            print(f"\n📝 Job Description:\n{job_offer.description[:200]}...")
        print()

        # Initialize agents
        logger.info("Initializing agents...")
        cv_parser = CVParserAgent(
            model_name=settings.openai_model,
            vision_model_name=settings.azure_openai_vision_deployment,
            use_ocr=settings.use_ocr,
            temperature=settings.openai_temperature,
            api_key=settings.api_key,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )

        feedback_agent = FeedbackAgent(
            model_name=settings.openai_model,
            temperature=settings.openai_feedback_temperature,
            api_key=settings.api_key,
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )

        # Initialize services
        cv_service = CVService(cv_parser)
        feedback_service = FeedbackService(feedback_agent)

        # Process CV
        print("=" * 80)
        print("PROCESSING CV")
        print("=" * 80)
        print(f"📄 File: {pdf_path}")
        print(f"🔧 Verbose mode: {settings.verbose}")
        print(f"🤖 Model: {settings.openai_model}")
        print(f"👁️ Vision model (Azure deployment): {settings.azure_openai_vision_deployment}")
        print(f"🔍 OCR enabled: {settings.use_ocr}")
        print()

        try:
            logger.info("=" * 80)
            logger.info("STARTING CV PROCESSING")
            logger.info("=" * 80)
            cv_data = cv_service.process_cv_from_pdf(pdf_path, verbose=settings.verbose)

            # Display CV summary
            print("\n" + "=" * 80)
            print("CV SUMMARY")
            print("=" * 80)
            print(f"👤 Name: {cv_data.full_name}")
            print(f"📧 Email: {cv_data.email or 'N/A'}")
            print(f"📞 Phone: {cv_data.phone or 'N/A'}")
            print(f"📍 Location: {cv_data.location or 'N/A'}")
            print(f"🎓 Education: {len(cv_data.education)} entries")
            print(f"💼 Experience: {len(cv_data.experience)} positions")
            print(f"🛠️ Skills: {len(cv_data.skills)} skills")
            print(f"📜 Certifications: {len(cv_data.certifications)} certifications")

            # Generate feedback
            print("\n" + "=" * 80)
            print("GENERATING PERSONALIZED FEEDBACK")
            print("=" * 80)
            print(f"📋 Position: {job_offer.title}")
            print(f"✅ Decision: {hr_feedback.decision.value.upper()}")
            print()

            candidate_feedback, is_validated, _ = feedback_service.generate_feedback(
                cv_data,
                hr_feedback,
                job_offer=job_offer,
                output_format=FeedbackFormat.HTML,  # Default: HTML only
                save_to_file=True,
            )

            # Display HTML feedback info (save happens in generate_feedback when save_to_file=True)
            _ = feedback_service.get_feedback_html(candidate_feedback)
            html_filename = f"feedback_{cv_data.full_name.replace(' ', '_')}.html"

            print("=" * 80)
            print("PERSONALIZED FEEDBACK (HTML)")
            print("=" * 80)
            print(f"HTML feedback generated and saved to: {html_filename}")
            print("=" * 80)
            print(f"\n📧 HTML email version saved to: {html_filename}")
            print("   You can copy the HTML content and use it in your email client.")

            logger.info("CV processing completed successfully")
            print("\n✅ Processing completed successfully!")

        except CVProcessingError as e:
            logger.error(f"CV processing error: {e}")
            print(f"\n❌ Error processing CV: {e}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


def _create_example_config(config_path: str):
    """Create example configuration file."""
    config_file = Path(config_path)
    example_file = Path("config/job_config_example.json")

    if example_file.exists():
        import shutil

        config_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(example_file, config_file)
        print(f"✅ Created example config file: {config_path}")
        print("   Please edit it with your job offer and HR feedback details.")
    else:
        print("❌ Example config file not found. Please create one manually.")


if __name__ == "__main__":
    main()
