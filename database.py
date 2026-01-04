"""
Database module for Quiz Application.
Handles all SQLite database operations including sessions, questions, and results.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database file path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "quiz.db")


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database() -> None:
    """Initialize the database with required tables and seed data."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with get_connection() as conn:
        cursor = conn.cursor()

        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id TEXT NOT NULL,
                topic TEXT NOT NULL,
                subtopic TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Create questions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                skill_tag TEXT NOT NULL,
                topic TEXT NOT NULL,
                options TEXT NOT NULL
            )
        """)

        # Create results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                student_id TEXT NOT NULL,
                question_id INTEGER NOT NULL,
                selected_answer TEXT,
                is_correct INTEGER NOT NULL,
                answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
        """)

        # Create users table for simple authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'teacher'
            )
        """)

        conn.commit()

        # Seed default teacher if not exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'teacher'")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                ("teacher", "demo123", "teacher")
            )
            conn.commit()

        # Seed Business Plan questions if not exists
        cursor.execute("SELECT COUNT(*) FROM questions WHERE topic = 'Business Plan'")
        if cursor.fetchone()[0] == 0:
            seed_business_plan_questions()


def seed_business_plan_questions() -> None:
    """Seed the database with 5 Business Plan questions (German)."""
    questions = [
        {
            "question_text": "Womit beginnt eine Geschäftsidee im Kern?",
            "correct_answer": "C",
            "skill_tag": "Geschäftsidee",
            "topic": "Business Plan",
            "options": "A) Mit einem schönen Produkt|B) Mit einer hohen Gewinnerwartung|C) Mit einem Kundenproblem|D) Mit Werbung"
        },
        {
            "question_text": "Was bedeutet \"Value Proposition\"?",
            "correct_answer": "B",
            "skill_tag": "Value Proposition",
            "topic": "Business Plan",
            "options": "A) Das Logo des Unternehmens|B) Der zentrale Nutzen für den Kunden|C) Die Kostenstruktur des Unternehmens|D) Die Wettbewerber"
        },
        {
            "question_text": "Wozu dient das Business Model Canvas?",
            "correct_answer": "B",
            "skill_tag": "Business Model Canvas",
            "topic": "Business Plan",
            "options": "A) Zur Berechnung von Steuern|B) Zur strukturierten und visuellen Darstellung des Geschäftsmodells|C) Zur Produktgestaltung|D) Zur Erstellung eines Vertrags"
        },
        {
            "question_text": "Was sind \"Revenue Streams\"?",
            "correct_answer": "C",
            "skill_tag": "Revenue Streams",
            "topic": "Business Plan",
            "options": "A) Die Ausgaben eines Unternehmens|B) Die Mitarbeitenden|C) Die Einnahmequellen eines Unternehmens|D) Die Kundensegmente"
        },
        {
            "question_text": "Warum ist das Gründerteam im Businessplan wichtig?",
            "correct_answer": "B",
            "skill_tag": "Gründerteam",
            "topic": "Business Plan",
            "options": "A) Weil viele Gründer immer besser sind|B) Weil Investoren zuerst auf die Menschen schauen|C) Weil es gesetzlich vorgeschrieben ist|D) Weil das Team für Werbung zuständig ist"
        }
    ]

    with get_connection() as conn:
        cursor = conn.cursor()
        for q in questions:
            cursor.execute("""
                INSERT INTO questions (question_text, correct_answer, skill_tag, topic, options)
                VALUES (?, ?, ?, ?, ?)
            """, (q["question_text"], q["correct_answer"], q["skill_tag"], q["topic"], q["options"]))
        conn.commit()


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user and return user data if successful."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "role": row["role"]}
        return None


def create_session(teacher_id: str, topic: str, subtopic: str) -> int:
    """Create a new quiz session and return its ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (teacher_id, topic, subtopic) VALUES (?, ?, ?)",
            (teacher_id, topic, subtopic)
        )
        conn.commit()
        return cursor.lastrowid


def get_session(session_id: int) -> Optional[Dict[str, Any]]:
    """Get session details by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def close_session(session_id: int) -> None:
    """Mark a session as inactive."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
        conn.commit()


def get_questions_by_topic(topic: str) -> List[Dict[str, Any]]:
    """Get all questions for a specific topic."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, question_text, correct_answer, skill_tag, options FROM questions WHERE topic = ?",
            (topic,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_questions_for_student(topic: str) -> List[Dict[str, Any]]:
    """Get questions for students (includes question text for display)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, question_text, skill_tag, options FROM questions WHERE topic = ?",
            (topic,)
        )
        return [dict(row) for row in cursor.fetchall()]


def save_student_answer(session_id: int, student_id: str, question_id: int,
                        selected_answer: str, is_correct: bool) -> None:
    """Save a student's answer to the results table."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO results (session_id, student_id, question_id, selected_answer, is_correct)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, student_id, question_id, selected_answer, 1 if is_correct else 0))
        conn.commit()


def check_student_completed(session_id: int, student_id: str) -> bool:
    """Check if a student has already completed the quiz for this session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM results WHERE session_id = ? AND student_id = ?",
            (session_id, student_id)
        )
        return cursor.fetchone()[0] > 0


def get_participation_count(session_id: int) -> int:
    """Get the number of unique students who participated in a session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(DISTINCT student_id) FROM results WHERE session_id = ?",
            (session_id,)
        )
        return cursor.fetchone()[0]


def get_skill_statistics(session_id: int) -> List[Dict[str, Any]]:
    """
    Get success percentages per skill_tag for a session.
    IMPORTANT: This does NOT return question_text to maintain privacy.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                q.skill_tag,
                COUNT(r.id) as total_answers,
                SUM(r.is_correct) as correct_answers,
                ROUND(CAST(SUM(r.is_correct) AS FLOAT) / COUNT(r.id) * 100, 1) as success_rate
            FROM results r
            JOIN questions q ON r.question_id = q.id
            WHERE r.session_id = ?
            GROUP BY q.skill_tag
        """, (session_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_aggregated_results(session_id: int) -> Dict[str, Any]:
    """
    Get aggregated results for AI report generation.
    Returns skill-level statistics without exposing question text.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        # Get participation count
        cursor.execute(
            "SELECT COUNT(DISTINCT student_id) FROM results WHERE session_id = ?",
            (session_id,)
        )
        participant_count = cursor.fetchone()[0]

        # Get skill statistics
        skill_stats = get_skill_statistics(session_id)

        # Get overall success rate
        cursor.execute("""
            SELECT
                COUNT(id) as total,
                SUM(is_correct) as correct
            FROM results WHERE session_id = ?
        """, (session_id,))
        overall = cursor.fetchone()
        overall_rate = round((overall["correct"] / overall["total"] * 100), 1) if overall["total"] > 0 else 0

        # Get session info
        session = get_session(session_id)

        return {
            "session_id": session_id,
            "topic": session["topic"] if session else "Unknown",
            "subtopic": session["subtopic"] if session else "Unknown",
            "participant_count": participant_count,
            "overall_success_rate": overall_rate,
            "skill_breakdown": skill_stats
        }


def get_teacher_sessions(teacher_id: str) -> List[Dict[str, Any]]:
    """Get all sessions created by a teacher."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE teacher_id = ? ORDER BY created_at DESC",
            (teacher_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


def get_correct_answer(question_id: int) -> str:
    """Get the correct answer for a question."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT correct_answer FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        return row["correct_answer"] if row else ""
