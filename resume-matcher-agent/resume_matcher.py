"""
RESUME / JOB DESCRIPTION MATCHER AGENT
==========================================
Fully local logic + one LLM call — no external data APIs, so nothing
here depends on a third-party service being up. Reuses LangChain
concepts from langchain_fundamentals.py: prompt templates + structured
output parsing.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

llm = ChatGoogleGenerativeAI(model="gemini-flash-latest")


# ---------------------------------------------------------------------
# Define the exact structure we want back — this is what makes the
# output usable in code (e.g. to render a progress bar, a bullet list)
# instead of just a wall of text.
# ---------------------------------------------------------------------
class MatchAnalysis(BaseModel):
    match_score: int = Field(description="Overall fit score from 0 to 100")
    matched_skills: List[str] = Field(
        description="Skills/requirements from the JD that the resume clearly demonstrates"
    )
    missing_skills: List[str] = Field(
        description="Skills/requirements from the JD NOT evident in the resume"
    )
    suggested_resume_tweaks: List[str] = Field(
        description="3-5 specific, actionable suggestions to improve fit — e.g. rewording a bullet, adding a keyword, reframing an experience"
    )
    overall_verdict: str = Field(
        description="One or two sentence honest verdict on how strong a candidate this is for this role, as-is"
    )


match_prompt = ChatPromptTemplate.from_template(
    """You are an experienced technical recruiter evaluating fit between a candidate's resume and a job description.

Be specific and honest — do not inflate the score to be encouraging. Base matched_skills and missing_skills
on what is ACTUALLY written in the resume, not what the candidate might plausibly know.

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

Respond ONLY as JSON matching this schema:
{{
  "match_score": int,
  "matched_skills": [str, ...],
  "missing_skills": [str, ...],
  "suggested_resume_tweaks": [str, ...],
  "overall_verdict": str
}}"""
)

match_chain = match_prompt | llm | JsonOutputParser(pydantic_object=MatchAnalysis)


def analyze_match(job_description: str, resume_text: str) -> dict:
    return match_chain.invoke(
        {
            "job_description": job_description,
            "resume_text": resume_text,
        }
    )


if __name__ == "__main__":
    sample_jd = """
    Senior Consultant, AI Solutions — EY-Parthenon
    Requirements: Experience with GenAI, LLMs, RAG, prompt engineering, AI platform
    evaluation. Ability to translate business challenges into AI use cases. Bachelor's
    or Master's in Computer Science, Data Science, or related technical field.
    """

    sample_resume = """
    Senior Consultant with 8 years in Dynamics 365 and Power Platform.
    Built AI agents using Python, LangGraph, RAG, and Gemini/Anthropic APIs.
    Led design of an Agentic AI Copilot Studio solution for a UK insurance client.
    """

    print("=== Resume/JD Match Analysis ===\n")
    result = analyze_match(sample_jd, sample_resume)

    print(f"Match Score: {result['match_score']}/100\n")
    print("Matched Skills:")
    for skill in result["matched_skills"]:
        print(f"  ✓ {skill}")
    print("\nMissing Skills:")
    for skill in result["missing_skills"]:
        print(f"  ✗ {skill}")
    print("\nSuggested Tweaks:")
    for tweak in result["suggested_resume_tweaks"]:
        print(f"  → {tweak}")
    print(f"\nVerdict: {result['overall_verdict']}")
