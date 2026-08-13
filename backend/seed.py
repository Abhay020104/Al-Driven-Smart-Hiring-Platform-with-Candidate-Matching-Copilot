"""
Database seeder — populates tables with initial mock data on first startup.
Idempotent: skips seeding if data already exists.
"""

from sqlalchemy.orm import Session

from backend.auth.security import hash_password
from backend.models.candidate import Candidate
from backend.models.role import Role
from backend.models.user import User


def seed_database(db: Session) -> None:
    """Populate the database with initial data if tables are empty."""

    # ── Default users ─────────────────────────────────────────────────────
    if db.query(User).count() == 0:
        users = [
            User(
                name="Admin User",
                email="admin@infosys.com",
                hashed_password=hash_password("admin123"),
                role="recruiter",
            ),
            User(
                name="Sarah Jenkins",
                email="recruiter@infosys.com",
                hashed_password=hash_password("recruiter123"),
                role="recruiter",
            ),
        ]
        db.add_all(users)
        db.commit()

    # ── Roles ─────────────────────────────────────────────────────────────
    if db.query(Role).count() == 0:
        roles = [
            Role(
                req_id="INF-AI-1042", role="Generative AI Engineer",
                business_unit="Infosys Topaz", location="Bengaluru",
                openings=18, applicants=264, screened=132, shortlisted=41,
                interview=19, offer=7, hired=3, days_open=24, target_days=35,
                risk="Medium", priority="High",
                required_skills="Python,LangChain,RAG,Azure AI,Vector DB,LLM,Prompt Engineering",
                experience_min=4, salary_band="₹18L – ₹28L",
            ),
            Role(
                req_id="INF-CLD-2217", role="Cloud Data Architect",
                business_unit="Digital Experience", location="Pune",
                openings=11, applicants=148, screened=92, shortlisted=26,
                interview=12, offer=4, hired=2, days_open=31, target_days=42,
                risk="Medium", priority="High",
                required_skills="Snowflake,Databricks,Azure,Data Modeling,Kafka,Lakehouse",
                experience_min=7, salary_band="₹22L – ₹35L",
            ),
            Role(
                req_id="INF-CYB-1905", role="Cybersecurity Consultant",
                business_unit="Cyber Next", location="Hyderabad",
                openings=9, applicants=116, screened=84, shortlisted=22,
                interview=11, offer=3, hired=1, days_open=38, target_days=40,
                risk="High", priority="Critical",
                required_skills="Zero Trust,IAM,SIEM,Cloud Security,SOC,ISO 27001",
                experience_min=5, salary_band="₹20L – ₹32L",
            ),
            Role(
                req_id="INF-SAP-3104", role="SAP SuccessFactors Lead",
                business_unit="Enterprise Apps", location="Chennai",
                openings=7, applicants=87, screened=59, shortlisted=18,
                interview=8, offer=2, hired=1, days_open=19, target_days=36,
                risk="Low", priority="Medium",
                required_skills="SuccessFactors,EC,RCM,LMS,Integration,SAP HCM",
                experience_min=8, salary_band="₹24L – ₹38L",
            ),
            Role(
                req_id="INF-QA-4120", role="QA Automation Specialist",
                business_unit="Quality Engineering", location="Mysuru",
                openings=14, applicants=203, screened=127, shortlisted=36,
                interview=15, offer=6, hired=4, days_open=16, target_days=30,
                risk="Low", priority="Medium",
                required_skills="Playwright,Selenium,API Testing,Java,TestNG,CI/CD",
                experience_min=3, salary_band="₹10L – ₹18L",
            ),
            Role(
                req_id="INF-HCM-5008", role="Talent Analytics Manager",
                business_unit="People Analytics", location="Gurugram",
                openings=5, applicants=73, screened=42, shortlisted=12,
                interview=6, offer=1, hired=0, days_open=44, target_days=38,
                risk="High", priority="Critical",
                required_skills="People Analytics,Power BI,SQL,Workforce Planning,Tableau,Python",
                experience_min=6, salary_band="₹18L – ₹28L",
            ),
        ]
        db.add_all(roles)
        db.commit()

    # ── Candidates ────────────────────────────────────────────────────────
    if db.query(Candidate).count() == 0:
        candidates = [
            Candidate(
                candidate="Aarav Mehta", role="Generative AI Engineer",
                location="Bengaluru", experience=6.5, match=94, skills_match=87,
                stage="Technical interview", availability="15 days",
                salary_fit="Aligned", risk="Low",
                skills="Python, LangChain, RAG, Azure AI, Vector DB",
                source="Referral", last_touch="Today",
                education="B.Tech CSE, IIT Bombay",
                certifications="Azure AI-102, Google ML",
                summary="6.5 years in ML/AI with strong GenAI focus. Led RAG pipeline for enterprise client.",
            ),
            Candidate(
                candidate="Nisha Kapoor", role="Generative AI Engineer",
                location="Hyderabad", experience=5.2, match=89, skills_match=97,
                stage="Manager interview", availability="30 days",
                salary_fit="Stretch", risk="Medium",
                skills="Python, LlamaIndex, MLOps, Prompting, AWS",
                source="LinkedIn", last_touch="Yesterday",
                education="M.Tech AI, BITS Pilani",
                certifications="AWS ML Specialty",
                summary="5.2 years in ML engineering. Strong in model deployment and LLM fine-tuning.",
            ),
            Candidate(
                candidate="Kabir Rao", role="Cloud Data Architect",
                location="Pune", experience=10.0, match=91, skills_match=88,
                stage="Offer discussion", availability="45 days",
                salary_fit="Aligned", risk="Low",
                skills="Snowflake, Databricks, Azure, Data Modeling",
                source="Agency", last_touch="Today",
                education="B.Tech IT, VIT",
                certifications="Azure Data Engineer, Snowflake SnowPro",
                summary="10 years in data engineering. Led lakehouse migrations for 3 Fortune 500 clients.",
            ),
            Candidate(
                candidate="Meera Sinha", role="Cloud Data Architect",
                location="Mumbai", experience=8.4, match=86, skills_match=84,
                stage="Technical interview", availability="30 days",
                salary_fit="Aligned", risk="Medium",
                skills="AWS, Glue, Redshift, Kafka, Lakehouse",
                source="Career site", last_touch="2 days ago",
                education="M.S. Data Science, IIIT Hyderabad",
                certifications="AWS Solutions Architect",
                summary="8.4 years in cloud data. Expert in event-driven architectures and real-time pipelines.",
            ),
            Candidate(
                candidate="Rohan Iyer", role="Cybersecurity Consultant",
                location="Hyderabad", experience=7.6, match=92, skills_match=100,
                stage="Technical interview", availability="Immediate",
                salary_fit="Aligned", risk="Low",
                skills="Zero Trust, IAM, SIEM, Cloud Security",
                source="Referral", last_touch="Today",
                education="B.Tech CSE, NIT Warangal",
                certifications="CISSP, CCSP",
                summary="7.6 years in cybersecurity. Designed Zero Trust architecture for banking sector.",
            ),
            Candidate(
                candidate="Fatima Khan", role="Cybersecurity Consultant",
                location="Noida", experience=6.1, match=84, skills_match=76,
                stage="Screening", availability="30 days",
                salary_fit="Stretch", risk="Medium",
                skills="SOC, Incident Response, ISO 27001, Splunk",
                source="Naukri", last_touch="Yesterday",
                education="B.E. IT, Delhi University",
                certifications="CEH, ISO 27001 Lead Auditor",
                summary="6.1 years in SOC operations. Led 24x7 SOC team for telecom client.",
            ),
            Candidate(
                candidate="Dev Menon", role="SAP SuccessFactors Lead",
                location="Chennai", experience=9.3, match=90, skills_match=89,
                stage="HR interview", availability="60 days",
                salary_fit="Aligned", risk="Medium",
                skills="SuccessFactors, EC, RCM, LMS, Integration",
                source="Alumni", last_touch="Today",
                education="MBA HR, XLRI Jamshedpur",
                certifications="SAP SuccessFactors EC, LMS",
                summary="9.3 years in SAP HR. Delivered global SuccessFactors rollout for 40,000-employee org.",
            ),
            Candidate(
                candidate="Isha Verma", role="QA Automation Specialist",
                location="Mysuru", experience=4.8, match=88, skills_match=75,
                stage="Manager interview", availability="15 days",
                salary_fit="Aligned", risk="Low",
                skills="Playwright, Selenium, API Testing, Java",
                source="Career site", last_touch="Today",
                education="B.E. CSE, Mysore University",
                certifications="ISTQB Advanced",
                summary="4.8 years in QA. Built end-to-end automation framework reducing regression time by 60%.",
            ),
            Candidate(
                candidate="Tanvi Nair", role="Talent Analytics Manager",
                location="Gurugram", experience=8.8, match=87, skills_match=80,
                stage="Technical interview", availability="30 days",
                salary_fit="Aligned", risk="Medium",
                skills="People Analytics, Power BI, SQL, Workforce Planning",
                source="LinkedIn", last_touch="Yesterday",
                education="MBA Analytics, ISB Hyderabad",
                certifications="Power BI Data Analyst",
                summary="8.8 years in HR analytics. Designed attrition prediction model saving ₹2Cr in retention costs.",
            ),
            Candidate(
                candidate="Arjun Das", role="Talent Analytics Manager",
                location="Bengaluru", experience=7.2, match=80, skills_match=84,
                stage="Screening", availability="45 days",
                salary_fit="Stretch", risk="High",
                skills="HR Metrics, Tableau, Python, Attrition Modeling",
                source="Naukri", last_touch="4 days ago",
                education="B.Tech + MBA, NMIMS",
                certifications="Tableau Desktop Specialist",
                summary="7.2 years in HR data. Specialises in workforce forecasting and headcount planning.",
            ),
        ]
        db.add_all(candidates)
        db.commit()


