# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Persistent SQLite storage for activities and enrollments

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run migrations and seed initial data:

   ```
   python manage_db.py
   ```

3. Run the application:

   ```
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## Database

- SQLite database file: `src/data/mergington.sqlite3`
- Seed source: `src/seed_data.json`
- Migration + seed command: `python manage_db.py`
- Reset database and reseed:

  ```
  python manage_db.py --reset
  ```

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |

## Data Model

The application uses normalized tables:

1. **User**
   - `id`
   - `email` (unique)
   - `name`
   - `role`

2. **Club**
   - `id`
   - `name` (unique)
   - `description`
   - `contact_email`

3. **Activity**
   - `id`
   - `name` (unique)
   - `description`
   - `schedule`
   - `max_participants`
   - `club_id`

4. **ActivityEnrollment**
   - `id`
   - `activity_id`
   - `user_id`
   - Unique constraint on (`activity_id`, `user_id`)

The API response shape for `/activities` remains unchanged for frontend compatibility.
