"""
Pydantic schemas for the auth API. Kept separate from db/models.py on
purpose: an ORM model and an API schema look similar but answer
different questions (what does the DB store vs. what should a client
see/send), and they should be free to diverge -- e.g. UserOut below
deliberately excludes password_hash and google_sub.
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        # Normalize at the SCHEMA level so every route gets it for free
        # and none can forget. Without this, 'Dor@x.com' and 'dor@x.com'
        # created two separate accounts (the DB unique constraint is
        # case-sensitive), and logging in with different casing than you
        # registered with silently failed with "incorrect email or
        # password". Mail domains are case-insensitive in practice and
        # every major provider treats them that way.
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        # Length over complexity rules: NIST SP 800-63B explicitly
        # recommends against forced complexity (mandatory uppercase/
        # digit/symbol) in favor of minimum length, since complexity
        # rules push people toward predictable patterns ("Password1!")
        # more than they push toward real entropy.
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        # Must match RegisterRequest's normalization exactly, or a user
        # who registered as 'dor@x.com' couldn't log in as 'Dor@x.com'.
        return v.strip().lower()


class UserOut(BaseModel):
    id: str
    email: str
    display_name: Optional[str]
    is_email_verified: bool

    class Config:
        from_attributes = True  # lets this build directly from a User ORM instance


class AuthResponse(BaseModel):
    """
    Returned by register/login/refresh. Both tokens travel in the JSON
    body, not a cookie -- see routes/auth.py's module docstring for why
    (a cross-site cookie between the two onrender.com subdomains is
    silently blocked by an increasing number of browsers, regardless of
    SameSite). The client is responsible for holding access_token in
    memory and refresh_token in its own persistent storage, and
    attaching access_token as an Authorization: Bearer header itself.
    """
    user: UserOut
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str
