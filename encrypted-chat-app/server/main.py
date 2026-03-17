"""
Main FastAPI server for encrypted chat application.
Includes REST API endpoints and WebSocket real-time messaging.
"""

from fastapi import FastAPI, Depends, HTTPException, WebSocket, File, UploadFile, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict
import os
import shutil
import random
from pathlib import Path
from contextlib import suppress

# Import our modules
from database import (
    init_db, get_db, SessionLocal, User, Room, RoomMember, Message, File as DBFile, Session as DBSession
)
from auth import (
    auth_manager, UserRegisterRequest, UserLoginRequest, UserResponse, SessionResponse
)
from encryption import encryption_manager
from image_bot import image_bot
import asyncio

# Initialize FastAPI app
app = FastAPI(title="Encrypted Chat API", version="1.0.0")

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: int):
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, room_id: int):
        if room_id in self.active_connections:
            self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def broadcast(self, room_id: int, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()


class BotStreamManager:
    """Manages interval-based bot image streams per room."""

    def __init__(self):
        self.tasks: Dict[int, asyncio.Task] = {}
        self.configs: Dict[int, Dict] = {}
        self.paused_rooms = set()

    def _get_or_create_bot_user_id(self) -> int:
        db = SessionLocal()
        try:
            bot_user = db.query(User).filter(User.username == "ImageBot").first()
            if not bot_user:
                bot_user = User(
                    username="ImageBot",
                    password_hash=auth_manager.hash_password("image_bot_internal_user")
                )
                db.add(bot_user)
                db.commit()
                db.refresh(bot_user)
            return bot_user.id
        finally:
            db.close()

    async def _post_bot_message(self, room_id: int, content: str):
        db = SessionLocal()
        try:
            bot_user_id = self._get_or_create_bot_user_id()
            encrypted_content = encryption_manager.encrypt_message(room_id, content)
            message = Message(
                room_id=room_id,
                user_id=bot_user_id,
                content=encrypted_content,
                message_type="bot"
            )
            db.add(message)
            db.commit()
            db.refresh(message)

            await manager.broadcast(room_id, {
                "type": "message_new",
                "id": message.id,
                "user_id": bot_user_id,
                "username": "ImageBot",
                "content": content,
                "message_type": "bot",
                "created_at": message.created_at.isoformat()
            })
        finally:
            db.close()

    async def _run_stream(self, room_id: int, interval: float, tag_pool: List[str], mode: str):
        try:
            image_bot.config.image_history = []
            await asyncio.to_thread(image_bot.prime_buffer, tag_pool)
            await self._post_bot_message(
                room_id,
                f"Image stream started: every {interval:g}s | mode: {mode} | tags: {', '.join(tag_pool)}"
            )
            miss_count = 0
            while True:
                image_post = await asyncio.to_thread(image_bot.fetch_buffered_image, tag_pool)
                if image_post and image_post.get("url"):
                    msg = (
                        f"Tags: {image_bot.format_tags_for_log(image_post.get('tags', ''), max_tags=20)}\n"
                        f"Query: {image_post.get('query_tag', 'rating:explicit')}\n"
                        f"{image_post['url']}"
                    )
                    await self._post_bot_message(room_id, msg)
                    miss_count = 0
                else:
                    miss_count += 1
                    if miss_count in {1, 5}:
                        await self._post_bot_message(
                            room_id,
                            "No image result right now. Retrying..."
                        )
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            await self._post_bot_message(room_id, f"Image stream error: {e}")

    async def start_stream(self, room_id: int, interval: float, tag_pool: List[str], mode: str) -> Dict:
        if room_id in self.tasks and not self.tasks[room_id].done():
            return {"started": False, "message": "Stream already running in this room"}

        task = asyncio.create_task(self._run_stream(room_id, interval, tag_pool, mode))
        self.tasks[room_id] = task
        self.paused_rooms.discard(room_id)
        self.configs[room_id] = {
            "interval": interval,
            "mode": mode,
            "tag_pool": tag_pool,
            "started_at": datetime.utcnow().isoformat()
        }
        return {"started": True, "message": "Stream started"}

    async def stop_stream(self, room_id: int) -> Dict:
        task = self.tasks.get(room_id)
        if not task or task.done():
            return {"stopped": False, "message": "No running stream in this room"}

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        self.tasks.pop(room_id, None)
        self.configs.pop(room_id, None)
        self.paused_rooms.discard(room_id)
        await self._post_bot_message(room_id, "Image stream stopped")
        return {"stopped": True, "message": "Stream stopped"}

    async def pause_stream(self, room_id: int) -> Dict:
        task = self.tasks.get(room_id)
        if not task or task.done():
            return {"paused": False, "message": "No running stream in this room"}

        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

        self.tasks.pop(room_id, None)
        self.paused_rooms.add(room_id)
        await self._post_bot_message(room_id, "Image stream paused")
        return {"paused": True, "message": "Stream paused"}

    async def resume_stream(self, room_id: int) -> Dict:
        if room_id in self.tasks and not self.tasks[room_id].done():
            return {"resumed": False, "message": "Stream is already running"}

        cfg = self.configs.get(room_id)
        if not cfg:
            return {"resumed": False, "message": "No previous stream config in this room"}

        task = asyncio.create_task(
            self._run_stream(
                room_id,
                float(cfg.get("interval", 30.0)),
                list(cfg.get("tag_pool", ["rating:explicit"])),
                str(cfg.get("mode", "random"))
            )
        )
        self.tasks[room_id] = task
        self.paused_rooms.discard(room_id)
        return {"resumed": True, "message": "Stream resumed"}

    def get_status(self, room_id: int) -> Dict:
        task = self.tasks.get(room_id)
        running = bool(task and not task.done())
        return {
            "running": running,
            "paused": room_id in self.paused_rooms,
            "config": self.configs.get(room_id)
        }

    async def stop_all(self):
        room_ids = list(self.tasks.keys())
        for room_id in room_ids:
            await self.stop_stream(room_id)


bot_stream_manager = BotStreamManager()

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()
    # Ensure default room is "Room One"; migrate legacy "General" if needed.
    db = next(get_db())
    room_one = db.query(Room).filter(Room.name == "Room One").first()
    legacy_general = db.query(Room).filter(Room.name == "General").first()

    if room_one is None and legacy_general is not None:
        legacy_general.name = "Room One"
        db.commit()
        db.refresh(legacy_general)
        room_one = legacy_general

    if room_one is None:
        room_one = Room(name="Room One", is_private=False)
        db.add(room_one)
        db.commit()
        db.refresh(room_one)

    # Ensure there is an in-memory encryption key for the default room.
    encryption_manager.generate_room_key(room_one.id)
    db.close()


@app.on_event("shutdown")
async def shutdown():
    await bot_stream_manager.stop_all()


# ================================
# AUTHENTICATION ENDPOINTS
# ================================

@app.post("/api/auth/register", response_model=UserResponse)
async def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    user, error = auth_manager.register_user(db, request.username, request.password)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return user


@app.post("/api/auth/login", response_model=SessionResponse)
async def login(request: UserLoginRequest, db: Session = Depends(get_db)):
    """Login a user and create a session."""
    session, error = auth_manager.login_user(db, request.username, request.password)
    if error:
        raise HTTPException(status_code=401, detail=error)

    # Ensure users are automatically added to the default Room One on login.
    room_one = db.query(Room).filter(Room.name == "Room One").first()
    if room_one:
        room_one_member = db.query(RoomMember).filter(
            RoomMember.user_id == session.user_id,
            RoomMember.room_id == room_one.id
        ).first()
        if not room_one_member:
            db.add(RoomMember(user_id=session.user_id, room_id=room_one.id))
            db.commit()
    
    return {
        "token": session.token,
        "expires_at": session.expires_at,
        "user": session.user
    }


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Logout a user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    auth_manager.logout_user(db, token)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/verify", response_model=UserResponse)
async def verify_token(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Verify a session token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    return user


# ================================
# ROOM ENDPOINTS
# ================================

@app.get("/api/rooms", response_model=List[Dict])
async def list_rooms(authorization: str = Header(None), db: Session = Depends(get_db)):
    """List rooms visible to the current user.

    Public rooms are always visible.
    Private rooms are visible only to creator or members.
    """
    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user, _ = auth_manager.verify_token(db, token)

    public_rooms = db.query(Room).filter(Room.is_private == False).all()

    visible = {room.id: room for room in public_rooms}
    if user:
        private_rooms = db.query(Room).filter(Room.is_private == True).all()
        for room in private_rooms:
            if room.created_by == user.id:
                visible[room.id] = room
                continue
            is_member = db.query(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.user_id == user.id
            ).first()
            if is_member:
                visible[room.id] = room

    rooms = sorted(visible.values(), key=lambda r: (r.name.lower(), r.id))
    return [
        {
            "id": r.id,
            "name": r.name,
            "is_private": r.is_private,
            "created_at": r.created_at
        }
        for r in rooms
    ]


@app.post("/api/rooms", response_model=Dict)
async def create_room(
    name: str,
    is_private: bool = False,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Create a new room."""
    user, error = auth_manager.verify_token(db, authorization.split(" ")[1] if authorization else "")
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    existing = db.query(Room).filter(Room.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists")
    
    room = Room(name=name, is_private=is_private, created_by=user.id)
    db.add(room)
    db.commit()
    db.refresh(room)
    encryption_manager.generate_room_key(room.id)

    # Creator is automatically a member so private rooms are usable right away.
    creator_member = db.query(RoomMember).filter(
        RoomMember.room_id == room.id,
        RoomMember.user_id == user.id
    ).first()
    if not creator_member:
        db.add(RoomMember(room_id=room.id, user_id=user.id))
        db.commit()
    
    return {"id": room.id, "name": room.name, "created_at": room.created_at}


@app.delete("/api/rooms/{room_id}")
async def delete_room(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a room. Only creator can delete; Room One is protected."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.name.strip().lower() == "room one":
        raise HTTPException(status_code=400, detail="Room One cannot be deleted")

    if room.created_by != user.id:
        raise HTTPException(status_code=403, detail="Only room creator can delete this room")

    # Stop any active bot stream tied to this room before deleting.
    status = bot_stream_manager.get_status(room_id)
    if status.get("running") or status.get("paused"):
        await bot_stream_manager.stop_stream(room_id)

    db.delete(room)
    db.commit()
    return {"message": "Room deleted", "room_id": room_id}


@app.post("/api/rooms/{room_id}/make-private")
async def make_room_private(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Mark a room as private. Only room creator can do this."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.created_by != user.id:
        raise HTTPException(status_code=403, detail="Only room creator can make this room private")

    if room.is_private:
        return {"message": "Room is already private", "room_id": room_id, "is_private": True}

    room.is_private = True
    db.commit()

    system_msg_text = f"{room.name} is now private"
    system_msg = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, system_msg_text),
        message_type="system"
    )
    db.add(system_msg)
    db.commit()

    await manager.broadcast(room_id, {
        "type": "room_privacy_updated",
        "room_id": room_id,
        "is_private": True,
        "message": system_msg_text
    })

    return {"message": system_msg_text, "room_id": room_id, "is_private": True}


@app.get("/api/rooms/{room_id}")
async def get_room(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get room details."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user, _ = auth_manager.verify_token(db, token)

    if room.is_private:
        if not user:
            raise HTTPException(status_code=403, detail="Private room")
        is_member = db.query(RoomMember).filter(
            RoomMember.user_id == user.id,
            RoomMember.room_id == room_id
        ).first()
        if not is_member:
            raise HTTPException(status_code=403, detail="Private room")
    
    members = db.query(RoomMember).filter(RoomMember.room_id == room_id).all()
    return {
        "id": room.id,
        "name": room.name,
        "is_private": room.is_private,
        "created_at": room.created_at,
        "member_count": len(members)
    }


@app.post("/api/rooms/{room_id}/join")
async def join_room(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Join a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Check if already in room
    existing = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if existing:
        return {"message": "Already a member of this room"}

    # Private rooms are invite-only (creator can auto-manage membership).
    if room.is_private and room.created_by != user.id:
        raise HTTPException(status_code=403, detail="Private room is invite-only")
    
    member = RoomMember(user_id=user.id, room_id=room_id)
    db.add(member)
    db.commit()
    
    # Send system message
    system_msg = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, f"{user.username} is online"),
        message_type="system"
    )
    db.add(system_msg)
    db.commit()
    
    await manager.broadcast(room_id, {
        "type": "user_joined",
        "username": user.username,
        "message": f"{user.username} is online"
    })
    
    return {"message": "Joined room successfully"}


@app.post("/api/rooms/{room_id}/leave")
async def leave_room(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Leave a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Not a member of this room")
    
    db.delete(member)
    db.commit()
    
    # Send system message
    system_msg = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, f"{user.username} is offline"),
        message_type="system"
    )
    db.add(system_msg)
    db.commit()
    
    await manager.broadcast(room_id, {
        "type": "user_left",
        "username": user.username,
        "message": f"{user.username} is offline"
    })
    
    return {"message": "Left room successfully"}


@app.get("/api/rooms/{room_id}/members", response_model=List[Dict])
async def get_room_members(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get room members."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user, _ = auth_manager.verify_token(db, token)

    if room.is_private:
        if not user:
            raise HTTPException(status_code=403, detail="Private room")
        is_member = db.query(RoomMember).filter(
            RoomMember.user_id == user.id,
            RoomMember.room_id == room_id
        ).first()
        if not is_member:
            raise HTTPException(status_code=403, detail="Private room")

    members = db.query(RoomMember).filter(RoomMember.room_id == room_id).all()
    return [{"id": m.user.id, "username": m.user.username, "joined_at": m.joined_at} for m in members]


# ================================
# MESSAGE ENDPOINTS
# ================================

@app.get("/api/rooms/{room_id}/messages")
async def get_messages(
    room_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get message history for a room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user, _ = auth_manager.verify_token(db, token)

    if room.is_private:
        if not user:
            raise HTTPException(status_code=403, detail="Private room")
        is_member = db.query(RoomMember).filter(
            RoomMember.user_id == user.id,
            RoomMember.room_id == room_id
        ).first()
        if not is_member:
            raise HTTPException(status_code=403, detail="Private room")

    messages = db.query(Message).filter(
        Message.room_id == room_id,
        Message.deleted_at == None
    ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for msg in reversed(messages):  # Reverse to get chronological order
        try:
            decrypted = encryption_manager.decrypt_message(room_id, msg.content)
            result.append({
                "id": msg.id,
                "user_id": msg.user_id,
                "username": msg.user.username,
                "content": decrypted,
                "message_type": msg.message_type,
                "created_at": msg.created_at
            })
        except:
            # Skip messages that can't be decrypted
            pass
    
    return result


@app.delete("/api/messages/{message_id}")
async def delete_message(
    message_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a message (soft delete)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Only the sender can delete
    if message.user_id != user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own messages")
    
    message.deleted_at = datetime.utcnow()
    db.commit()
    
    await manager.broadcast(message.room_id, {
        "type": "message_deleted",
        "message_id": message_id
    })
    
    return {"message": "Message deleted"}


@app.post("/api/rooms/{room_id}/clear")
async def clear_room_messages(
    room_id: int,
    count: int = Query(1, ge=1, le=500),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Clear recent messages in a room.

    - Room creator can clear any recent user/bot/image messages.
    - Non-creator can clear only their own recent messages.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before clearing messages")

    query = db.query(Message).filter(
        Message.room_id == room_id,
        Message.deleted_at == None,
        Message.message_type != "system"
    )

    if room.created_by != user.id:
        query = query.filter(Message.user_id == user.id)

    target_messages = query.order_by(Message.created_at.desc()).limit(count).all()

    if not target_messages:
        return {"deleted": 0, "message": "No matching messages to clear"}

    now = datetime.utcnow()
    deleted_ids = []
    for msg in target_messages:
        msg.deleted_at = now
        deleted_ids.append(msg.id)

    db.commit()

    for msg_id in deleted_ids:
        await manager.broadcast(room_id, {
            "type": "message_deleted",
            "message_id": msg_id
        })

    return {
        "deleted": len(deleted_ids),
        "message": f"Cleared {len(deleted_ids)} message(s)",
        "scope": "room" if room.created_by == user.id else "own"
    }


# ================================
# FILE/IMAGE ENDPOINTS
# ================================

@app.post("/api/upload")
async def upload_file(
    room_id: int,
    file: UploadFile = File(...),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Upload an image file."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Save file
    file_extension = Path(file.filename).suffix
    unique_filename = f"{user.id}_{datetime.utcnow().timestamp()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Create message with image
    message = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, "[Image]"),
        message_type="image"
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Store file metadata
    db_file = DBFile(
        message_id=message.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=file.content_type
    )
    db.add(db_file)
    db.commit()
    
    await manager.broadcast(room_id, {
        "type": "message_new",
        "id": message.id,
        "user_id": user.id,
        "username": user.username,
        "content": "[Image]",
        "message_type": "image",
        "created_at": message.created_at.isoformat()
    })
    
    return {"message_id": message.id, "file_id": db_file.id}


@app.get("/api/files/{file_id}")
async def get_file(file_id: int, db: Session = Depends(get_db)):
    """Download/serve a file."""
    db_file = db.query(DBFile).filter(DBFile.id == file_id).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(db_file.file_path, media_type=db_file.file_type)


# ================================
# BOT ENDPOINTS
# ================================

@app.post("/api/bot/search")
async def search_tags(query: str):
    """Search for tags across APIs."""
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    results = image_bot.search_tags(query, limit=50)
    return results


@app.post("/api/bot/images")
async def fetch_images(tags: str, limit: int = Query(10, ge=1, le=50)):
    """Fetch images for given tags."""
    if not tags or len(tags.strip()) < 2:
        raise HTTPException(status_code=400, detail="Tags must be specified")
    
    images = image_bot.fetch_images(tags, limit=limit)
    return {"images": images}


@app.get("/api/bot/blacklist")
async def get_blacklist():
    """Get current blacklist."""
    return {"blacklist": image_bot.get_blacklist()}


@app.post("/api/bot/blacklist/add")
async def add_blacklist(tags: str):
    """Add tags to blacklist."""
    added = image_bot.add_blacklist_tags(tags)
    return {"added": added, "blacklist": image_bot.get_blacklist()}


@app.post("/api/bot/blacklist/remove")
async def remove_blacklist(tags: str):
    """Remove tags from blacklist."""
    removed = image_bot.remove_blacklist_tags(tags)
    return {"removed": removed, "blacklist": image_bot.get_blacklist()}


@app.get("/api/bot/tags")
async def get_saved_tags():
    """Get saved/start tags used by start command."""
    return {
        "saved_tags": image_bot.get_saved_tags(),
        "start_tags": image_bot.get_start_tags()
    }


@app.post("/api/bot/tags/add")
async def add_saved_tags(tags: str):
    """Add tags to saved/start pools."""
    return image_bot.add_tags(tags)


@app.post("/api/bot/tags/remove")
async def remove_saved_tags(tags: str):
    """Remove tags from saved/start pools."""
    return image_bot.remove_tags(tags)


@app.post("/api/bot/tags/clear")
async def clear_saved_tags():
    """Clear saved/start tag pools."""
    return image_bot.clear_tags()


@app.post("/api/bot/stream/start")
async def start_bot_stream(
    room_id: int,
    interval: float = Query(30.0, ge=1.0, le=3600.0),
    tags: Optional[str] = Query(None),
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Start interval-based bot image stream for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before starting stream")

    resolved = image_bot.resolve_start_tag_pool(tags)
    tag_pool = resolved["tag_pool"]
    mode = resolved["mode"]
    result = await bot_stream_manager.start_stream(room_id, interval, tag_pool, mode)
    return {
        **result,
        "room_id": room_id,
        "interval": interval,
        "mode": mode,
        "tag_pool": tag_pool
    }


@app.post("/api/bot/stream/stop")
async def stop_bot_stream(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Stop interval-based bot image stream for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before stopping stream")

    result = await bot_stream_manager.stop_stream(room_id)
    return {**result, "room_id": room_id}


@app.post("/api/bot/stream/pause")
async def pause_bot_stream(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Pause interval-based bot image stream for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before pausing stream")

    result = await bot_stream_manager.pause_stream(room_id)
    return {**result, "room_id": room_id}


@app.post("/api/bot/stream/resume")
async def resume_bot_stream(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Resume interval-based bot image stream for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before resuming stream")

    result = await bot_stream_manager.resume_stream(room_id)
    return {**result, "room_id": room_id}


@app.get("/api/bot/stream/status")
async def bot_stream_status(
    room_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Get bot stream status for a room."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Join the room before checking stream status")

    status = bot_stream_manager.get_status(room_id)
    return {"room_id": room_id, **status}


# ================================
# WEBSOCKET ENDPOINT
# ================================

@app.websocket("/ws/rooms/{room_id}/{token}")
async def websocket_endpoint(room_id: int, token: str, websocket: WebSocket):
    """WebSocket endpoint for real-time messaging."""
    # Verify user
    db = next(get_db())
    user, error = auth_manager.verify_token(db, token)
    if error:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Check room exists
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return
    
    # Check user is member
    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        await websocket.close(code=4003, reason="Not a member of this room")
        return
    
    await manager.connect(websocket, room_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Encrypt and store message
                encrypted_content = encryption_manager.encrypt_message(room_id, data.get("content", ""))
                message = Message(
                    room_id=room_id,
                    user_id=user.id,
                    content=encrypted_content,
                    message_type="text"
                )
                db.add(message)
                db.commit()
                db.refresh(message)
                
                # Broadcast to all users in room
                await manager.broadcast(room_id, {
                    "type": "message_new",
                    "id": message.id,
                    "user_id": user.id,
                    "username": user.username,
                    "content": data.get("content", ""),
                    "message_type": "text",
                    "created_at": message.created_at.isoformat()
                })
            
            elif data.get("type") == "typing":
                await manager.broadcast(room_id, {
                    "type": "typing",
                    "username": user.username
                })
    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    finally:
        manager.disconnect(websocket, room_id)
        db.close()


# ================================
# HEALTH CHECK
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile=None, ssl_certfile=None)
