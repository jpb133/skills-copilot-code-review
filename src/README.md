# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- View active announcements
- Manage announcements when signed in as a teacher/admin

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| POST   | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Remove a student from an activity                                   |
| POST   | `/auth/login?username={username}&password={password}`            | Sign in as a teacher or admin                                       |
| GET    | `/auth/check-session?username={username}`                        | Validate a signed-in user                                           |
| GET    | `/announcements`                                                 | Get active announcements for the banner                             |
| GET    | `/announcements/manage?teacher_username={username}`              | List all announcements (auth required)                              |
| POST   | `/announcements?teacher_username={username}`                     | Create announcement (auth required)                                 |
| PUT    | `/announcements/{announcement_id}?teacher_username={username}`   | Update announcement (auth required)                                 |
| DELETE | `/announcements/{announcement_id}?teacher_username={username}`   | Delete announcement (auth required)                                 |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

3. **Announcements** - Uses generated MongoDB identifier:
   - Title
   - Message
   - Optional start date
   - Required expiration date

All data is stored in MongoDB.
