"""
Authentication routes for EstimAI backend.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..core.auth import authenticate_user, create_user_token

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""
    token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse, summary="Authenticate user and get JWT token")
async def login(request: LoginRequest):
    """
    Authenticate a user with username and password.
    
    Returns a JWT token for authenticated requests.
    """
    # Authenticate user
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    token = create_user_token(user["username"], user["scopes"])
    
    # Return response
    return LoginResponse(
        token=token,
        user={
            "email": user["username"],
            "name": user["name"]
        }
    )
