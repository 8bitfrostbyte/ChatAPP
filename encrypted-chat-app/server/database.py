"""
Database models for the encrypted chat application.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Table, LargeBinary, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
import os

# Database setup
DATABASE_URL = "sqlite:///./chat_app.db"
# For production, use PostgreSQL:
# DATABASE_URL = "postgresql://user:password@localhost/chat_app_db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    room_members = relationship("RoomMember", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.username}>"


class Room(Base):
    """Chat room/channel model."""
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    is_private = Column(Boolean, default=False)
    encryption_key = Column(LargeBinary, nullable=True)  # Room-specific encryption key
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")
    members = relationship("RoomMember", back_populates="room", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Room {self.name}>"


class RoomMember(Base):
    """Many-to-many relationship between users and rooms."""
    __tablename__ = "room_members"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_members")
    
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_members_room_user"),
    )
    
    def __repr__(self):
        return f"<RoomMember user_id={self.user_id} room_id={self.room_id}>"


class Message(Base):
    """Chat message model."""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)  # Encrypted content
    message_type = Column(String(20), default="text")  # text, system, bot, image
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Relationships
    room = relationship("Room", back_populates="messages")
    user = relationship("User", back_populates="messages")
    files = relationship("File", back_populates="message", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Message room_id={self.room_id} user_id={self.user_id}>"


class File(Base):
    """File/image attachment model."""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))  # image/png, image/jpeg, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("Message", back_populates="files")
    
    def __repr__(self):
        return f"<File {self.filename}>"


class Session(Base):
    """User session model for authentication."""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<Session user_id={self.user_id}>"


def init_db():
    """Initialize the database, creating all tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
