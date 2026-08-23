"""
User and RefreshToken ORM models -- the auth slice of the schema.

Design choices worth knowing about:

- Passwords are NEVER stored -- only password_hash (Argon2id, see
  api/security.py). A user who only ever signs in via Google has
  password_hash = NULL, which is why it's nullable, not empty-string:
  NULL means "no password auth for this account" unambiguously,
  whereas an empty string could be mistaken for an unset-but-valid hash.

- RefreshToken stores a HASH of the token, not the token itself. If the
  database were ever read (backup leak, injection, insider access), the
  attacker gets hashes they can't use to log in -- same reasoning as
  password storage, applied to refresh tokens too. The actual token
  value only ever exists in memory and in the user's httpOnly cookie.

- RefreshToken has revoked_at and replaced_by_id for rotation: every
  refresh issues a NEW refresh token and immediately revokes the old
  one (see api/routes/auth.py). If a revoked token is ever presented
  again, that's a signal the old token leaked -- the whole token
  family gets revoked, not just the one token. This is the standard
  "refresh token rotation with reuse detection" pattern, not something
  invented for this project.
"""
import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # NULL = Google-only account, see docstring
    google_sub = Column(String, unique=True, nullable=True, index=True)  # Google's stable user ID
    display_name = Column(String, nullable=True)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)  # see docstring -- never the raw token
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(String, nullable=True)  # points at the token that rotated this one out

    user = relationship("User", back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.datetime.utcnow()


class EmailVerificationToken(Base):
    """
    Short-lived token emailed to a user to confirm their address. Same
    hash-at-rest reasoning as RefreshToken: store the hash, not the
    token, so a DB read alone can't be used to verify arbitrary emails.
    """
    __tablename__ = "email_verification_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)
