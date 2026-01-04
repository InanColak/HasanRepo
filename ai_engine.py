"""
AI Engine module for Quiz Application.
Handles OpenAI API integration for generating pedagogical reports.
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_openai_client() -> Optional[OpenAI]:
    """Initialize and return OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_pedagogical_report(aggregated_results: Dict[str, Any]) -> str:
    """
    Generate a pedagogical report based on aggregated quiz results.

    Args:
        aggregated_results: Dictionary containing:
            - session_id: The session identifier
            - topic: Main topic (e.g., "Business Plan")
            - subtopic: Subtopic (e.g., "Fundamental Components")
            - participant_count: Number of students
            - overall_success_rate: Overall percentage of correct answers
            - skill_breakdown: List of skill statistics

    Returns:
        A pedagogical report string with recommendations.
    """
    client = get_openai_client()

    if not client:
        return generate_fallback_report(aggregated_results)

    # Prepare the prompt
    skill_summary = "\n".join([
        f"- {skill['skill_tag']}: {skill['success_rate']}% success rate "
        f"({skill['correct_answers']}/{skill['total_answers']} correct)"
        for skill in aggregated_results.get("skill_breakdown", [])
    ])

    prompt = f"""You are an educational consultant analyzing quiz results for a class.
Based on the following data, provide a brief pedagogical report with actionable recommendations.

Topic: {aggregated_results.get('topic', 'Unknown')}
Subtopic: {aggregated_results.get('subtopic', 'Unknown')}
Number of Participants: {aggregated_results.get('participant_count', 0)}
Overall Success Rate: {aggregated_results.get('overall_success_rate', 0)}%

Performance by Skill Area:
{skill_summary}

Please provide:
1. A brief summary of class performance (2-3 sentences)
2. Identify which skill areas need the most attention
3. Provide 2-3 specific teaching recommendations for the next lesson
4. Suggest any additional resources or activities that could help

Keep the response concise and actionable for a teacher to use immediately.
Format the response in a clear, professional manner."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful educational consultant who provides actionable insights for teachers."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating AI report: {str(e)}\n\n{generate_fallback_report(aggregated_results)}"


def generate_fallback_report(aggregated_results: Dict[str, Any]) -> str:
    """
    Generate a basic report when OpenAI API is not available.

    Args:
        aggregated_results: Dictionary containing quiz results data.

    Returns:
        A basic report string with analysis.
    """
    skill_breakdown = aggregated_results.get("skill_breakdown", [])

    # Find weakest and strongest areas
    if not skill_breakdown:
        return "No data available for analysis. Please wait for students to complete the quiz."

    sorted_skills = sorted(skill_breakdown, key=lambda x: x.get("success_rate", 0))
    weakest = sorted_skills[0] if sorted_skills else None
    strongest = sorted_skills[-1] if sorted_skills else None

    report = f"""
📊 **Quiz Performance Report**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Topic:** {aggregated_results.get('topic', 'Unknown')}
**Subtopic:** {aggregated_results.get('subtopic', 'Unknown')}
**Participants:** {aggregated_results.get('participant_count', 0)} students
**Overall Success Rate:** {aggregated_results.get('overall_success_rate', 0)}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Performance by Skill Area:**
"""

    for skill in skill_breakdown:
        rate = skill.get("success_rate", 0)
        if rate >= 80:
            indicator = "🟢"
        elif rate >= 60:
            indicator = "🟡"
        else:
            indicator = "🔴"
        report += f"\n{indicator} **{skill['skill_tag']}**: {rate}%"

    report += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n**Recommendations:**\n"

    if weakest and weakest.get("success_rate", 100) < 70:
        report += f"\n⚠️ **Focus Area:** The class struggles with '{weakest['skill_tag']}' "
        report += f"(only {weakest['success_rate']}% success rate). "
        report += "Consider dedicating more time to this topic in the next lesson."

    if strongest and strongest.get("success_rate", 0) >= 80:
        report += f"\n\n✅ **Strength:** Students perform well in '{strongest['skill_tag']}' "
        report += f"({strongest['success_rate']}% success rate)."

    overall_rate = aggregated_results.get("overall_success_rate", 0)
    if overall_rate < 60:
        report += "\n\n📝 **General Note:** Overall performance suggests a review session "
        report += "might be beneficial before moving to new material."
    elif overall_rate >= 80:
        report += "\n\n🎯 **General Note:** Excellent overall performance! "
        report += "The class is ready to advance to more complex topics."

    report += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    report += "\n*Note: For more detailed AI-powered insights, please configure your OpenAI API key.*"

    return report


def analyze_individual_performance(student_results: Dict[str, Any]) -> str:
    """
    Generate individual student performance analysis.

    Args:
        student_results: Dictionary containing individual student results.

    Returns:
        A brief analysis string.
    """
    correct = student_results.get("correct", 0)
    total = student_results.get("total", 0)

    if total == 0:
        return "No answers recorded."

    percentage = (correct / total) * 100

    if percentage >= 80:
        return f"Excellent! You scored {correct}/{total} ({percentage:.0f}%). Keep up the great work!"
    elif percentage >= 60:
        return f"Good job! You scored {correct}/{total} ({percentage:.0f}%). Review the areas you missed."
    else:
        return f"You scored {correct}/{total} ({percentage:.0f}%). Consider reviewing the material again."
