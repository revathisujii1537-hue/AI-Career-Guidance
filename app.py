from flask import Flask, render_template, request, redirect, session,send_file
import sqlite3
import os
import re
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from dotenv import load_dotenv
from google import genai


load_dotenv()


client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

app = Flask(__name__)

app.secret_key = "career_secret_key"


@app.route("/")
def home():
    return render_template("home.html")



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("career.db")
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

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]


        conn = sqlite3.connect("career.db")
        cursor = conn.cursor()


        cursor.execute(
            "INSERT INTO users(fullname,email,password) VALUES(?,?,?)",
            (fullname,email,password)
        )


        conn.commit()
        conn.close()


        return redirect("/login")


    return render_template("register.html")




@app.route("/career-dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    
    conn = sqlite3.connect("career.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id,name,career_role,score,degree
    FROM career_results
    WHERE user_id=?
    ORDER BY id DESC
    """,
    (session["user_id"],)
    )

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
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/download/<int:id>")
def download_report(id):

    conn = sqlite3.connect("career.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM career_results WHERE id=?",
        (id,)
    )

    report = cursor.fetchone()
    conn.close()

    if not report:
        return "Report not found"

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>AI Career Guidance Report</b>", styles["Title"]))
    story.append(Paragraph(f"<b>Name:</b> {report[1]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Degree:</b> {report[2]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Skills:</b> {report[3]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Interest:</b> {report[4]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Dream Job:</b> {report[5]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Recommended Career:</b> {report[6]}", styles["Normal"]))
    story.append(Paragraph(f"<b>Career Match:</b> {report[7]}%", styles["Normal"]))
    story.append(Paragraph("<b>AI Recommendation</b>", styles["Heading2"]))
    story.append(Paragraph(report[8].replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Career_Report.pdf",
        mimetype="application/pdf"
    )

@app.route("/report/<int:id>")
def view_report(id):

    conn = sqlite3.connect("career.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM career_results WHERE id=?",
        (id,)
    )

    report = cursor.fetchone()

    conn.close()

    return render_template(
        "full_report.html",
        report=report
    )




@app.route("/analyze", methods=["POST"])
def analyze():

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


    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt
    )


    ai_text = response.text

    try:
       response = client.models.generate_content(
          model="gemini-3.5-flash",
          contents=prompt
       )

       ai_text = response.text

except Exception:
    return """
    <h2>⚠️ AI Service is temporarily unavailable.</h2>
    <p>Your Gemini API free quota has been reached or the service is busy.</p>
    <p>Please try again after a minute.</p>
    <br>
    <a href="/career-dashboard">
        <button>⬅ Back to Dashboard</button>
    </a>
    """




    # Extract Score

    score_match = re.search(r'(\d+)%', ai_text)

    if score_match:
        score = score_match.group(1)
    else:
        score = "90"



    # Extract Career Role

    career_match = re.search(
        r'Career Role:\s*(.*)',
        ai_text
    )


    if career_match:
        career_role = career_match.group(1)
    else:
        career_role = "AI Engineer"


    conn = sqlite3.connect("career.db")

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
    conn.close()     



    return render_template(
        "result.html",
        name=name,
        degree=degree,
        skills=skills,
        interest=interest,
        dreamjob=dreamjob,
        ai_result=ai_text.replace("\n","<br>"),
        score=score,
        career_role=career_role
    )



if __name__ == "__main__":
    app.run(debug=True)
