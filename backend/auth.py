"""
Authentication utilities for Clerk JWT verification
"""
import jwt
import requests
from typing import Optional
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from functools import lru_cache
import os

security = HTTPBearer()

# Clerk configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")

# Extract issuer from publishable key (format: pk_test_xxxxx or pk_live_xxxxx)
if CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
    CLERK_ISSUER = f"https://clerk.{CLERK_PUBLISHABLE_KEY.split('_')[2]}.lcl.dev"
else:
    # For production, extract domain from publishable key
    CLERK_ISSUER = "https://clerk.com"  # Update this based on your Clerk domain


@lru_cache()
def get_clerk_jwks():
    """Fetch Clerk's JWKS (JSON Web Key Set) for token verification"""
    try:
        # Clerk's JWKS endpoint
        jwks_url = f"{CLERK_ISSUER}/.well-known/jwks.json"
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching JWKS: {e}")
        return None


def verify_clerk_token(token: str) -> dict:
    """
    Verify Clerk JWT token and return decoded payload
    
    Args:
        token: JWT token from Clerk
        
    Returns:
        dict: Decoded token payload containing user information
        
    Raises:
        HTTPException: If token is invalid or verification fails
    """
    try:
        # For development: If using secret key directly
        if CLERK_SECRET_KEY:
            # Decode without verification for development
            # In production, you should verify with JWKS
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # For development only
            )
            return decoded
        
        # Production: Verify with JWKS
        jwks = get_clerk_jwks()
        if not jwks:
            raise HTTPException(status_code=500, detail="Could not fetch JWKS")
        
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        # Find the matching key
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break
        
        if not key:
            raise HTTPException(status_code=401, detail="Invalid token key")
        
        # Verify and decode token
        decoded = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=CLERK_ISSUER
        )
        
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token verification failed: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> dict:
    """
    FastAPI dependency to get current authenticated user from JWT token
    
    Returns:
        dict: User information from token including clerk_user_id (as 'sub')
    """
    token = credentials.credentials
    user_data = verify_clerk_token(token)
    
    # Clerk tokens have 'sub' field as the user ID
    if "sub" not in user_data:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    return user_data


def get_user_id_from_token(user_data: dict) -> str:
    """
    Extract Clerk user ID from decoded token
    
    Args:
        user_data: Decoded JWT token payload
        
    Returns:
        str: Clerk user ID
    """
    return user_data.get("sub")
