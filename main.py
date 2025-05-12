# Architecture Recommendation:
# - Frontend: React SPA with Redux for state management, Material UI for components
# - Backend: Spring Boot microservices architecture
#   - API Gateway for routing and authentication
#   - Core services: UserService, TripService, BlogService, WeatherService, etc.
# - Database: PostgreSQL with separate schemas for different domains
# - Authentication: JWT-based with refresh tokens
# - External Integrations: Weather API, Traffic API, AI recommendation engine
# - Deployment: Docker containers orchestrated with Kubernetes

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter, Query, Path, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime, timedelta
import jwt
from passlib.context import CryptContext
import uvicorn
from enum import Enum
from uuid import UUID, uuid4
import re
import json

# Initialize FastAPI app
app = FastAPI(
    title="WanderWise API",
    description="API documentation for the WanderWise AI-powered trip planning and management platform",
    version="1.0.0",
    openapi_tags=[
        {"name": "Home", "description": "Homepage information"},
        {"name": "About", "description": "About page information"},
        {"name": "Auth", "description": "Authentication operations"},
        {"name": "Groups", "description": "Group trip planning and collaboration"},
        {"name": "Blogs", "description": "Blog post management"},
        {"name": "Weather", "description": "Weather data integration"},
        {"name": "Traffic", "description": "Traffic information"},
        {"name": "TripPlan", "description": "AI-powered trip planning"},
        {"name": "Profile", "description": "User profile management"}
    ]
)

# Custom OpenAPI schema generator to remove validation error responses
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Remove all 422 Validation Error responses
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if "responses" in openapi_schema["paths"][path][method]:
                if "422" in openapi_schema["paths"][path][method]["responses"]:
                    del openapi_schema["paths"][path][method]["responses"]["422"]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication setup
SECRET_KEY = "your-secret-key-for-jwt-should-be-very-secure-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")

# ====================== Models ======================

# New Models for Home, About, Contact
class FeaturedTrip(BaseModel):
    id: str
    title: str
    image_url: str
    description: str
    days: int
    avg_rating: float

class Banner(BaseModel):
    id: str
    image_url: str
    title: str
    description: str
    link: str

class Testimonial(BaseModel):
    id: str
    name: str
    photo_url: Optional[str] = None
    content: str
    rating: float

class HomeResponse(BaseModel):
    featured_trips: List[FeaturedTrip]
    banners: List[Banner]
    testimonials: List[Testimonial]

class AboutResponse(BaseModel):
    title: str
    content: str

class ContactResponse(BaseModel):
    email: str
    phone: str

class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    message: str

class MessageResponse(BaseModel):
    status: str
    message: str

# Auth Models
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=3, max_length=100)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: str = None

class UserResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: str
    created_at: datetime

# Common Models
class LocationBase(BaseModel):
    city: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Group Models
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    trip_id: str

class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    trip_id: str
    members: List[str]
    created_by: str
    created_at: datetime

class GroupInvite(BaseModel):
    email: EmailStr
    message: Optional[str] = None
    group_id: str

# Blog Models
class BlogCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=100)
    content: str
    trip_id: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = True

class BlogResponse(BaseModel):
    id: str
    title: str
    content: str
    trip_id: Optional[str] = None
    tags: List[str] = []
    is_public: bool
    author_id: str
    created_at: datetime
    updated_at: datetime

# Weather Models
class WeatherData(BaseModel):
    location: LocationBase
    date: date
    temperature: float
    conditions: str
    humidity: int
    wind_speed: float
    precipitation_chance: float

class WeatherCheckRequest(BaseModel):
    trip_id: str
    destination: str
    start_date: date
    end_date: date

class SevereWeatherDay(BaseModel):
    date: date
    condition: str
    risk_level: str
    reason: str

class ProposedItineraryChange(BaseModel):
    new_start_date: date
    new_end_date: date
    new_destination: str

class WeatherCheckResponse(BaseModel):
    message: str
    severe_weather_days: List[SevereWeatherDay]
    recommended_actions: List[str]
    proposed_itinerary_change: ProposedItineraryChange
    user_decision_required: bool

class TripChangeRequest(BaseModel):
    trip_id: str
    confirm: bool
    new_start_date: date
    new_destination: str

class NewItinerary(BaseModel):
    start_date: date
    end_date: date
    destination: str

class TripChangeResponse(BaseModel):
    message: str
    trip_id: str
    new_itinerary: NewItinerary

# Traffic Models
class TrafficLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class TrafficInfo(BaseModel):
    origin: LocationBase
    destination: LocationBase
    date: date
    time: str
    traffic_level: TrafficLevel
    estimated_delay_minutes: int
    alternative_routes: Optional[List[str]] = None

# Trip Plan Models
class TripPlanExtractRequest(BaseModel):
    text: str

class TripPlanExtractResponse(BaseModel):
    output: Dict[str, Any]
    metadata: Dict[str, Any]

class BudgetBreakdown(BaseModel):
    total: str
    breakdown: Dict[str, str]

class GeoLocation(BaseModel):
    location: str
    latitude: str
    longitude: str

class Logistics(BaseModel):
    departure_time: str
    arrival_time: str
    tips: str

class Checkpoint(BaseModel):
    origin: GeoLocation
    destination: GeoLocation
    logistics: Logistics

class FoodPlace(BaseModel):
    title: str
    address: str
    latitude: float
    longitude: float
    rating: float
    ratingCount: int
    category: str
    phoneNumber: str
    cid: str
    cost: str
    website: Optional[str] = None

class MealPlan(BaseModel):
    breakfast: FoodPlace
    launch: FoodPlace
    dinner: FoodPlace

class Accommodation(BaseModel):
    title: str
    address: str
    latitude: float
    longitude: float
    rating: float
    ratingCount: int
    category: str
    phoneNumber: str
    cid: str
    website: Optional[str] = None

class SpotSuggestion(BaseModel):
    name: str
    description: str
    latitude: float
    longitude: float
    recommendedTime: str
    estimatedDurationHours: int

class TripPlanResponse(BaseModel):
    output: Dict[str, Any]
    metadata: Dict[str, Any]

# AI Recommendation Models
class RecommendationRequest(BaseModel):
    location: Optional[LocationBase] = None
    travel_dates: Optional[List[date]] = None
    preferences: Optional[Dict[str, Any]] = None
    budget_range: Optional[Dict[str, float]] = None
    group_size: Optional[int] = None

class Recommendation(BaseModel):
    id: str
    type: str  # 'DESTINATION', 'ACTIVITY', 'ACCOMMODATION', etc.
    title: str
    description: str
    location: Optional[LocationBase] = None
    estimated_cost: Optional[float] = None
    rating: Optional[float] = None
    images: List[str] = []
    tags: List[str] = []

# Profile Models
class TripBasicInfo(BaseModel):
    tripId: str
    tripName: str
    startDate: date
    days: int
    people: int
    budget: float
    status: str

class UserProfile(BaseModel):
    userId: str
    name: str
    email: EmailStr
    currentTrip: Optional[TripBasicInfo] = None
    pastTrips: List[TripBasicInfo] = []

class TripDetails(BaseModel):
    tripId: str
    tripName: str
    startDate: date
    status: str
    days: int
    budget: float
    people: int
    placesVisited: List[str] = []
    placesLeft: List[str] = []

class PlaceUpdateRequest(BaseModel):
    place: str

class PlaceUpdateResponse(BaseModel):
    message: str
    placesVisited: List[str]
    placesLeft: List[str]

class AddPlaceResponse(BaseModel):
    message: str
    placesLeft: List[str]

# ====================== Helper Functions ======================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except jwt.PyJWTError:
        raise credentials_exception
    
    # In a real app, we would fetch the user from the database
    # Here we're just mocking it
    user = {"id": token_data.user_id, "username": "testuser", "email": "test@example.com", "full_name": "Test User", "created_at": datetime.now()}
    
    if user is None:
        raise credentials_exception
    return user

# New helper functions for trip planning
def extract_trip_details_from_text(text: str) -> Dict[str, Any]:
    """
    Extract trip details from natural language text using simple pattern matching.
    In a real app, this would use a more sophisticated NLP model.
    """
    # Very basic extraction logic - would be replaced with actual NLP
    origin_match = re.search(r'from\s+(\w+)', text, re.IGNORECASE)
    destination_match = re.search(r'to\s+(\w+)', text, re.IGNORECASE)
    days_match = re.search(r'(\d+)\s+days', text, re.IGNORECASE)
    budget_match = re.search(r'budget\s+(\d+)k', text, re.IGNORECASE)
    people_match = re.search(r'(\d+)\s+friends', text, re.IGNORECASE)
    
    origin = origin_match.group(1) if origin_match else ""
    destination = destination_match.group(1) if destination_match else ""
    days = days_match.group(1) if days_match else ""
    budget = str(int(budget_match.group(1)) * 1000) if budget_match else ""
    people = str(int(people_match.group(1)) + 1) if people_match else "1"  # +1 to include the user
    
    return {
        "origin": origin,
        "destination": destination,
        "days": days,
        "budget": budget,
        "people": people,
        "preferences": "",
        "tripType": "oneWay",
        "journeyDate": "today",
        "travelClass": "economy"
    }

def generate_trip_itinerary(
    origin: str,
    destination: str,
    days: str,
    budget: str,
    people: str,
    preferences: str,
    trip_type: str,
    journey_date: str,
    travel_class: str
) -> Dict[str, Any]:
    """
    Generate a trip itinerary based on user preferences.
    In a real app, this would call an AI service or database.
    """
    # Mock data for demonstration
    total_budget = int(budget)
    transportation_budget = int(total_budget * 0.4)
    food_budget = int(total_budget * 0.3)
    accommodation_budget = int(total_budget * 0.25)
    misc_budget = total_budget - transportation_budget - food_budget - accommodation_budget
    
    # Create a trip based on the inputs
    return {
        "trip_name": f"{origin} to {destination} {days} days trip with {people} people" + (f" to enjoy the {preferences}" if preferences else ""),
        "origin": origin,
        "destination": destination,
        "days": days,
        "budget": {
            "total": budget,
            "breakdown": {
                "transportation": str(transportation_budget),
                "food": str(food_budget),
                "accommodation": str(accommodation_budget),
                "miscellaneous": str(misc_budget)
            }
        },
        "people": people,
        "preferences": preferences,
        "tripType": trip_type,
        "journeyDate": journey_date,
        "travelClass": travel_class,
        "checkpoints": [
            {
                "origin": {
                    "location": origin,
                    "latitude": "23.8103" if origin.lower() == "dhaka" else "24.1233",
                    "longitude": "90.4125" if origin.lower() == "dhaka" else "90.5678"
                },
                "destination": {
                    "location": destination,
                    "latitude": "24.8949" if destination.lower() == "sylhet" else "23.9876",
                    "longitude": "91.8687" if destination.lower() == "sylhet" else "91.4567"
                },
                "logistics": {
                    "departure_time": "06:00 AM",
                    "arrival_time": "12:00 PM",
                    "tips": f"Take an early morning bus from {origin} to {destination} to enjoy the scenic beauty along the way."
                }
            }
        ],
        "food": {
            "1": {
                "breakfast": {
                    "title": "Panshi Restaurant",
                    "address": "Jallarpar Rd, Sylhet 3100",
                    "latitude": 24.895068799999997,
                    "longitude": 91.8674443,
                    "rating": 4.2,
                    "ratingCount": 18000,
                    "category": "Bangladeshi restaurant",
                    "phoneNumber": "01761-152939",
                    "cid": "4184260984599101480",
                    "cost": "150"
                },
                "launch": {
                    "title": "Pach Bhai Restaurant",
                    "address": "Jallarpar Rd, Sylhet 3100",
                    "latitude": 24.8946981,
                    "longitude": 91.8664029,
                    "rating": 4.3,
                    "ratingCount": 16000,
                    "category": "Bangladeshi restaurant",
                    "phoneNumber": "01710-459607",
                    "cid": "1251724275242512479",
                    "cost": "200"
                },
                "dinner": {
                    "title": "The Mad Grill",
                    "address": "Nayasarak Point, Manik Pir Road, 3100",
                    "latitude": 24.8995748,
                    "longitude": 91.87515789999999,
                    "rating": 4.3,
                    "ratingCount": 2300,
                    "category": "Restaurant",
                    "phoneNumber": "01954-556677",
                    "website": "https://www.facebook.com/themadgrill/",
                    "cid": "9696671651361504064",
                    "cost": "250"
                }
            }
        },
        "accommodation": {
            "1": {
                "title": "The Grand Hotel",
                "address": "4th Floor, H. S. Tower, HS Tower 3rd Floor Waves -1 East, Waves-1 Dargah Gate, Sylhet 3100",
                "latitude": 24.901723,
                "longitude": 91.86977929999999,
                "rating": 4,
                "ratingCount": 564,
                "category": "Hotel",
                "phoneNumber": "01970-793366",
                "cid": "16335710689796874260"
            },
            "2": {
                "title": "Hotel Noorjahan Grand",
                "address": "Waves 1 Dargah Gate, Sylhet 3100",
                "latitude": 24.901979599999997,
                "longitude": 91.8696968,
                "rating": 4.2,
                "ratingCount": 2900,
                "category": "Hotel",
                "phoneNumber": "01930-111666",
                "website": "http://www.noorjahangrand.com/",
                "cid": "15253580246980481310"
            }
        },
        "weather": [
            {
                "date": "2024-10-24",
                "temperature": 28.5,
                "conditions": "Partly Cloudy",
                "humidity": 72,
                "wind_speed": 8.5,
                "precipitation_chance": 15.0
            },
            {
                "date": "2024-10-25",
                "temperature": 29.2,
                "conditions": "Sunny",
                "humidity": 70,
                "wind_speed": 7.2,
                "precipitation_chance": 5.0
            },
            {
                "date": "2024-10-26",
                "temperature": 27.8,
                "conditions": "Light Rain",
                "humidity": 85,
                "wind_speed": 10.5,
                "precipitation_chance": 60.0
            }
        ],
        "traffic": {
            "current": {
                "level": "MODERATE",
                "estimated_delay_minutes": 25,
                "congestion_points": ["Mohakhali Flyover", "Kuril Bishwa Road"],
                "best_departure_time": "05:30 AM"
            },
            "forecast": {
                "morning_rush": "HIGH",
                "evening_rush": "VERY_HIGH",
                "weekend_traffic": "MODERATE",
                "road_conditions": "Good with some construction near the destination"
            }
        }
    }

# ====================== Routers ======================

# Auth Router
auth_router = APIRouter(prefix="/v1/auth", tags=["Auth"])

@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, 
                 responses={
                     201: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "id": "b0e42fe7-31a0-4f2b-9b4e-87c5534d9fdf",
                                     "username": "newuser123",
                                     "email": "user@example.com",
                                     "full_name": "John Smith",
                                     "created_at": "2023-01-01T00:00:00"
                                 }
                             }
                         }
                     }
                 })
async def register(user_data: UserRegister = Body(
    ...,
    example={
        "email": "user@example.com",
        "username": "newuser123",
        "password": "securepassword123",
        "full_name": "John Smith"
    }
)):
    """
    Register a new user.
    """
    # This is just an example implementation
    return {
        "id": "b0e42fe7-31a0-4f2b-9b4e-87c5534d9fdf",
        "username": "newuser123",
        "email": "user@example.com",
        "full_name": "John Smith",
        "created_at": datetime.now()
    }

@auth_router.post("/login", response_model=Token,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                                     "token_type": "bearer"
                                 }
                             }
                         }
                     }
                 })
async def login(user_data: UserLogin = Body(
    ...,
    example={
        "email": "user@example.com",
        "password": "securepassword123"
    }
)):
    """
    Authenticate a user and provide access and refresh tokens.
    """
    # This is just an example implementation
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }

@auth_router.post("/forgot-password", status_code=status.HTTP_200_OK,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "message": "Password reset instructions sent to your email"
                                 }
                             }
                         }
                     }
                 })
async def forgot_password(forgot_pwd: ForgotPassword = Body(
    ...,
    example={
        "email": "user@example.com"
    }
)):
    """
    Send a password reset link to the user's email.
    """
    # This is just an example implementation
    return {"message": "Password reset instructions sent to your email"}

@auth_router.post("/reset-password", status_code=status.HTTP_200_OK,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "message": "Password has been reset successfully"
                                 }
                             }
                         }
                     }
                 })
async def reset_password(reset_pwd: ResetPassword = Body(
    ...,
    example={
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "new_password": "newSecurePassword123"
    }
)):
    """
    Reset a user's password using a valid reset token.
    """
    # This is just an example implementation
    return {"message": "Password has been reset successfully"}

# Group Router
group_router = APIRouter(prefix="/v1/groups", tags=["Groups"])

@group_router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED,
                 responses={
                     201: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "id": "1",
                                     "name": "Europe Summer Trip",
                                     "description": "Planning our summer adventure",
                                     "trip_id": "1",
                                     "members": ["user123", "user456"],
                                     "created_by": "user123",
                                     "created_at": "2023-01-01T00:00:00"
                                 }
                             }
                         }
                     }
                 })
async def create_group(group: GroupCreate = Body(
    ...,
    example={
        "name": "Europe Summer Trip",
        "description": "Planning our summer adventure",
        "trip_id": "1"
    }
)):
    """
    Create a new travel group for collaborative trip planning.
    """
    # This is just an example implementation
    new_group = {
        "id": "1",
        "name": "Europe Summer Trip",
        "description": "Planning our summer adventure",
        "trip_id": "1",
        "members": ["user123", "user456"],
        "created_by": "user123",
        "created_at": datetime.now()
    }
    
    return GroupResponse(**new_group)

@group_router.post("/{group_id}/invite", status_code=status.HTTP_200_OK,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "message": "Invitation sent to user@example.com"
                                 }
                             }
                         }
                     }
                 })
async def invite_to_group(
    group_id: str = Path(..., description="The ID of the group to send invites for", examples={"example": {"value": "123"}}),
    invite: GroupInvite = Body(
    ...,
    example={
        "email": "user@example.com",
        "message": "Join our group for an amazing trip!",
        "group_id": "123" 
    }
)):
    """
    Invite a user to join a travel group.
    """
    # This is just an example implementation
    return {"message": f"Invitation sent to user@example.com"}

@group_router.post("/{group_id}/join", status_code=status.HTTP_200_OK,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "message": "Successfully joined the group",
                                     "group_id": "123",
                                     "group_name": "Europe Summer Trip"
                                 }
                             }
                         }
                     }
                 })
async def join_group(
    group_id: str = Path(..., description="The ID of the group to join", examples={"example": {"value": "123"}}),
    current_user: Dict = Depends(get_current_user)
):
    """
    Join an existing travel group that you've been invited to.
    """
    # This is just an example implementation
    return {
        "message": "Successfully joined the group",
        "group_id": group_id,
        "group_name": "Europe Summer Trip"
    }

@group_router.get("", response_model=List[GroupResponse],
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": [
                                     {
                                         "id": "1",
                                         "name": "Europe Summer Trip",
                                         "description": "Planning our summer adventure",
                                         "trip_id": "1",
                                         "members": ["user123", "user456"],
                                         "created_by": "user123",
                                         "created_at": "2023-01-01T00:00:00"
                                     }
                                 ]
                             }
                         }
                     }
                 })
async def get_groups(
    user_id: Optional[str] = Query(None, description="Filter groups by user ID", examples={"example": {"value": "user123"}}),
    active_only: bool = Query(False, description="Show only active groups")
):
    """
    Get all groups the current user is a member of.
    """
    # This is just an example implementation
    group = {
        "id": "1",
        "name": "Europe Summer Trip",
        "description": "Planning our summer adventure",
        "trip_id": "1",
        "members": ["user123", "user456"],
        "created_by": "user123",
        "created_at": datetime.now()
    }
    
    return [GroupResponse(**group)]

# Blog Router
blog_router = APIRouter(prefix="/v1/blogs", tags=["Blogs"])

@blog_router.post("", response_model=BlogResponse, status_code=status.HTTP_201_CREATED,
                 responses={
                     201: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "id": "1",
                                     "title": "My Amazing Paris Adventure",
                                     "content": "# Paris Trip\n\nWhat an amazing time we had...",
                                     "trip_id": "1",
                                     "tags": ["paris", "france", "travel"],
                                     "is_public": True,
                                     "author_id": "user123",
                                     "created_at": "2023-01-01T00:00:00",
                                     "updated_at": "2023-01-01T00:00:00"
                                 }
                             }
                         }
                     }
                 })
async def create_blog(blog: BlogCreate = Body(
    ...,
    example={
        "title": "My Amazing Paris Adventure",
        "content": "# Paris Trip\n\nWhat an amazing time we had...",
        "trip_id": "1",
        "tags": ["paris", "france", "travel"],
        "is_public": True
    }
)):
    """
    Create a new blog post about your travel experiences.
    """
    # This is just an example implementation
    new_blog = {
        "id": "1",
        "title": "My Amazing Paris Adventure",
        "content": "# Paris Trip\n\nWhat an amazing time we had...",
        "trip_id": "1",
        "tags": ["paris", "france", "travel"],
        "is_public": True,
        "author_id": "user123",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    return BlogResponse(**new_blog)

@blog_router.get("", response_model=List[BlogResponse],
                responses={
                    200: {
                        "content": {
                            "application/json": {
                                "example": [
                                    {
                                        "id": "1",
                                        "title": "My Amazing Paris Adventure",
                                        "content": "# Paris Trip\n\nWhat an amazing time we had...",
                                        "trip_id": "1",
                                        "tags": ["paris", "france", "travel"],
                                        "is_public": True,
                                        "author_id": "user123",
                                        "created_at": "2023-01-01T00:00:00",
                                        "updated_at": "2023-01-01T00:00:00"
                                    }
                                ]
                            }
                        }
                    }
                })
async def get_blogs(
    author_id: Optional[str] = Query(None, description="Filter blogs by author ID", examples={"example": {"value": "user123"}}),
    trip_id: Optional[str] = Query(None, description="Filter blogs by trip ID", examples={"example": {"value": "trip001"}}),
    tag: Optional[str] = Query(None, description="Filter blogs by tag", examples={"example": {"value": "paris"}}),
    limit: int = Query(10, description="Maximum number of blogs to return", ge=1, le=100)
):
    """
    Get a list of blog posts.
    """
    # This is just an example implementation
    blog = {
        "id": "1",
        "title": "My Amazing Paris Adventure",
        "content": "# Paris Trip\n\nWhat an amazing time we had...",
        "trip_id": "1",
        "tags": ["paris", "france", "travel"],
        "is_public": True,
        "author_id": "user123",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    return [BlogResponse(**blog)]

# Weather Router
weather_router = APIRouter(prefix="/v1/weather", tags=["Weather"])

@weather_router.get("/forecast/{trip_id}", response_model=List[WeatherData],
                  responses={
                      200: {
                          "content": {
                              "application/json": {
                                  "example": [
                                      {
                                          "location": {
                                              "city": "Paris",
                                              "country": "France",
                                              "latitude": 48.8566,
                                              "longitude": 2.3522
                                          },
                                          "date": "2025-06-01",
                                          "temperature": 22.5,
                                          "conditions": "Partly Cloudy",
                                          "humidity": 65,
                                          "wind_speed": 12.0,
                                          "precipitation_chance": 20.0
                                      }
                                  ]
                              }
                          }
                      }
                  })
async def get_weather_forecast(
    trip_id: str = Path(..., description="ID of the trip to get weather forecast for", examples={"example": {"value": "trip123"}})
):
    """
    Get weather forecast for a trip's destination and dates.
    """
    # This is just an example implementation
    weather = {
        "location": {"city": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522},
        "date": date(2025, 6, 1),
        "temperature": 22.5,
        "conditions": "Partly Cloudy",
        "humidity": 65,
        "wind_speed": 12.0,
        "precipitation_chance": 20.0
    }
    
    return [WeatherData(**weather)]

@weather_router.post("/check", response_model=WeatherCheckResponse,
                   responses={
                       200: {
                           "content": {
                               "application/json": {
                                   "example": {
                                       "message": "Severe weather alert detected. Trip update suggested.",
                                       "severe_weather_days": [
                                           {
                                               "date": "2025-05-11",
                                               "condition": "Typhoon",
                                               "risk_level": "High",
                                               "reason": "Strong winds and potential flooding"
                                           }
                                       ],
                                       "recommended_actions": [
                                           "Postpone trip to start from 2025-05-17",
                                           "Or change destination to Chiang Mai"
                                       ],
                                       "proposed_itinerary_change": {
                                           "new_start_date": "2025-05-17",
                                           "new_end_date": "2025-05-22",
                                           "new_destination": "Chiang Mai"
                                       },
                                       "user_decision_required": True
                                   }
                               }
                           }
                       }
                   })
async def check_weather_conditions(request: WeatherCheckRequest = Body(
    ...,
    example={
        "trip_id": "abc123",
        "destination": "Bangkok",
        "start_date": "2025-05-10",
        "end_date": "2025-05-15"
    }
)):
    """
    Check for severe weather conditions that might affect trip plans.
    """
    # This is just an example implementation
    response = {
        "message": "Severe weather alert detected. Trip update suggested.",
        "severe_weather_days": [
            {
                "date": date(2025, 5, 11),
                "condition": "Typhoon",
                "risk_level": "High",
                "reason": "Strong winds and potential flooding"
            }
        ],
        "recommended_actions": [
            "Postpone trip to start from 2025-05-17",
            "Or change destination to Chiang Mai"
        ],
        "proposed_itinerary_change": {
            "new_start_date": date(2025, 5, 17),
            "new_end_date": date(2025, 5, 22),
            "new_destination": "Chiang Mai"
        },
        "user_decision_required": True
    }
    
    return WeatherCheckResponse(**response)
    """
    Checks weather forecasts and, in case of severe conditions, suggests changing trip dates or destinations.
    """
    # This is just an example implementation
    return {
        "message": "Severe weather alert detected. Trip update suggested.",
        "severe_weather_days": [
            {
                "date": date(2025, 5, 11),
                "condition": "Typhoon",
                "risk_level": "High",
                "reason": "Strong winds and potential flooding"
            }
        ],
        "recommended_actions": [
            "Postpone trip to start from 2025-05-17",
            "Or change destination to Chiang Mai"
        ],
        "proposed_itinerary_change": {
            "new_start_date": date(2025, 5, 17),
            "new_end_date": date(2025, 5, 22),
            "new_destination": "Chiang Mai"
        },
        "user_decision_required": True
    }

@weather_router.post("/trip/confirm-change", response_model=TripChangeResponse,
                   responses={
                       200: {
                           "content": {
                               "application/json": {
                                   "example": {
                                       "message": "Trip updated successfully",
                                       "trip_id": "abc123",
                                       "new_itinerary": {
                                           "start_date": "2025-05-17",
                                           "end_date": "2025-05-22",
                                           "destination": "Chiang Mai"
                                       }
                                   }
                               }
                           }
                       }
                   })
async def confirm_trip_change(request: TripChangeRequest = Body(
    ...,
    example={
        "trip_id": "abc123",
        "confirm": True,
        "new_start_date": "2025-05-17",
        "new_destination": "Chiang Mai"
    }
)):
    """
    Endpoint for users to accept the weather-based trip change suggestion.
    """
    # This is just an example implementation
    return {
        "message": "Trip updated successfully",
        "trip_id": "abc123",
        "new_itinerary": {
            "start_date": date(2025, 5, 17),
            "end_date": date(2025, 5, 22),
            "destination": "Chiang Mai"
        }
    }

# Traffic Router
traffic_router = APIRouter(prefix="/v1/traffic", tags=["Traffic"])

@traffic_router.get("/info/{trip_id}", response_model=TrafficInfo,
                  responses={
                      200: {
                          "content": {
                              "application/json": {
                                  "example": {
                                      "origin": {
                                          "city": "Paris",
                                          "country": "France",
                                          "latitude": 48.8566,
                                          "longitude": 2.3522
                                      },
                                      "destination": {
                                          "city": "Versailles",
                                          "country": "France",
                                          "latitude": 48.8044,
                                          "longitude": 2.1232
                                      },
                                      "date": "2025-06-01",
                                      "time": "09:00",
                                      "traffic_level": "MODERATE",
                                      "estimated_delay_minutes": 15,
                                      "alternative_routes": ["Via A13", "Via N118"]
                                  }
                              }
                          }
                      }
                  })
async def get_traffic_info(
    trip_id: str = Path(..., description="ID of the trip to get traffic information for", examples={"example": {"value": "trip123"}})
):
    """
    Get traffic information for a trip's route.
    """
    # This is just an example implementation
    traffic_info = {
        "origin": {"city": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522},
        "destination": {"city": "Versailles", "country": "France", "latitude": 48.8044, "longitude": 2.1232},
        "date": date(2025, 6, 1),
        "time": "09:00",
        "traffic_level": TrafficLevel.MODERATE,
        "estimated_delay_minutes": 15,
        "alternative_routes": ["Via A13", "Via N118"]
    }
    
    return TrafficInfo(**traffic_info)

# Trip Plan Router
trip_plan_router = APIRouter(prefix="/v1/tripPlan", tags=["TripPlan"])

@trip_plan_router.get("/extract", response_model=TripPlanExtractResponse, 
                     summary="Extract trip details from text",
                     responses={
                         200: {
                             "content": {
                                 "application/json": {
                                     "example": {
                                         "output": {
                                             "origin": "Dhaka",
                                             "destination": "Sylhet",
                                             "days": "4",
                                             "budget": "5000",
                                             "people": "4",
                                             "preferences": "",
                                             "tripType": "oneWay",
                                             "journeyDate": "today",
                                             "travelClass": "economy"
                                         },
                                         "metadata": {
                                             "run_id": "3e2d0a89-be92-45ef-8e10-1d64f7bd24ec",
                                             "feedback_tokens": []
                                         }
                                     }
                                 }
                             }
                         }
                     })
async def extract_trip_plan(
    text: str = Query(..., description="Natural language text describing trip plans", 
                    examples={"example": {"value": "journey from dhaka to sylhet with 3 friends 4 days budget 5k"}})
):
    """
    Extract structured trip information from natural language description.
    """
    # This is just an example implementation
    return {
        "output": {
            "origin": "Dhaka",
            "destination": "Sylhet",
            "days": "4",
            "budget": "5000",
            "people": "4",
            "preferences": "",
            "tripType": "oneWay",
            "journeyDate": "today",
            "travelClass": "economy"
        },
        "metadata": {
            "run_id": "3e2d0a89-be92-45ef-8e10-1d64f7bd24ec",
            "feedback_tokens": []
        }
    }

@trip_plan_router.get("", response_model=TripPlanResponse,
                    responses={
                        200: {
                            "content": {
                                "application/json": {
                                    "example": {
                                        "output": {
                                            "trip_name": "Dhaka to Sylhet 3 days trip with 4 people to enjoy the hill",
                                            "origin": "Dhaka",
                                            "destination": "Sylhet",
                                            "days": "3",
                                            "budget": {
                                                "total": "2000",
                                                "breakdown": {
                                                    "transportation": "800",
                                                    "food": "600",
                                                    "accommodation": "500",
                                                    "miscellaneous": "100"
                                                }
                                            },
                                            "people": "4",
                                            "preferences": "hill",
                                            "tripType": "oneWay",
                                            "journeyDate": "24/10/2024",
                                            "travelClass": "economy",
                                            "checkpoints": [
                                                {
                                                    "origin": {
                                                        "location": "Dhaka",
                                                        "latitude": "23.8103",
                                                        "longitude": "90.4125"
                                                    },
                                                    "destination": {
                                                        "location": "Sylhet",
                                                        "latitude": "24.8949",
                                                        "longitude": "91.8687"
                                                    },
                                                    "logistics": {
                                                        "departure_time": "06:00 AM",
                                                        "arrival_time": "12:00 PM",
                                                        "tips": "Take an early morning bus from Dhaka to Sylhet to enjoy the scenic beauty along the way."
                                                    }
                                                }
                                            ],
                                            "food": {
                                                "1": {
                                                    "breakfast": {
                                                        "title": "Panshi Restaurant",
                                                        "address": "Jallarpar Rd, Sylhet 3100",
                                                        "latitude": 24.895068799999997,
                                                        "longitude": 91.8674443,
                                                        "rating": 4.2,
                                                        "ratingCount": 18000,
                                                        "category": "Bangladeshi restaurant",
                                                        "phoneNumber": "01761-152939",
                                                        "cid": "4184260984599101480",
                                                        "cost": "150"
                                                    },
                                                    "launch": {
                                                        "title": "Pach Bhai Restaurant",
                                                        "address": "Jallarpar Rd, Sylhet 3100",
                                                        "latitude": 24.8946981,
                                                        "longitude": 91.8664029,
                                                        "rating": 4.3,
                                                        "ratingCount": 16000,
                                                        "category": "Bangladeshi restaurant",
                                                        "phoneNumber": "01710-459607",
                                                        "cid": "1251724275242512479",
                                                        "cost": "200"
                                                    },
                                                    "dinner": {
                                                        "title": "The Mad Grill",
                                                        "address": "Nayasarak Point, Manik Pir Road, 3100",
                                                        "latitude": 24.8995748,
                                                        "longitude": 91.87515789999999,
                                                        "rating": 4.3,
                                                        "ratingCount": 2300,
                                                        "category": "Restaurant",
                                                        "phoneNumber": "01954-556677",
                                                        "website": "https://www.facebook.com/themadgrill/",
                                                        "cid": "9696671651361504064",
                                                        "cost": "250"
                                                    }
                                                }
                                            },
                                            "accommodation": {
                                                "1": {
                                                    "title": "The Grand Hotel",
                                                    "address": "4th Floor, H. S. Tower, HS Tower 3rd Floor Waves -1 East, Waves-1 Dargah Gate, Sylhet 3100",
                                                    "latitude": 24.901723,
                                                    "longitude": 91.86977929999999,
                                                    "rating": 4,
                                                    "ratingCount": 564,
                                                    "category": "Hotel",
                                                    "phoneNumber": "01970-793366",
                                                    "cid": "16335710689796874260"
                                                },
                                                "2": {
                                                    "title": "Hotel Noorjahan Grand",
                                                    "address": "Waves 1 Dargah Gate, Sylhet 3100",
                                                    "latitude": 24.901979599999997,
                                                    "longitude": 91.8696968,
                                                    "rating": 4.2,
                                                    "ratingCount": 2900,
                                                    "category": "Hotel",
                                                    "phoneNumber": "01930-111666",
                                                    "website": "http://www.noorjahangrand.com/",
                                                    "cid": "15253580246980481310"
                                                }
                                            },
                                            "weather": [
                                                {
                                                    "date": "2024-10-24",
                                                    "temperature": 28.5,
                                                    "conditions": "Partly Cloudy",
                                                    "humidity": 72,
                                                    "wind_speed": 8.5,
                                                    "precipitation_chance": 15.0
                                                },
                                                {
                                                    "date": "2024-10-25",
                                                    "temperature": 29.2,
                                                    "conditions": "Sunny",
                                                    "humidity": 70,
                                                    "wind_speed": 7.2,
                                                    "precipitation_chance": 5.0
                                                },
                                                {
                                                    "date": "2024-10-26",
                                                    "temperature": 27.8,
                                                    "conditions": "Light Rain",
                                                    "humidity": 85,
                                                    "wind_speed": 10.5,
                                                    "precipitation_chance": 60.0
                                                }
                                            ],
                                            "traffic": {
                                                "current": {
                                                    "level": "MODERATE",
                                                    "estimated_delay_minutes": 25,
                                                    "congestion_points": ["Mohakhali Flyover", "Kuril Bishwa Road"],
                                                    "best_departure_time": "05:30 AM"
                                                },
                                                "forecast": {
                                                    "morning_rush": "HIGH",
                                                    "evening_rush": "VERY_HIGH",
                                                    "weekend_traffic": "MODERATE",
                                                    "road_conditions": "Good with some construction near the destination"
                                                }
                                            },
                                            "spotSuggestions": [
                                                {
                                                    "name": "Ratargul Swamp Forest",
                                                    "description": "A freshwater swamp forest famous for boat rides through submerged trees.",
                                                    "latitude": 25.0056,
                                                    "longitude": 91.9583,
                                                    "recommendedTime": "Morning",
                                                    "estimatedDurationHours": 3
                                                },
                                                {
                                                    "name": "Jaflong",
                                                    "description": "A scenic border area with hills, rivers, and stone collection activities.",
                                                    "latitude": 25.1597,
                                                    "longitude": 92.0216,
                                                    "recommendedTime": "Afternoon",
                                                    "estimatedDurationHours": 4
                                                },
                                                {
                                                    "name": "Bisnakandi",
                                                    "description": "A beautiful spot where several streams from Meghalaya converge.",
                                                    "latitude": 25.2282,
                                                    "longitude": 92.0078,
                                                    "recommendedTime": "Morning or Early Afternoon",
                                                    "estimatedDurationHours": 3
                                                },
                                                {
                                                    "name": "Hazrat Shah Jalal Mazar",
                                                    "description": "A historical and religious shrine in the heart of Sylhet.",
                                                    "latitude": 24.8992,
                                                    "longitude": 91.8701,
                                                    "recommendedTime": "Evening",
                                                    "estimatedDurationHours": 1
                                                }
                                            ]
                                        },
                                        "metadata": {
                                            "run_id": "6fff0355-b8e0-47c9-9776-40664d30d169",
                                            "feedback_tokens": []
                                        }
                                    }
                                }
                            }
                        }
                    })
async def generate_trip_plan(
    origin: str = Query(None, description="Starting location", examples={"example": {"value": "Dhaka"}}),
    destination: str = Query(None, description="Destination location", examples={"example": {"value": "Sylhet"}}),
    start_date: Optional[date] = Query(None, description="Trip start date", examples={"example": {"value": "2024-10-24"}}),
    days: Optional[int] = Query(None, description="Trip duration in days", examples={"example": {"value": 3}}, ge=1, le=30),
    budget: Optional[float] = Query(None, description="Trip budget", examples={"example": {"value": 5000.0}}, ge=0),
    people: Optional[int] = Query(None, description="Number of travelers", examples={"example": {"value": 4}}, ge=1)
):
    """
    Generate a complete trip itinerary based on user preferences.
    """
    # This is just an example implementation
    return {
        "output": {
            "trip_name": "Dhaka to Sylhet 3 days trip with 4 people to enjoy the hill",
            "origin": "Dhaka",
            "destination": "Sylhet",
            "days": "3",
            "budget": {
                "total": "2000",
                "breakdown": {
                    "transportation": "800",
                    "food": "600",
                    "accommodation": "500",
                    "miscellaneous": "100"
                }
            },
            "people": "4",
            "preferences": "hill",
            "tripType": "oneWay",
            "journeyDate": "24/10/2024",
            "travelClass": "economy",
            # Additional output fields truncated for brevity
        },
        "metadata": {
            "run_id": "6fff0355-b8e0-47c9-9776-40664d30d169",
            "feedback_tokens": []
        }
    }





# Profile Router
profile_router = APIRouter(prefix="/v1/profile", tags=["Profile"])

@profile_router.get("", response_model=UserProfile,
                  responses={
                      200: {
                          "content": {
                              "application/json": {
                                  "example": {
                                      "userId": "u123",
                                      "name": "John Doe",
                                      "email": "john@example.com",
                                      "currentTrip": {
                                          "tripId": "t001",
                                          "tripName": "Dhaka to Sylhet Adventure",
                                          "startDate": "2024-10-24",
                                          "days": 4,
                                          "people": 3,
                                          "budget": 5000,
                                          "status": "active"
                                      },
                                      "pastTrips": [
                                          {
                                              "tripId": "t000",
                                              "tripName": "Cox's Bazar Getaway",
                                              "startDate": "2023-12-10",
                                              "days": 3,
                                              "people": 2,
                                              "budget": 7000,
                                              "status": "completed"
                                          }
                                      ]
                                  }
                              }
                          }
                      }
                  })
async def get_user_profile(
    user_id: Optional[str] = Query(None, description="User ID to fetch profile for (defaults to authenticated user)", examples={"example": {"value": "u123"}})
):
    """
    Get the user's profile information including current and past trips.
    """
    # This is just an example implementation
    return {
        "userId": "u123",
        "name": "John Doe",
        "email": "john@example.com",
        "currentTrip": {
            "tripId": "t001",
            "tripName": "Dhaka to Sylhet Adventure",
            "startDate": date(2024, 10, 24),
            "days": 4,
            "people": 3,
            "budget": 5000,
            "status": "active"
        },
        "pastTrips": [
            {
                "tripId": "t000",
                "tripName": "Cox's Bazar Getaway",
                "startDate": date(2023, 12, 10),
                "days": 3,
                "people": 2,
                "budget": 7000,
                "status": "completed"
            }
        ]
    }

@profile_router.get("/trips/{trip_id}", response_model=TripDetails,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "tripId": "t001",
                                     "tripName": "Dhaka to Sylhet Adventure",
                                     "startDate": "2024-10-24",
                                     "status": "active",
                                     "days": 4,
                                     "budget": 5000,
                                     "people": 3,
                                     "placesVisited": [
                                         "Lalakhal",
                                         "Bisnakandi"
                                     ],
                                     "placesLeft": [
                                         "Ratargul Swamp Forest",
                                         "Jaflong",
                                         "Shahjalal Dargah"
                                     ]
                                 }
                             }
                         }
                     }
                 })
async def get_trip_details(
    trip_id: str = Path(..., description="ID of the trip to get details for", examples={"example": {"value": "t001"}})
):
    """
    Get detailed information about a specific trip, including todo list.
    """
    # This is just an example implementation
    return {
        "tripId": "t001",
        "tripName": "Dhaka to Sylhet Adventure",
        "startDate": date(2024, 10, 24),
        "status": "active",
        "days": 4,
        "budget": 5000,
        "people": 3,
        "placesVisited": [
            "Lalakhal",
            "Bisnakandi"
        ],
        "placesLeft": [
            "Ratargul Swamp Forest",
            "Jaflong",
            "Shahjalal Dargah"
        ]
    }

@profile_router.put("/trips/{trip_id}/todolist/visit", response_model=PlaceUpdateResponse,
                  responses={
                      200: {
                          "content": {
                              "application/json": {
                                  "example": {
                                      "message": "Marked 'Ratargul Swamp Forest' as visited.",
                                      "placesVisited": [
                                          "Lalakhal",
                                          "Bisnakandi",
                                          "Ratargul Swamp Forest"
                                      ],
                                      "placesLeft": [
                                          "Jaflong",
                                          "Shahjalal Dargah"
                                      ]
                                  }
                              }
                          }
                      }
                  })
async def mark_place_visited(
    trip_id: str = Path(..., description="ID of the trip to update", examples={"example": {"value": "t001"}}),
    place_update: PlaceUpdateRequest = Body(
    ...,
    examples={
        "example": {
            "summary": "Mark place as visited",
            "value": {
                "place": "Ratargul Swamp Forest"
            }
        }
    }
)):
    """
    Mark a place as visited in the trip's todo list.
    """
    # This is just an example implementation
    return {
        "message": f"Marked '{place_update.place}' as visited.",
        "placesVisited": [
            "Lalakhal",
            "Bisnakandi",
            "Ratargul Swamp Forest"
        ],
        "placesLeft": [
            "Jaflong",
            "Shahjalal Dargah"
        ]
    }

@profile_router.post("/trips/{trip_id}/todolist", response_model=AddPlaceResponse,
                   responses={
                       200: {
                           "content": {
                               "application/json": {
                                   "example": {
                                       "message": "Place added to to-do list.",
                                       "placesLeft": [
                                           "Jaflong",
                                           "Shahjalal Dargah",
                                           "Sreemangal Tea Garden"
                                       ]
                                   }
                               }
                           }
                       }
                   })
async def add_place_to_todolist(
    trip_id: str = Path(..., description="ID of the trip to add a place to", example="t001"),
    place_update: PlaceUpdateRequest = Body(
    ...,
    example={
        "place": "Sreemangal Tea Garden"
    }
)):
    """
    Add a new place to the trip's todo list.
    """
    # This is just an example implementation
    return {
        "message": "Place added to to-do list.",
        "placesLeft": [
            "Jaflong",
            "Shahjalal Dargah",
            "Sreemangal Tea Garden"
        ]
    }

# Home Router
home_router = APIRouter(prefix="/v1/home", tags=["Home"])

@home_router.get("", response_model=HomeResponse,
                responses={
                    200: {
                        "content": {
                            "application/json": {
                                "example": {
                                    "featured_trips": [
                                        {
                                            "id": "1",
                                            "title": "Paris Getaway",
                                            "image_url": "https://example.com/images/paris.jpg",
                                            "description": "Experience the city of lights",
                                            "days": 3,
                                            "avg_rating": 4.8
                                        }
                                    ],
                                    "banners": [
                                        {
                                            "id": "1",
                                            "image_url": "https://example.com/images/banner1.jpg",
                                            "title": "Summer Sale",
                                            "description": "Get 20% off on all summer trips",
                                            "link": "/promotions/summer"
                                        }
                                    ],
                                    "testimonials": [
                                        {
                                            "id": "1",
                                            "name": "John Smith",
                                            "photo_url": "https://example.com/images/john.jpg",
                                            "content": "WanderWise made our trip planning so easy!",
                                            "rating": 5.0
                                        }
                                    ]
                                }
                            }
                        }
                    }
                })
async def get_homepage():
    """
    Get homepage information including featured trips, banners, and testimonials.
    """
    # This is just an example implementation
    return {
        "featured_trips": [
            {
                "id": "1",
                "title": "Paris Getaway",
                "image_url": "https://example.com/images/paris.jpg",
                "description": "Experience the city of lights",
                "days": 3,
                "avg_rating": 4.8
            }
        ],
        "banners": [
            {
                "id": "1",
                "image_url": "https://example.com/images/banner1.jpg",
                "title": "Summer Sale",
                "description": "Get 20% off on all summer trips",
                "link": "/promotions/summer"
            }
        ],
        "testimonials": [
            {
                "id": "1",
                "name": "John Smith",
                "photo_url": "https://example.com/images/john.jpg",
                "content": "WanderWise made our trip planning so easy!",
                "rating": 5.0
            }
        ]
    }

# About Router
about_router = APIRouter(prefix="/v1/about", tags=["About"])

@about_router.get("", response_model=AboutResponse,
                 responses={
                     200: {
                         "content": {
                             "application/json": {
                                 "example": {
                                     "title": "About WanderWise",
                                     "content": "We help travelers plan smart..."
                                 }
                             }
                         }
                     }
                 })
async def get_about():
    """
    Get information about the company/platform.
    """
    # This is just an example implementation
    return {
        "title": "About WanderWise",
        "content": "We help travelers plan smart, personalized trips with our AI-powered platform. Founded in 2023, WanderWise combines advanced technology with local expertise to create unforgettable travel experiences."
    }







# Register all routers
app.include_router(auth_router)
app.include_router(group_router)
app.include_router(blog_router)
app.include_router(weather_router)
app.include_router(traffic_router)
app.include_router(trip_plan_router)
app.include_router(profile_router)
app.include_router(home_router)
app.include_router(about_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)