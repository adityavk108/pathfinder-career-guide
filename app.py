import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
database_url = os.environ.get("DATABASE_URL", "")
if database_url:
    database_url = database_url.replace("postgres://", "postgresql://")
    if "supabase" in database_url:
        database_url = database_url.split("?")[0] + "?sslmode=require"
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

@app.template_filter('fromjson')
def fromjson_filter(s):
    return json.loads(s)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    assessments = db.relationship("Assessment", backref="user", lazy=True)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subjects = db.Column(db.String(500))
    hobbies = db.Column(db.String(500))
    style = db.Column(db.String(200))
    value = db.Column(db.String(500))
    careers_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Gemini API Configuration ---
try:
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("MODEL_NAME")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    
    genai.configure(api_key=api_key)
    
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "careers": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "title": {"type": "STRING", "description": "The name of the career"},
                        "match_reason": {"type": "STRING", "description": "Why this is a good match"},
                        "roadmap": {"type": "ARRAY", "items": {"type": "STRING"}}
                    },
                    "required": ["title", "match_reason", "roadmap"]
                }
            }
        },
        "required": ["careers"]
    }
    
    model = genai.GenerativeModel(model_name)
    
except ValueError as e:
    print(e)
    model = None
except Exception as e:
    print(f"Gemini configuration error: {e}")
    model = None

# --- Auth Routes ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("assessment"))
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for("register"))
        
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for("assessment"))
    
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("assessment"))
    
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("assessment"))
        
        flash("Invalid email or password", "error")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route("/history")
@login_required
def history():
    assessments = Assessment.query.filter_by(user_id=current_user.id).order_by(Assessment.created_at.desc()).all()
    return render_template("history.html", assessments=assessments)

# --- App Routes ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/assessment")
@login_required
def assessment():
    return render_template("assessment.html")

@app.route("/results", methods=["POST"])
@login_required
def results():
    if not model:
        return "Error: Gemini API is not configured.", 500
    
    try:
        subjects = request.form.get("subjects", "")
        hobbies = request.form.get("hobbies", "")
        style = request.form.get("style", "")
        value = request.form.get("value", "")
        
        prompt = f"""
        Act as an expert career counselor for a high school or early college student.
        
        The student has provided:
        - Favorite Subjects: {subjects}
        - Hobbies and Interests: {hobbies}
        - Preferred Work Style: {style}
        - What they value in a job: {value}
        
        Generate their "Top 3 Career Matches". For each career provide:
        1. title: The job title.
        2. match_reason: A 1-2 sentence explanation of why it's a good match.
        3. roadmap: A list of 3-4 actionable steps to start exploring this path.
        
        Return only valid JSON adhering to: {json.dumps(response_schema)}.
        """
        
        request_generation_config = {
            "response_mime_type": "application/json",
            "response_schema": response_schema
        }
        
        chat = model.start_chat()
        response = chat.send_message([prompt], generation_config=request_generation_config)
        
        response_data = json.loads(response.text)
        careers = response_data.get("careers", [])
        
        assessment = Assessment(
            user_id=current_user.id,
            subjects=subjects,
            hobbies=hobbies,
            style=style,
            value=value,
            careers_json=json.dumps(careers)
        )
        db.session.add(assessment)
        db.session.commit()
        
        return render_template("results.html", careers=careers)
        
    except Exception as e:
        print(f"Error processing results: {e}")
        return redirect(url_for("error_page", message=str(e)))

@app.route("/error")
def error_page():
    message = request.args.get("message", "An unknown error occurred.")
    return render_template("error.html", error_message=message)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
