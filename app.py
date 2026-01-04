"""
Main Streamlit Application for Quiz System.
Provides Teacher and Student interfaces for conducting and taking quizzes.
"""

import streamlit as st
import qrcode
import io
import base64
import uuid
import time
import socket
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

# Import local modules
from database import (
    init_database,
    authenticate_user,
    create_session,
    get_session,
    close_session,
    get_questions_for_student,
    save_student_answer,
    check_student_completed,
    get_participation_count,
    get_skill_statistics,
    get_aggregated_results,
    get_teacher_sessions,
    get_correct_answer
)
from ai_engine import generate_pedagogical_report

# Page configuration
st.set_page_config(
    page_title="Quiz System - Business Plan",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .success-box {
        background-color: #D1FAE5;
        border-left: 4px solid #10B981;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    .question-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    .timer-display {
        font-size: 2rem;
        font-weight: bold;
        color: #DC2626;
        text-align: center;
        padding: 1rem;
        background-color: #FEE2E2;
        border-radius: 8px;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "student_id" not in st.session_state:
        st.session_state.student_id = None
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "answers" not in st.session_state:
        st.session_state.answers = {}
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "quiz_end_time" not in st.session_state:
        st.session_state.quiz_end_time = None
    if "quiz_completed" not in st.session_state:
        st.session_state.quiz_completed = False


def generate_qr_code(url: str) -> str:
    """Generate QR code and return as base64 string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def teacher_login():
    """Display teacher login form."""
    st.markdown('<p class="main-header">📚 Quiz System</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Teacher Portal</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            st.subheader("🔐 Teacher Login")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")

            if st.form_submit_button("Login", use_container_width=True):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")

        st.info("**Demo Credentials:** Username: `teacher` | Password: `demo123`")


def teacher_dashboard():
    """Display teacher dashboard with session management."""
    st.markdown('<p class="main-header">📚 Teacher Dashboard</p>', unsafe_allow_html=True)

    # Sidebar for navigation
    with st.sidebar:
        st.subheader(f"👋 Welcome, {st.session_state.user['username']}")
        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.current_session_id = None
            st.rerun()

    # Main content
    if st.session_state.current_session_id is None:
        create_new_session()
    else:
        show_active_session()


def create_new_session():
    """Display form to create a new quiz session."""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.subheader("🎯 Start New Quiz Session")

        with st.form("new_session"):
            topic = st.selectbox(
                "Select Topic",
                ["Business Plan"],
                help="Choose the main topic for the quiz"
            )

            subtopic = st.selectbox(
                "Select Subtopic",
                ["Fundamental Components"],
                help="Choose the specific area to assess"
            )

            st.info("""
            **About this quiz:**
            - 5 questions covering Business Plan fundamentals
            - Students have 5 minutes to complete
            - Real-time participation tracking
            - AI-powered performance analysis
            """)

            if st.form_submit_button("🚀 Start Session", use_container_width=True):
                session_id = create_session(
                    teacher_id=st.session_state.user['username'],
                    topic=topic,
                    subtopic=subtopic
                )
                st.session_state.current_session_id = session_id
                st.rerun()

    # Show previous sessions
    st.divider()
    st.subheader("📋 Previous Sessions")

    sessions = get_teacher_sessions(st.session_state.user['username'])
    if sessions:
        for session in sessions[:5]:
            status = "🟢 Active" if session['is_active'] else "⚪ Closed"
            with st.expander(f"{status} Session #{session['id']} - {session['topic']}"):
                st.write(f"**Subtopic:** {session['subtopic']}")
                st.write(f"**Created:** {session['created_at']}")

                if session['is_active']:
                    if st.button(f"View Session #{session['id']}", key=f"view_{session['id']}"):
                        st.session_state.current_session_id = session['id']
                        st.rerun()
    else:
        st.info("No previous sessions found. Create your first quiz session above!")


def show_active_session():
    """Display active session with QR code and live dashboard."""
    session = get_session(st.session_state.current_session_id)

    if not session:
        st.error("Session not found!")
        st.session_state.current_session_id = None
        st.rerun()
        return

    # Session header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"📊 Session #{session['id']}: {session['topic']}")
        st.caption(f"Subtopic: {session['subtopic']}")
    with col2:
        if st.button("🔙 Back to Sessions"):
            st.session_state.current_session_id = None
            st.rerun()

    st.divider()

    # Three columns: QR Code, Stats, Skills
    col1, col2, col3 = st.columns([1, 1, 1])

    # Generate student URL with local IP for mobile access
    local_ip = get_local_ip()
    default_url = f"http://{local_ip}:8501"

    base_url = st.text_input(
        "Base URL (your Streamlit app URL)",
        value=default_url,
        help="This URL uses your local IP so mobile devices can connect"
    )
    student_url = f"{base_url}?role=student&session_id={session['id']}"

    with col1:
        st.subheader("📱 QR Code")
        qr_base64 = generate_qr_code(student_url)
        st.image(f"data:image/png;base64,{qr_base64}", width=250)
        st.code(student_url, language=None)

        if st.button("📋 Copy URL"):
            st.toast("URL displayed above - copy manually")

    with col2:
        st.subheader("📈 Live Statistics")

        # Auto-refresh participation count
        participation = get_participation_count(session['id'])

        st.metric(
            label="👥 Students Participated",
            value=participation,
            delta=None
        )

        # Refresh button
        if st.button("🔄 Refresh Stats"):
            st.rerun()

        # Auto-refresh option
        auto_refresh = st.checkbox("Auto-refresh (every 5s)")
        if auto_refresh:
            time.sleep(5)
            st.rerun()

    with col3:
        st.subheader("🎯 Skill Performance")

        # Get skill statistics - NOTE: This does NOT fetch question_text
        stats = get_skill_statistics(session['id'])

        if stats:
            for skill in stats:
                rate = skill['success_rate']
                if rate >= 80:
                    color = "🟢"
                elif rate >= 60:
                    color = "🟡"
                else:
                    color = "🔴"

                st.write(f"{color} **{skill['skill_tag']}**")
                st.progress(rate / 100)
                st.caption(f"{rate}% ({skill['correct_answers']}/{skill['total_answers']})")
        else:
            st.info("Waiting for student responses...")

    st.divider()

    # Visualization section
    if stats:
        st.subheader("📊 Performance Visualization")

        col1, col2 = st.columns(2)

        with col1:
            # Bar chart for skill performance
            df = pd.DataFrame(stats)
            fig = px.bar(
                df,
                x='skill_tag',
                y='success_rate',
                color='success_rate',
                color_continuous_scale=['#EF4444', '#F59E0B', '#10B981'],
                title='Success Rate by Skill Area',
                labels={'skill_tag': 'Skill', 'success_rate': 'Success Rate (%)'}
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Pie chart for answer distribution
            fig = go.Figure(data=[go.Pie(
                labels=[s['skill_tag'] for s in stats],
                values=[s['total_answers'] for s in stats],
                hole=.4,
                marker_colors=['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']
            )])
            fig.update_layout(title='Response Distribution by Skill')
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # AI Report section
    st.subheader("🤖 AI Pedagogical Report")

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("📝 Generate AI Report", use_container_width=True):
            if participation == 0:
                st.warning("No student responses yet. Wait for students to complete the quiz.")
            else:
                with st.spinner("Generating AI report..."):
                    aggregated = get_aggregated_results(session['id'])
                    report = generate_pedagogical_report(aggregated)
                    st.session_state.ai_report = report

    with col2:
        if "ai_report" in st.session_state:
            st.markdown(st.session_state.ai_report)

    # Session controls
    st.divider()
    col1, col2 = st.columns(2)

    with col2:
        if session['is_active']:
            if st.button("🛑 End Session", type="secondary", use_container_width=True):
                close_session(session['id'])
                st.success("Session closed successfully!")
                st.rerun()


def student_quiz():
    """Display student quiz interface."""
    # Get session ID from URL params
    params = st.query_params
    session_id = params.get("session_id")

    if not session_id:
        st.error("❌ Invalid access. Please use the QR code provided by your teacher.")
        return

    session_id = int(session_id)
    session = get_session(session_id)

    if not session:
        st.error("❌ Session not found. Please contact your teacher.")
        return

    if not session['is_active']:
        st.warning("⚠️ This quiz session has ended.")
        return

    # Generate or retrieve student ID
    if st.session_state.student_id is None:
        st.session_state.student_id = str(uuid.uuid4())[:8]

    # Check if student already completed
    if check_student_completed(session_id, st.session_state.student_id):
        st.session_state.quiz_completed = True

    if st.session_state.quiz_completed:
        show_quiz_completion()
        return

    # Quiz header
    st.markdown('<p class="main-header">📝 Business Plan Quiz</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">{session["subtopic"]}</p>', unsafe_allow_html=True)

    # Get questions
    questions = get_questions_for_student("Business Plan")

    if not questions:
        st.error("No questions available for this quiz.")
        return

    # Start quiz button
    if not st.session_state.quiz_started:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.info(f"""
            **Quiz Information:**
            - 📚 Topic: {session['topic']}
            - 📋 Questions: {len(questions)}
            - ⏱️ Time Limit: 5 minutes
            - 📝 Answer all questions before time runs out
            """)

            if st.button("🚀 Start Quiz", use_container_width=True, type="primary"):
                st.session_state.quiz_started = True
                st.session_state.quiz_end_time = datetime.now() + timedelta(minutes=5)
                st.session_state.current_question = 0
                st.session_state.answers = {}
                st.rerun()
        return

    # Timer display
    if st.session_state.quiz_end_time:
        remaining = st.session_state.quiz_end_time - datetime.now()
        remaining_seconds = max(0, int(remaining.total_seconds()))

        if remaining_seconds <= 0:
            # Time's up - auto submit
            submit_all_answers(session_id, questions)
            st.session_state.quiz_completed = True
            st.rerun()

        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60

        timer_color = "#DC2626" if remaining_seconds < 60 else "#1E3A8A"
        st.markdown(
            f'<div class="timer-display" style="color: {timer_color};">'
            f'⏱️ Time Remaining: {minutes:02d}:{seconds:02d}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # Progress bar
    progress = (st.session_state.current_question) / len(questions)
    st.progress(progress)
    st.caption(f"Question {st.session_state.current_question + 1} of {len(questions)}")

    # Current question
    current_q = questions[st.session_state.current_question]
    options = current_q['options'].split('|')

    # Display question using native Streamlit components
    st.subheader(f"Frage {st.session_state.current_question + 1}")
    st.markdown(f"**{current_q['question_text']}**")
    st.caption(f"Skill Area: {current_q['skill_tag']}")

    # Answer options
    current_answer = st.session_state.answers.get(current_q['id'])

    for opt in options:
        option_letter = opt[0]
        option_text = opt[2:] if len(opt) > 2 else opt

        is_selected = current_answer == option_letter
        button_type = "primary" if is_selected else "secondary"

        if st.button(
            f"{'✓ ' if is_selected else ''}{opt}",
            key=f"opt_{current_q['id']}_{option_letter}",
            use_container_width=True,
            type=button_type
        ):
            st.session_state.answers[current_q['id']] = option_letter
            st.rerun()

    st.divider()

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.session_state.current_question > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.current_question -= 1
                st.rerun()

    with col2:
        answered = len(st.session_state.answers)
        st.caption(f"Answered: {answered}/{len(questions)}")

    with col3:
        if st.session_state.current_question < len(questions) - 1:
            if st.button("Next ➡️", use_container_width=True):
                st.session_state.current_question += 1
                st.rerun()
        else:
            if st.button("✅ Submit Quiz", use_container_width=True, type="primary"):
                if len(st.session_state.answers) < len(questions):
                    st.warning(f"Please answer all questions. ({len(st.session_state.answers)}/{len(questions)} answered)")
                else:
                    submit_all_answers(session_id, questions)
                    st.session_state.quiz_completed = True
                    st.rerun()


def submit_all_answers(session_id: int, questions: list):
    """Submit all student answers to the database."""
    student_id = st.session_state.student_id

    for question in questions:
        q_id = question['id']
        selected = st.session_state.answers.get(q_id, "")
        correct_answer = get_correct_answer(q_id)
        is_correct = selected == correct_answer

        save_student_answer(
            session_id=session_id,
            student_id=student_id,
            question_id=q_id,
            selected_answer=selected,
            is_correct=is_correct
        )


def show_quiz_completion():
    """Display quiz completion screen for students."""
    st.markdown('<p class="main-header">🎉 Quiz Completed!</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.success("""
        **Thank you for completing the quiz!**

        Your responses have been submitted successfully.
        Your teacher will review the class results.
        """)

        st.balloons()

        st.info("""
        📊 **What happens next?**

        - Your teacher will analyze the class performance
        - Focus areas will be identified for the next lesson
        - No individual scores will be shared publicly
        """)


def main():
    """Main application entry point."""
    # Initialize database
    init_database()

    # Initialize session state
    init_session_state()

    # Check URL parameters for role
    params = st.query_params
    role = params.get("role", "teacher")

    if role == "student":
        student_quiz()
    else:
        # Teacher flow
        if not st.session_state.authenticated:
            teacher_login()
        else:
            teacher_dashboard()


if __name__ == "__main__":
    main()
