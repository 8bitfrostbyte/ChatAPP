"""
Authentication module for user registration and login.
"""

import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from database import User, Session as DBSession
from pydantic import BaseModel


class UserRegisterRequest(BaseModel):
    username: str
    password: str


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse


class AuthManager:
    """Handles user authentication, registration, and session management."""
    
    SESSION_DURATION = timedelta(hours=24)  # Sessions expire after 24 hours
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    
    @staticmethod
    def register_user(db: Session, username: str, password: str) -> Tuple[User, Optional[str]]:
        """
        Register a new user.
        Returns: (user, error_message) - error_message is None if successful
        """
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            return None, "Username already exists"
        
        # Validate username length
        if len(username) < 3 or len(username) > 50:
            return None, "Username must be between 3 and 50 characters"
        
        # Validate password length
        if len(password) < 6:
            return None, "Password must be at least 6 characters"
        
        # Create new user
        password_hash = AuthManager.hash_password(password)
        new_user = User(
            username=username,
            password_hash=password_hash
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return new_user, None
    
    @staticmethod
    def login_user(db: Session, username: str, password: str) -> Tuple[Optional[DBSession], Optional[str]]:
        """
        Authenticate a user and create a session.
        Returns: (session, error_message) - error_message is None if successful
        """
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None, "Invalid username or password"
        
        # Verify password
        if not AuthManager.verify_password(password, user.password_hash):
            return None, "Invalid username or password"
        
        # Create session token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + AuthManager.SESSION_DURATION
        
        session = DBSession(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        return session, None
    
    @staticmethod
    def verify_token(db: Session, token: str) -> Tuple[Optional[User], Optional[str]]:
        """
        Verify a session token and return the associated user.
        Returns: (user, error_message) - error_message is None if successful
        """
        session = db.query(DBSession).filter(DBSession.token == token).first()
        if not session:
            return None, "Invalid token"
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            db.delete(session)
            db.commit()
            return None, "Session expired"
        
        return session.user, None
    
    @staticmethod
    def logout_user(db: Session, token: str) -> bool:
        """
        Logout a user by deleting their session.
        Returns: True if successful, False otherwise
        """
        session = db.query(DBSession).filter(DBSession.token == token).first()
        if session:
            db.delete(session)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()


# Global auth manager instance
auth_manager = AuthManager()
