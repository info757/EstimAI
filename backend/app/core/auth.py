"""
Authentication helpers for EstimAI backend.

Provides JWT token creation, decoding, and user authentication utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError

from .config import get_settings

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = HTTPBearer()

# Demo users for development/testing
DEMO_USERS = {
    "demo@example.com": {
        "password": "demo123",
        "name": "Demo User",
        "scopes": ["read", "write"]
    }
}


def create_access_token(data: dict, expires_minutes: int = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing the data to encode in the token
        expires_minutes: Token expiration time in minutes (defaults to config value)
    
    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    
    if expires_minutes is None:
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # Create expiration time
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    
    # Prepare token data
    to_encode = data.copy()
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    # Encode token
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET, 
        algorithm=settings.JWT_ALG
    )
    
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
    
    Returns:
        Decoded token payload as dictionary
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()
    
    try:
        # Decode token
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET, 
            algorithms=[settings.JWT_ALG]
        )
        
        # Check if token has expired
        if "exp" in payload:
            exp_timestamp = payload["exp"]
            current_timestamp = datetime.now(timezone.utc).timestamp()
            if current_timestamp > exp_timestamp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        return payload
        
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)
) -> dict:
    """
    Get the current authenticated user from the JWT token.
    
    Args:
        credentials: HTTP authorization credentials from the request
    
    Returns:
        Dictionary containing user information (sub, scopes, etc.)
    
    Raises:
        HTTPException: If token is invalid or user not found
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode the token
    payload = decode_token(credentials.credentials)
    
    # Extract user information
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Return user information
    return {
        "sub": username,
        "scopes": payload.get("scopes", []),
        "exp": payload.get("exp"),
        "iat": payload.get("iat")
    }


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: User's email/username
        password: User's password
    
    Returns:
        User information dictionary if authentication succeeds, None otherwise
    """
    if username in DEMO_USERS:
        user = DEMO_USERS[username]
        if user["password"] == password:
            return {
                "username": username,
                "name": user["name"],
                "scopes": user["scopes"]
            }
    
    return None


def create_user_token(username: str, scopes: list = None) -> str:
    """
    Create an access token for a user.
    
    Args:
        username: User's email/username
        scopes: List of user scopes/permissions
    
    Returns:
        JWT access token string
    """
    if scopes is None:
        scopes = ["read"]  # Default scope
    
    token_data = {
        "sub": username,
        "scopes": scopes,
        "type": "access"
    }
    
    return create_access_token(token_data)
