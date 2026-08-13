"""
AI business logic — migrated from the inline functions in app.py.
All LLM calls are routed through services.llm.call_llama().
"""

import json
from datetime import date

from backend.models.candidate import Candidate as CandidateModel
from backend.models.role import Role as RoleModel
from backend.services.llm import call_llama

# ── Skill keywords used for local (non-LLM) resume parsing ───────────────────

_SKILL_KEYWORDS = [
    "Python", "Java", "C++", "JavaScript", "React", "Node.js", "SQL",
    "AWS", "Azure", "GCP", "Machine Learning", "AI", "Docker", "Kubernetes",
    "DevOps", "Agile", "Scrum", "Data Science", "Tableau", "PowerBI",
    "Communication", "Leadership", "LangChain", "RAG", "LLM",
    "Prompt Engineering", "Snowflake", "Databricks", "Kafka",
    "Zero Trust", "IAM", "SIEM", "Cloud Security", "Playwright", "Selenium",
]


# ── JD Analysis ───────────────────────────────────────────────────────────────

async def analyse_jd(jd_text: str) -> dict:
    prompt = f"""
You are an expert technical recruiter analyzing a job description.
Extract the following details from the job description text below and return ONLY a valid JSON object. Do not include markdown formatting or extra text outside the JSON.

Expected JSON schema:
{{
  "skills": ["skill1", "skill2"],
  "seniority": "Junior | Mid-level | Senior | Principal / Staff | Any level",
  "exp_years": 5,
  "flags": ["list", "of", "concerning", "phrases", "or", "red", "flags"],
  "salary": "estimated salary range string (e.g. '₹18L – ₹35L')",
  "tone_score": 85,
  "rewrite": "A well-written, inclusive, and professional rewrite of the job description in markdown format."
}}

Job Description Text:
{jd_text}
"""
    response = await call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        data = {
            "skills": ["Parse Error"],
            "seniority": "Unknown",
            "exp_years": 0,
            "flags": ["Could not parse LLM output"],
            "salary": "Unknown",
            "tone_score": 50,
            "rewrite": "Error analyzing JD with AI.",
        }

    data["word_count"] = len(jd_text.split())

    seniority = data.get("seniority", "Any level")
    color_map = {
        "Principal / Staff": "#7c3aed",
        "Senior": "#2563eb",
        "Mid-level": "#0f8b8d",
        "Junior": "#2a9d8f",
    }
    data["level_color"] = color_map.get(seniority, "#64748b")

    return {
        "skills": data.get("skills", []),
        "seniority": seniority,
        "level_color": data.get("level_color", "#64748b"),
        "exp_years": data.get("exp_years", 0),
        "flags": data.get("flags", []),
        "salary": data.get("salary", "Unknown"),
        "word_count": data.get("word_count", len(jd_text.split())),
        "tone_score": data.get("tone_score", 50),
        "rewrite": data.get("rewrite", "N/A"),
    }


# ── Resume Parsing (local keyword matching) ───────────────────────────────────

def parse_resume_text(text: str) -> dict:
    text_lower = text.lower()
    found_skills = [s for s in _SKILL_KEYWORDS if s.lower() in text_lower]

    exp_years = 0
    for part in text.split():
        p = part.strip(".,+'\"")
        if p.isascii() and p.isdigit():
            v = int(p)
            if 1 <= v <= 25:
                exp_years = max(exp_years, v)

    edu_map = {
        "phd": "PhD", "m.tech": "M.Tech", "mtech": "M.Tech", "m.s.": "M.S.",
        "mba": "MBA", "b.tech": "B.Tech", "btech": "B.Tech",
        "b.e.": "B.E.", "be ": "B.E.",
    }
    detected_edu = "Not specified"
    for key, val in edu_map.items():
        if key in text_lower:
            detected_edu = val
            break

    cert_keywords = [
        "aws", "azure", "gcp", "google", "cisco", "pmp",
        "cissp", "istqb", "safe", "scrum", "ceh",
    ]
    certs = [c.upper() for c in cert_keywords if c in text_lower]

    return {
        "skills": found_skills,
        "exp_years": exp_years,
        "education": detected_edu,
        "certifications": certs,
    }


# ── Resume Scoring vs Role ────────────────────────────────────────────────────

async def score_resume_vs_role(
    resume: dict,
    role_row: RoleModel,
    required_skills_override: list[str] | None = None,
) -> dict:
    required = (
        required_skills_override
        if required_skills_override
        else [s.strip() for s in role_row.required_skills.split(",")]
    )

    prompt = f"""
You are an expert technical recruiter matching a candidate's resume to a job role.
The job requires the following skills: {required}
The candidate has the following skills: {resume.get('skills', [])}

Return a JSON object containing two lists:
1. "matched_skills": A list of required skills the candidate clearly possesses (or close equivalents).
2. "missing_skills": A list of required skills the candidate is missing.

JSON Format:
{{
  "matched_skills": ["skillA", "skillB"],
  "missing_skills": ["skillC"]
}}
"""
    response = await call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
        matched = data.get("matched_skills", [])
        missing = data.get("missing_skills", required)
    except Exception:
        matched = [s for s in required if any(s.lower() in rs.lower() for rs in resume["skills"])]
        missing = [s for s in required if s not in matched]

    coverage = round(len(matched) / max(len(required), 1) * 100)
    exp_ok = resume["exp_years"] >= role_row.experience_min
    exp_bonus = 10 if resume["exp_years"] >= role_row.experience_min + 3 else (5 if exp_ok else -10)
    match_score = max(0, min(100, coverage + exp_bonus))

    if match_score >= 85:
        verdict, v_class = "Excellent fit", "recommend"
    elif match_score >= 70:
        verdict, v_class = "Good fit — minor gaps", "recommend"
    elif match_score >= 55:
        verdict, v_class = "Possible fit — train on gaps", "waitlist"
    else:
        verdict, v_class = "Significant gaps", "decline"

    return {
        "match_score": match_score,
        "coverage": coverage,
        "matched_skills": matched,
        "missing_skills": missing,
        "exp_ok": exp_ok,
        "verdict": verdict,
        "v_class": v_class,
    }


# ── Copilot Chat ──────────────────────────────────────────────────────────────

async def build_copilot_reply(
    prompt: str,
    context: str = "",
    user_role: str = "recruiter",
) -> str:
    system = f"""You are the AI-Driven Smart Hiring Platform Copilot — a STRICTLY scoped AI assistant.

ALLOWED TOPICS (you may ONLY answer questions about these):
- Recruitment: candidates, job roles, job descriptions, interviews, hiring pipelines, resume screening, skill matching.
- HR Operations: reports, communications, emails, offer letters, JD analysis.
- Dashboard Features: how to use the Overview, Find Candidates, JD Analyser, Resume AI, Interviews, Recruitment Insights, Communications, Reports, or Chat with AI pages.

Current user role: {user_role}
{context}

STRICT RULES:
1. If a question is NOT related to recruitment, HR, or this project's features, you MUST refuse to answer.
2. For any off-topic question, respond ONLY with:
   "I'm sorry, I can only assist with recruitment, and HR-related queries within this platform."
3. Do NOT attempt to answer off-topic questions even partially.
4. For on-topic questions, answer concisely and professionally.
"""
    return await call_llama(prompt, system=system)


# ── Email Generation ──────────────────────────────────────────────────────────

async def generate_email(
    template_key: str,
    candidate: CandidateModel,
) -> tuple[str, str]:
    prompt = f"""
You are an AI assistant helping a recruiter write an email.
The email type is: {template_key}

Candidate details:
- Name: {candidate.candidate}
- Role Applied: {candidate.role}
- Skills: {candidate.skills}
- Current Stage: {candidate.stage}

Return ONLY a valid JSON object with EXACTLY two keys: "subject" and "body".
Do NOT include markdown formatting outside the JSON, no backticks, no explanations.
The body MUST use paragraphs and strictly follow a professional business template format.
"""
    response = await call_llama(prompt, expect_json=True)
    try:
        data = json.loads(response)
        subject = data.get("subject", f"Update regarding your application for {candidate.role}")
        body = data.get("body", "Failed to generate email content.")
    except Exception:
        subject = f"Update regarding your application for {candidate.role}"
        body = "An error occurred generating the email. Please try again."

    return subject, body


# ── Hiring Recommendation ─────────────────────────────────────────────────────

async def build_hiring_recommendation(
    candidate: CandidateModel,
) -> tuple[str, str, str]:
    score = candidate.match
    risk = candidate.risk
    sal = candidate.salary_fit
    avail = candidate.availability
    name = candidate.candidate

    prompt = f"""
You are a senior recruitment manager.
Write a 2-sentence hiring recommendation for {name}.
Context:
- Match score: {score}%
- Retention risk: {risk}
- Salary expectations: {sal}
- Availability: {avail}

Be decisive. If score >= 85 and risk is Low, recommend strongly. If score < 80, advise waiting or rejecting.
Return ONLY the reasoning text. No JSON, no markdown.
"""
    reason = await call_llama(prompt)

    if score >= 90 and risk == "Low" and sal == "Aligned":
        verdict, css = "✅ Strongly Recommend", "recommend"
    elif score >= 85 and risk in ["Low", "Medium"]:
        verdict, css = "👍 Recommend", "recommend"
    elif score >= 80:
        verdict, css = "⏳ Waitlist", "waitlist"
    else:
        verdict, css = "❌ Do Not Proceed", "decline"

    return verdict, css, reason


# ── Report Generation ─────────────────────────────────────────────────────────

async def generate_report(
    report_type: str,
    roles_data: dict,
    period_label: str,
) -> tuple[str, str]:
    today_str = date.today().strftime("%d %B %Y")

    total_app = roles_data.get("total_applicants", 0)
    total_hire = roles_data.get("total_hired", 0)
    avg_match = roles_data.get("avg_match", 0)
    selected_roles = roles_data.get("selected_roles", [])

    system = "You are an expert HR Data Analyst generating a recruitment report."
    prompt = f"""
Generate a professional {report_type} in Markdown format.

Context data:
- Date Generated: {today_str}
- Period: {period_label}
- Roles included: {', '.join(selected_roles) if selected_roles else 'All Roles'}
- Total Applications: {total_app}
- Total Hires: {total_hire}
- Average Candidate Match Score: {avg_match}%

You MUST follow this STRICT markdown structure containing exactly 5 headings. Use clean pointers/bullet points instead of long paragraphs.
CRITICAL: Do NOT use any code blocks, triple backticks, or indented blocks.

# 1. Executive Summary
- [Bullet point summary of the overall health of the recruitment pipeline]

# 2. Key Metrics Analysis
- [Brief pointers on metrics and conversion rates]

# 3. Sourcing Channel Performance
- [Pointers on which sourcing channels are performing best vs worst]

# 4. Bottlenecks Analysis
- [Identify 3-4 specific bottlenecks in the current process]

# 5. Strategic Recommendations
- [Provide 3-4 highly actionable recommendations]
"""
    content = await call_llama(prompt, system=system)
    return report_type, content


# ── AI Interview Generator ────────────────────────────────────────────────────

async def generate_interview_questions(
    role_name: str, 
    skills: str, 
    num_questions: int, 
    difficulty: str, 
    focus_area: str
) -> list[str]:
    system = "You are an expert technical interviewer."
    prompt = f"""
Generate EXACTLY {num_questions} interview questions for a {role_name}.
The candidate has the following skills/experience context: {skills}

- Difficulty level: {difficulty}
- Focus Area: {focus_area}

Output ONLY a JSON array of strings containing the questions. Do not include introductory text or markdown wrappers outside the JSON array.
Format:
[
  "Question 1?",
  "Question 2?"
]
"""
    response = await call_llama(prompt, expect_json=True, system=system)
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "questions" in data:
            return data["questions"]
    except Exception:
        pass
    
    # Fallback if json parsing fails
    return [
        f"Can you describe your experience with {skills}?",
        f"What is the most complex problem you solved as a {role_name}?",
        "How do you ensure quality in your work?"
    ]

async def evaluate_interview_answers(
    questions: list[str], 
    answers: list[str], 
    role_name: str, 
    skills: str
) -> dict:
    system = "You are an expert technical interviewer evaluating a candidate's test."
    
    qa_pairs = ""
    for i, (q, a) in enumerate(zip(questions, answers)):
        qa_pairs += f"Question {i+1}: {q}\nCandidate Answer: {a}\n\n"
        
    prompt = f"""
Evaluate the following candidate answers for a {role_name} position.
Role Context / Expected Skills: {skills}

{qa_pairs}

CRITICAL INSTRUCTIONS FOR SCORING:
- Be EXTREMELY STRICT with scoring.
- If an answer is gibberish, irrelevant, nonsensical, or clearly shows a lack of understanding, you MUST give a score of 0 for that question.
- Do NOT give partial credit (like 4/10 or 40%) for merely typing words or attempting to answer if the content is incorrect or gibberish.
- The `overall_score` MUST be 0 if all answers are gibberish or irrelevant.
- Only award points for technically accurate, relevant, and well-reasoned answers.

Analyze the answers and return ONLY a valid JSON object (no markdown, no backticks).
Expected JSON format:
{{
  "evaluations": [
    {{
      "question": "The question text",
      "score": 8,
      "feedback": "Feedback on the candidate's answer"
    }}
  ],
  "overall_score": 85,
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1"],
  "recommendation": "Strongly Recommend / Recommend / Consider / Do Not Recommend"
}}
"""
    response = await call_llama(prompt, expect_json=True, system=system)
    try:
        data = json.loads(response)
        return data
    except Exception:
        return {
            "evaluations": [],
            "overall_score": 0,
            "strengths": ["Failed to generate report"],
            "weaknesses": ["Failed to generate report"],
            "recommendation": "Error"
        }

