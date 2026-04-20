"""Mergington High School activities API with persistent SQLite storage."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from db import (
    ActivityCapacityError,
    ActivityNotFoundError,
    DuplicateEnrollmentError,
    EnrollmentNotFoundError,
    fetch_activities,
    initialize_database,
    signup_student,
    unregister_student,
)

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

current_dir = Path(__file__).parent
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(current_dir, "static")),
    name="static",
)


@app.on_event("startup")
def startup() -> None:
    """Ensure schema and seed data exist before serving requests."""
    initialize_database(current_dir / "seed_data.json")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return fetch_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        signup_student(activity_name, email)
        return {"message": f"Signed up {email} for {activity_name}"}
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Activity not found") from exc
    except DuplicateEnrollmentError as exc:
        raise HTTPException(status_code=400, detail="Student is already signed up") from exc
    except ActivityCapacityError as exc:
        raise HTTPException(status_code=400, detail="Activity is full") from exc


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        unregister_student(activity_name, email)
        return {"message": f"Unregistered {email} from {activity_name}"}
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Activity not found") from exc
    except EnrollmentNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        ) from exc
