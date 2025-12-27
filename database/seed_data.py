"""Seed database with example data."""
from pathlib import Path
import sys
from pathlib import Path as PathLib

# Add parent directory to path
sys.path.insert(0, str(PathLib(__file__).parent.parent))

from database.models import (
    init_db, create_position, create_candidate,
    CandidateStatus, RecruitmentStage, get_all_positions, get_all_candidates,
    clear_database
)
from config.job_config import load_job_config, create_job_offer_from_config
from core.logger import logger


def seed_database(reset: bool = False):
    """Seed database with example positions and candidates."""
    # Initialize database
    init_db()

    if reset:
        logger.info("Reset flag detected: clearing database tables (without dropping)...")
        clear_database(reset_autoincrement=True)
    
    logger.info("Seeding database with example data...")
    
    # Try to import position from job_config_example.yaml first
    try:
        config_path = Path('config/job_config_example.yaml')
        if config_path.exists():
            config = load_job_config(str(config_path))
            job_offer = create_job_offer_from_config(config)
            
            # Check if position already exists
            existing_positions = get_all_positions()
            position_exists = any(
                pos.title == job_offer.title and pos.company == job_offer.company 
                for pos in existing_positions
            )
            
            if not position_exists:
                logger.info(f"Importing position from config: {job_offer.title} at {job_offer.company}")
                create_position(
                    title=job_offer.title,
                    company=job_offer.company,
                    description=job_offer.description
                )
    except Exception as e:
        logger.warning(f"Could not import position from config: {str(e)}")
    
    # Check if we should skip seeding (only if positions and candidates exist)
    existing_positions = get_all_positions()
    existing_candidates = get_all_candidates()
    
    if existing_positions and existing_candidates:
        logger.info("Database already contains data. Skipping additional seed.")
        return
    
    # Create example positions (various industries)
    positions = [
        {
            'title': 'Senior DevOps Engineer',
            'company': 'TechCorp Inc.',
            'description': '''We are looking for an experienced DevOps Engineer to join our team.
You will be responsible for designing, implementing, and maintaining our cloud infrastructure, CI/CD pipelines, and automation systems.

Required Qualifications:
- 5+ years of experience in DevOps/Cloud Engineering
- Strong knowledge of AWS and/or Azure
- Experience with Infrastructure as Code (Terraform, CloudFormation)
- Proficiency in Python or Bash scripting
- Experience with CI/CD tools (GitLab CI, GitHub Actions, Jenkins)
- Knowledge of Kubernetes and containerization
- Strong problem-solving and communication skills

Nice to Have:
- Experience with MLOps
- Knowledge of monitoring tools (Prometheus, Grafana)
- Certifications (AWS, Azure, Kubernetes)
- Experience with Ansible
- Knowledge of security best practices

Benefits:
- Remote work
- Flexible working hours
- Private health insurance
- Learning budget
- Stock options'''
        },
        {
            'title': 'Marketing Manager',
            'company': 'Creative Solutions Sp. z o.o.',
            'description': '''We are seeking a dynamic Marketing Manager to lead our marketing team and drive brand awareness.

Key Responsibilities:
- Develop and execute comprehensive marketing strategies
- Manage marketing campaigns across digital and traditional channels
- Analyze market trends and competitor activities
- Oversee social media presence and content creation
- Collaborate with sales team to generate leads
- Manage marketing budget and ROI tracking

Requirements:
- Bachelor's degree in Marketing, Business, or related field
- 5+ years of marketing experience
- Strong analytical and creative thinking skills
- Experience with digital marketing tools (Google Analytics, Facebook Ads, etc.)
- Excellent communication and leadership skills
- Fluent in Polish and English

What We Offer:
- Competitive salary
- Professional development opportunities
- Modern office in city center
- Flexible working arrangements'''
        },
        {
            'title': 'Financial Analyst',
            'company': 'Global Finance Group',
            'description': '''Join our finance team as a Financial Analyst and help drive strategic business decisions.

Your Role:
- Prepare financial reports and forecasts
- Analyze financial data and market trends
- Support budgeting and planning processes
- Conduct variance analysis and identify opportunities
- Assist in investment analysis and due diligence
- Collaborate with cross-functional teams

Qualifications:
- Bachelor's degree in Finance, Accounting, or Economics
- 3+ years of financial analysis experience
- Strong Excel and financial modeling skills
- Knowledge of financial software (SAP, Oracle, etc.)
- Attention to detail and analytical mindset
- Professional certifications (CFA, CPA) preferred

Benefits:
- Attractive compensation package
- Health and dental insurance
- Retirement savings plan
- Training and certification support'''
        },
        {
            'title': 'UX/UI Designer',
            'company': 'Digital Innovations',
            'description': '''We're looking for a talented UX/UI Designer to create beautiful and intuitive user experiences.

What You'll Do:
- Design user interfaces for web and mobile applications
- Create wireframes, prototypes, and high-fidelity designs
- Conduct user research and usability testing
- Collaborate with product managers and developers
- Maintain design systems and style guides
- Stay up-to-date with design trends and best practices

Requirements:
- Portfolio demonstrating strong design skills
- 3+ years of UX/UI design experience
- Proficiency in design tools (Figma, Sketch, Adobe XD)
- Understanding of user-centered design principles
- Knowledge of HTML/CSS basics
- Excellent communication and collaboration skills

Perks:
- Creative and collaborative work environment
- Latest design tools and equipment
- Flexible schedule
- Remote work options
- Annual design conference attendance'''
        },
        {
            'title': 'Sales Representative',
            'company': 'Business Partners Ltd.',
            'description': '''Join our sales team and help grow our business by building relationships with clients.

Responsibilities:
- Identify and pursue new business opportunities
- Build and maintain client relationships
- Present products and services to potential customers
- Negotiate contracts and close deals
- Meet and exceed sales targets
- Provide excellent customer service

What We're Looking For:
- Proven sales experience (2+ years)
- Strong communication and negotiation skills
- Self-motivated and results-oriented
- Ability to work independently and in a team
- Valid driver's license
- Bachelor's degree preferred but not required

Compensation:
- Base salary + commission
- Performance bonuses
- Company car
- Health insurance
- Unlimited earning potential'''
        }
    ]
    
    created_positions = []
    for pos_data in positions:
        position = create_position(**pos_data)
        created_positions.append(position)
        logger.info(f"Created position: {position.title} at {position.company}")
    
    # Create example candidates
    candidates_data = [
        {
            'first_name': 'Anna',
            'last_name': 'Kowalska',
            'email': 'anna.kowalska@example.com',
            'position_id': created_positions[0].id,  # DevOps Engineer
            'status': CandidateStatus.IN_PROGRESS,
            'stage': RecruitmentStage.TECHNICAL_ASSESSMENT,
            'cv_path': None
        },
        {
            'first_name': 'Jan',
            'last_name': 'Nowak',
            'email': 'jan.nowak@example.com',
            'position_id': created_positions[0].id,  # DevOps Engineer
            'status': CandidateStatus.ACCEPTED,
            'stage': RecruitmentStage.OFFER,
            'cv_path': None
        },
        {
            'first_name': 'Maria',
            'last_name': 'Wiśniewska',
            'email': 'maria.wisniewska@example.com',
            'position_id': created_positions[1].id,  # Marketing Manager
            'status': CandidateStatus.IN_PROGRESS,
            'stage': RecruitmentStage.HR_INTERVIEW,
            'cv_path': None
        },
        {
            'first_name': 'Piotr',
            'last_name': 'Zieliński',
            'email': 'piotr.zielinski@example.com',
            'position_id': created_positions[2].id,  # Financial Analyst
            'status': CandidateStatus.REJECTED,
            'stage': RecruitmentStage.INITIAL_SCREENING,
            'cv_path': None
        },
        {
            'first_name': 'Katarzyna',
            'last_name': 'Szymańska',
            'email': 'katarzyna.szymanska@example.com',
            'position_id': created_positions[3].id,  # UX/UI Designer
            'status': CandidateStatus.IN_PROGRESS,
            'stage': RecruitmentStage.FINAL_INTERVIEW,
            'cv_path': None
        },
        {
            'first_name': 'Tomasz',
            'last_name': 'Wójcik',
            'email': 'tomasz.wojcik@example.com',
            'position_id': created_positions[4].id,  # Sales Representative
            'status': CandidateStatus.IN_PROGRESS,
            'stage': RecruitmentStage.INITIAL_SCREENING,
            'cv_path': None
        },
        {
            'first_name': 'Magdalena',
            'last_name': 'Kaczmarek',
            'email': 'magdalena.kaczmarek@example.com',
            'position_id': created_positions[1].id,  # Marketing Manager
            'status': CandidateStatus.IN_PROGRESS,
            'stage': RecruitmentStage.TECHNICAL_ASSESSMENT,
            'cv_path': None
        },
        {
            'first_name': 'Michał',
            'last_name': 'Mazur',
            'email': 'michal.mazur@example.com',
            'position_id': created_positions[0].id,  # DevOps Engineer
            'status': CandidateStatus.REJECTED,
            'stage': RecruitmentStage.INITIAL_SCREENING,
            'cv_path': None
        }
    ]
    
    for cand_data in candidates_data:
        candidate = create_candidate(**cand_data)
        logger.info(f"Created candidate: {candidate.full_name}")
    
    logger.info("Database seeding completed!")


if __name__ == '__main__':
    reset = "--reset" in sys.argv
    seed_database(reset=reset)

