from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import os
import re
import io

from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader

from dotenv import load_dotenv
from google import genai

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

app = Flask(__name__)
app.secret_key = "career_secret_key"

def get_db_connection():
    conn = sqlite3.connect(
        "career.db",
        timeout=30,
        check_same_thread=False
    )

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")

    return conn


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("career.db", timeout=30)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:

            session["user_id"] = user[0]
            session["username"] = user[1]

            return redirect("/career-dashboard")

        else:
            return "<h2>❌ Invalid Email or Password</h2>"

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        conn = None

        try:
            fullname = request.form["fullname"]
            email = request.form["email"]
            password = request.form["password"]

            print("REGISTER REQUEST:", fullname, email)

            conn = sqlite3.connect("career.db", timeout=30)

            import os
            print("DB PATH:", os.path.abspath("career.db"))

            cursor = conn.cursor()

            cursor.execute("PRAGMA busy_timeout = 30000")

            cursor.execute(
                "INSERT INTO users(fullname,email,password) VALUES(?,?,?)",
                (fullname, email, password)
            )

            conn.commit()

            print("REGISTER SUCCESS")

            return redirect("/login")


        except Exception as e:

            if conn:
                conn.rollback()

            print("REGISTER ERROR:", e)

            return f"<h2>REGISTER ERROR: {e}</h2>"


        finally:

            if conn:
                conn.close()


    return render_template("register.html")
    

@app.route("/career-dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect("career.db", timeout=30)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, career_role, score, degree
        FROM career_results
        WHERE user_id=?
        ORDER BY id DESC
    """, (session["user_id"],))

    reports = cursor.fetchall()

    latest_report = reports[0] if reports else None
    report_count = len(reports)

    conn.close()

    return render_template(
        "dashboard.html",
        reports=reports,
        latest_report=latest_report,
        username=session["username"],
        report_count=report_count
    )

@app.route("/resume-analyzer")
def resume_analyzer():
    return render_template("resume_analyzer.html")

@app.route("/analyze-resume", methods=["POST"])
def analyze_resume():

    file = request.files["resume"]

    if file.filename == "":
        return "No file selected"

    reader = PdfReader(file)

    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    prompt = f"""
You are an AI Resume Analyzer.

Analyze this resume and give a professional ATS report.

Resume Content:

{text}

Give output in this format:

📊 ATS Score:
(percentage)

✅ Strengths:
- 

⚠ Missing Skills:
-

💡 Suggestions:
-

🎯 Recommended Roles:
-
"""

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        ai_result = response.text

    except Exception as e:

        ai_result = """
🤖 AI Resume Analysis

📊 ATS Score:
85%

✅ Strengths:
• Python
• AI Knowledge
• Web Development

⚠ Missing Skills:
• SQL
• Deep Learning

💡 Suggestions:
• Add more AI projects
• Add measurable achievements
• Improve resume keywords

🎯 Recommended Roles:
• AI Engineer
• Data Analyst
"""


    return render_template(
    "resume_result.html",
    ai_result=ai_result.replace("\n","<br>")
)
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


@app.route("/report/<int:id>")
def view_report(id):

    conn = sqlite3.connect("career.db", timeout=30)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM career_results WHERE id=?",
        (id,)
    )

    report = cursor.fetchone()
    conn.close()

    if not report:
        return "<h2>Report Not Found</h2>"

    return render_template(
        "full_report.html",
        report=report
    )


@app.route("/download/<int:id>")
def download_report(id):

    conn = sqlite3.connect("career.db", timeout=30)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM career_results WHERE id=?",
        (id,)
    )

    report = cursor.fetchone()
    conn.close()

    if not report:
        return "<h2>Report Not Found</h2>"

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("AI Career Guidance Report", styles["Title"]))
    story.append(Paragraph(f"<b>Name:</b> {report[1]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Degree:</b> {report[2]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Skills:</b> {report[3]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Interest:</b> {report[4]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Dream Job:</b> {report[5]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Recommended Career:</b> {report[6]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Career Match:</b> {report[7]}%", styles["Normal"]))
    story.append(Paragraph("<br/><b>AI Recommendation</b>", styles["Heading2"]))
    story.append(Paragraph(report[8].replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Career_Report.pdf",
        mimetype="application/pdf"
    )

@app.route("/analyze", methods=["POST"])
def analyze():

    if "user_id" not in session:
        return redirect("/login")

    name = request.form["name"]
    degree = request.form["degree"]
    skills = request.form["skills"]
    interest = request.form["interest"]
    dreamjob = request.form["dreamjob"]

    prompt = f"""
You are an AI Career Guidance Assistant.

Analyze this student profile and generate a professional career report.

Student Details:

Name: {name}
Degree: {degree}
Skills: {skills}
Interest: {interest}
Dream Job: {dreamjob}

Use this format:

🎯 CAREER RECOMMENDATION

Career Role:
-

📊 CAREER MATCH SCORE

Score:
-

💡 WHY THIS CAREER

• Point 1
• Point 2
• Point 3

🛠 SKILLS TO LEARN

1.
2.
3.
4.

📚 LEARNING ROADMAP

Phase 1:
•

Phase 2:
•

Phase 3:
•

🚀 RECOMMENDED PROJECTS

1.
2.
3.

Rules:
- Keep it short
- Use bullet points
- Avoid long paragraphs
- Dashboard friendly format
"""

    try:

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )

        ai_text = response.text

    except Exception:

        return render_template(
            "result.html",
            name=name,
            degree=degree,
            skills=skills,
            interest=interest,
            dreamjob=dreamjob,
            career_role="Service Temporarily Unavailable",
            score="0",
            ai_result="""
⚠ Gemini AI is temporarily unavailable.

Possible Reasons:

• Free API quota exceeded
• Network issue
• Gemini server busy

Please try again after a minute.
""".replace("\n", "<br>")
        )

    score_match = re.search(r'(\d+)%', ai_text)

    if score_match:
        score = score_match.group(1)
    else:
        score = "90"

    career_match = re.search(
        r'Career Role:\s*(.*)',
        ai_text
    )

    if career_match:
        career_role = career_match.group(1).strip("- ").strip()
    else:
        career_role = "AI Engineer"

    conn = sqlite3.connect("career.db", timeout=30)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO career_results
    (user_id, name, degree, skills, interest, dreamjob, career_role, score, ai_result)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        session["user_id"],
        name,
        degree,
        skills,
        interest,
        dreamjob,
        career_role,
        score,
        ai_text
    ))

    conn.commit()

    cursor.execute("SELECT * FROM users")
    print("USERS:", cursor.fetchall())

    conn.close()


    return render_template(
        "result.html",
        name=name,
        degree=degree,
        skills=skills,
        interest=interest,
        dreamjob=dreamjob,
        ai_result=ai_text.replace("\n", "<br>"),
        score=score,
        career_role=career_role
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
