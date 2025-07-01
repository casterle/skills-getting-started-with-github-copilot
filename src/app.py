"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import re
import sqlite3
from typing import List, Dict
from email_validator import validate_email, EmailNotValidError
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = os.path.join(current_dir, "activities.db")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS activities (
        name TEXT PRIMARY KEY,
        description TEXT,
        schedule TEXT,
        max_participants INTEGER
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS participants (
        activity_name TEXT,
        email TEXT,
        PRIMARY KEY (activity_name, email),
        FOREIGN KEY (activity_name) REFERENCES activities(name)
    )''')
    conn.commit()
    conn.close()

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    # Sports related activities
    "Soccer Team": {
        "description": "Join the school soccer team and compete in local leagues",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 18,
        "participants": ["lucas@mergington.edu", "mia@mergington.edu"]
    },
    "Basketball Club": {
        "description": "Practice basketball skills and play friendly matches",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["liam@mergington.edu", "ava@mergington.edu"]
    },
    # Artistic activities
    "Drama Club": {
        "description": "Participate in school plays and improve acting skills",
        "schedule": "Mondays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["noah@mergington.edu", "isabella@mergington.edu"]
    },
    "Art Workshop": {
        "description": "Explore painting, drawing, and other visual arts",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 16,
        "participants": ["amelia@mergington.edu", "benjamin@mergington.edu"]
    },
    # Intellectual activities
    "Math Olympiad": {
        "description": "Prepare for math competitions and solve challenging problems",
        "schedule": "Fridays, 2:00 PM - 3:30 PM",
        "max_participants": 10,
        "participants": ["charlotte@mergington.edu", "elijah@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 14,
        "participants": ["william@mergington.edu", "harper@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.on_event("startup")
def startup_event():
    init_db()
    # Populate DB if empty
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM activities")
    if c.fetchone()[0] == 0:
        for name, details in activities.items():
            c.execute("INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                      (name, details["description"], details["schedule"], details["max_participants"]))
            for email in details["participants"]:
                c.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (name, email))
        conn.commit()
    conn.close()


@app.get("/activities")
def get_activities(db=Depends(get_db)):
    c = db.cursor()
    c.execute("SELECT * FROM activities")
    activities_dict = {}
    for row in c.fetchall():
        name = row["name"]
        c2 = db.cursor()
        c2.execute("SELECT email FROM participants WHERE activity_name=?", (name,))
        participants = [r["email"] for r in c2.fetchall()]
        activities_dict[name] = {
            "description": row["description"],
            "schedule": row["schedule"],
            "max_participants": row["max_participants"],
            "participants": participants
        }
    return activities_dict


@app.post("/activities/{activity_name}/signup")
@limiter.limit("5/minute")
def signup_for_activity(activity_name: str, email: str, request: Request, db=Depends(get_db)):
    c = db.cursor()
    c.execute("SELECT * FROM activities WHERE name=?", (activity_name,))
    activity = c.fetchone()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    c.execute("SELECT COUNT(*) FROM participants WHERE activity_name=?", (activity_name,))
    count = c.fetchone()[0]
    if count >= activity["max_participants"]:
        raise HTTPException(status_code=409, detail="Activity is full", headers={"X-Error-Type": "activity_full"})
    c.execute("SELECT * FROM participants WHERE activity_name=? AND email=?", (activity_name, email))
    if c.fetchone():
        raise HTTPException(status_code=409, detail="Student already registered for this activity", headers={"X-Error-Type": "already_registered"})
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        raise HTTPException(status_code=422, detail=f"Invalid email: {str(e)}")
    c.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (activity_name, email))
    db.commit()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.post("/activities/{activity_name}/unregister")
@limiter.limit("5/minute")
def unregister_from_activity(activity_name: str, email: str, request: Request, db=Depends(get_db)):
    c = db.cursor()
    c.execute("SELECT * FROM activities WHERE name=?", (activity_name,))
    if not c.fetchone():
        raise HTTPException(status_code=404, detail="Activity not found")
    c.execute("SELECT * FROM participants WHERE activity_name=? AND email=?", (activity_name, email))
    if not c.fetchone():
        raise HTTPException(status_code=409, detail="Student is not registered for this activity", headers={"X-Error-Type": "not_registered"})
    c.execute("DELETE FROM participants WHERE activity_name=? AND email=?", (activity_name, email))
    db.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later."}
    )
