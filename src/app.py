"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import sqlite3

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

DB_PATH = current_dir / "school.db"

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    with get_db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                schedule TEXT NOT NULL,
                max_participants INTEGER NOT NULL CHECK (max_participants > 0)
            );

            CREATE TABLE IF NOT EXISTS students (
                email TEXT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS activity_attendance (
                activity_id INTEGER NOT NULL,
                student_email TEXT NOT NULL,
                PRIMARY KEY (activity_id, student_email),
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                FOREIGN KEY (student_email) REFERENCES students(email) ON DELETE CASCADE
            );
            """
        )

        existing_count = conn.execute("SELECT COUNT(1) FROM activities").fetchone()[0]
        if existing_count == 0:
            for activity_name, activity_data in DEFAULT_ACTIVITIES.items():
                cursor = conn.execute(
                    """
                    INSERT INTO activities (name, description, schedule, max_participants)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        activity_name,
                        activity_data["description"],
                        activity_data["schedule"],
                        activity_data["max_participants"],
                    ),
                )
                activity_id = cursor.lastrowid

                for email in activity_data["participants"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO students (email) VALUES (?)",
                        (email,),
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO activity_attendance (activity_id, student_email)
                        VALUES (?, ?)
                        """,
                        (activity_id, email),
                    )

        conn.commit()


def load_activities() -> dict:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                a.id,
                a.name,
                a.description,
                a.schedule,
                a.max_participants,
                aa.student_email
            FROM activities a
            LEFT JOIN activity_attendance aa ON aa.activity_id = a.id
            ORDER BY a.name, aa.student_email
            """
        ).fetchall()

    activities = {}
    for row in rows:
        activity_name = row["name"]
        if activity_name not in activities:
            activities[activity_name] = {
                "description": row["description"],
                "schedule": row["schedule"],
                "max_participants": row["max_participants"],
                "participants": [],
            }
        if row["student_email"]:
            activities[activity_name]["participants"].append(row["student_email"])

    return activities


@app.on_event("startup")
def startup_event() -> None:
    initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return load_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with get_db_connection() as conn:
        activity = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        is_already_signed_up = conn.execute(
            """
            SELECT 1
            FROM activity_attendance
            WHERE activity_id = ? AND student_email = ?
            """,
            (activity["id"], email),
        ).fetchone()
        if is_already_signed_up:
            raise HTTPException(status_code=400, detail="Student is already signed up")

        conn.execute(
            "INSERT OR IGNORE INTO students (email) VALUES (?)",
            (email,),
        )
        conn.execute(
            """
            INSERT INTO activity_attendance (activity_id, student_email)
            VALUES (?, ?)
            """,
            (activity["id"], email),
        )
        conn.commit()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with get_db_connection() as conn:
        activity = conn.execute(
            "SELECT id FROM activities WHERE name = ?",
            (activity_name,),
        ).fetchone()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")

        removed_rows = conn.execute(
            """
            DELETE FROM activity_attendance
            WHERE activity_id = ? AND student_email = ?
            """,
            (activity["id"], email),
        ).rowcount
        if removed_rows == 0:
            raise HTTPException(
                status_code=400,
                detail="Student is not signed up for this activity",
            )

        conn.commit()

    return {"message": f"Unregistered {email} from {activity_name}"}
