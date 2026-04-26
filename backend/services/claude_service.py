import os
import json

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def get_ai_response(system: str, prompt: str, max_tokens: int = 2000) -> str:
    """Single function to call AI - uses Gemini if available, else Anthropic"""
    if GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system
        )
        response = model.generate_content(prompt)
        return response.text
    elif ANTHROPIC_API_KEY:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    else:
        raise Exception("No AI API key configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY.")


def extract_text_from_file(file_path: str, filename: str) -> str:
    """Extract text from any file type"""
    fn = filename.lower()
    try:
        if fn.endswith('.pdf'):
            import fitz
            doc = fitz.open(file_path)
            text = "".join(page.get_text() for page in doc)
            doc.close()
            return text[:150000]
        elif fn.endswith('.docx'):
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return text[:150000]
        elif fn.endswith(('.txt', '.md', '.r', '.R', '.py', '.csv', '.rmd',
                          '.Rmd', '.qmd', '.tex', '.html', '.sh', '.json',
                          '.xml', '.log')):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:150000]
        else:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()[:150000]
                if len(content.strip()) > 50:
                    return content
            except:
                pass
            try:
                import fitz
                doc = fitz.open(file_path)
                text = "".join(page.get_text() for page in doc)
                doc.close()
                if text.strip():
                    return text[:150000]
            except:
                pass
            return f"[File: {filename} — text extraction not available for this format]"
    except Exception as e:
        return f"Could not extract text from {filename}: {str(e)}"


def extract_text_from_pdf(file_path: str) -> str:
    return extract_text_from_file(file_path, file_path)


def chat_with_paper(paper_text: str, messages: list, user_question: str, paper_title: str = "") -> str:
    system = f"""You are ScholarMind, an expert academic AI assistant.
You are helping a researcher or professor analyze and understand an academic paper or document.

Paper title: {paper_title}

FULL DOCUMENT CONTENT:
{paper_text[:100000]}

Your role:
- Answer questions about this specific document with precision
- Explain statistical methods, study designs, and findings clearly
- Identify methodological strengths and weaknesses
- Be direct and academically rigorous
- Always ground your answers in the actual document content above"""

    history_text = ""
    for m in messages[-6:]:
        role = "User" if m["role"] == "user" else "Assistant"
        history_text += f"{role}: {m['content']}\n\n"

    prompt = f"{history_text}User: {user_question}"
    return get_ai_response(system, prompt, max_tokens=1500)


def analyze_paper_for_review(paper_text: str, supp_text: str, paper_type: str, journal: str = "") -> dict:
    system = """You are ScholarMind, an expert academic peer reviewer.
You have deep expertise in biomedical research, statistics, epidemiology, genetics, and scientific methodology.
You produce rigorous, constructive, and balanced peer reviews."""

    prompt = f"""Carefully analyze this manuscript and produce a comprehensive peer review.

Paper type: {paper_type}
Journal: {journal}

MAIN DOCUMENT:
{paper_text[:80000]}

SUPPLEMENTARY MATERIAL:
{supp_text[:20000] if supp_text else "None provided"}

Produce a JSON response with EXACTLY this structure (no extra text, just JSON):
{{
  "summary": "2-3 paragraph summary of what the paper does, its main findings, and overall assessment",
  "major_concerns": "Numbered list of major concerns that must be addressed. Be specific.",
  "minor_concerns": "Numbered list of minor issues",
  "strengths": "What the paper does well",
  "statistical_issues": "Specific statistical problems found, or None identified",
  "recommendation": "Accept|Minor Revision|Major Revision|Reject",
  "score_novelty": 7.5,
  "score_methodology": 6.0,
  "score_clarity": 8.0,
  "score_statistics": 5.5,
  "checklist": [
    {{"item": "Clear research question", "status": "pass", "note": ""}},
    {{"item": "Appropriate study design", "status": "pass", "note": ""}},
    {{"item": "Adequate sample size / power", "status": "warn", "note": "No power calculation provided"}},
    {{"item": "Multiple testing correction", "status": "fail", "note": "No FDR correction for secondary outcomes"}},
    {{"item": "Reproducible methods", "status": "pass", "note": ""}},
    {{"item": "Appropriate statistical tests", "status": "warn", "note": ""}},
    {{"item": "Conclusions match results", "status": "pass", "note": ""}},
    {{"item": "Conflict of interest declared", "status": "pass", "note": ""}},
    {{"item": "Data availability statement", "status": "warn", "note": ""}},
    {{"item": "Ethics approval stated", "status": "pass", "note": ""}}
  ],
  "suggested_additional_analyses": "List of analyses that would strengthen the paper"
}}"""

    text = get_ai_response(system, prompt, max_tokens=4000)
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except:
        return {
            "summary": text[:800] if text else "Analysis complete",
            "major_concerns": "See summary above",
            "minor_concerns": "",
            "strengths": "",
            "statistical_issues": "",
            "recommendation": "Major Revision",
            "score_novelty": 7.0,
            "score_methodology": 7.0,
            "score_clarity": 7.0,
            "score_statistics": 7.0,
            "checklist": [],
            "suggested_additional_analyses": ""
        }


def generate_grant_section(section: str, research_profile: str, grant_info: dict, existing_content: str = "") -> str:
    system = """You are ScholarMind, an expert academic grant writing assistant.
You have helped researchers win millions in funding from CIHR, NSERC, NIH, and other agencies.
You write compelling, specific, scientifically rigorous grant content."""

    prompt = f"""Write the '{section}' section for this grant application.

Grant details:
- Agency: {grant_info.get('agency', '')}
- Program: {grant_info.get('program', '')}
- Title: {grant_info.get('title', '')}

Researcher profile:
{research_profile}

{f"Existing draft to improve: {existing_content}" if existing_content else "Write a strong first draft."}

Write a compelling, specific, well-structured {section} section.
Use strong action verbs. Be specific about methods and impact.
Tailor language to {grant_info.get('agency', 'the funding agency')} priorities."""

    return get_ai_response(system, prompt, max_tokens=2000)


def generate_student_followup(student: dict, supervisor_name: str) -> str:
    system = "You are an academic writing assistant helping professors communicate with their students."
    prompt = f"""Write a brief, warm but professional follow-up email from Prof. {supervisor_name} to their student.

Student: {student['name']}
Program: {student['program']} Year {student['year']}
Thesis: {student.get('thesis_title', 'not specified')}
Last meeting: {student.get('last_meeting', 'unknown')}
Progress: {student.get('progress_percent', 0)}%
Notes: {student.get('notes', '')}

Write a 3-4 sentence email checking in on progress, asking about blockers, and suggesting next steps.
Be warm, encouraging, and specific."""

    return get_ai_response(system, prompt, max_tokens=300)


def get_grant_opportunities(research_profile: str) -> list:
    system = "You are an expert in academic research funding and grant opportunities."
    prompt = f"""Based on this researcher's profile, suggest 6 realistic grant opportunities.

Profile: {research_profile}

Return ONLY a JSON array with no extra text:
[
  {{
    "title": "Grant program name",
    "agency": "CIHR/NSERC/NIH/etc",
    "program": "Specific program name",
    "deadline": "2026-09-15",
    "amount": "$250,000/year for 5 years",
    "relevance": "Why this matches their research",
    "url": "https://example.com"
  }}
]

Include realistic Canadian (CIHR, NSERC, FRQS) and international (NIH, Wellcome) opportunities."""

    text = get_ai_response(system, prompt, max_tokens=2000)
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        return json.loads(text[start:end])
    except:
        return []
