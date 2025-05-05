# TripAdvisor API Documentation

A comprehensive FastAPI application that provides API documentation for a TripAdvisor clone with AI-powered trip planning features.

## Key Features

- AI-driven trip planning and recommendations
- Trip adjustments based on weather and traffic data
- Group trip planning and collaboration
- Blog post creation and management
- Complete trip management

## Authentication

- JWT-based authentication system
- User registration and login
- Password reset functionality

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Start the server:
   ```
   python main.py
   ```
   Or use uvicorn directly:
   ```
   uvicorn main:app --reload
   ```

2. Access the API documentation at:
   ```
   http://localhost:8000/docs
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get access token
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

### Trips
- `GET /trips` - List all trips
- `POST /trips` - Create a new trip
- `GET /trips/{trip_id}` - Get a specific trip
- `PUT /trips/{trip_id}` - Update a trip
- `DELETE /trips/{trip_id}` - Delete a trip

### Groups
- `GET /groups` - List all groups
- `POST /groups` - Create a new group
- `POST /groups/{group_id}/invite` - Invite users to a group

### Blogs
- `GET /blogs` - List all blogs
- `POST /blogs` - Create a new blog post

### Weather
- `GET /weather/forecast/{trip_id}` - Get weather forecast for a trip

### Recommendations
- `POST /recommendations` - Get AI-powered recommendations

## Authentication

All endpoints (except registration and login) require authentication:

1. Register a new user at `/auth/register`
2. Get an access token at `/auth/login`
3. Click the "Authorize" button in the Swagger UI and enter your token
4. Use the authenticated endpoints

## Architecture

- Frontend: React SPA with Redux
- Backend: Spring Boot microservices
- Database: PostgreSQL
- Authentication: JWT
- External integrations: Weather API, Traffic API, AI recommendation engine 