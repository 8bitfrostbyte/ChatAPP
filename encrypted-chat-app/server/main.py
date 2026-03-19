

from fastapi import FastAPI, Depends, HTTPException, WebSocket, File, UploadFile, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict
import os
import shutil
import random
import mimetypes
import re
import time
from pathlib import Path
from contextlib import suppress
import requests

# Import our modules
from database import (
    init_db, get_db, SessionLocal, User, Room, RoomMember, RoomInvite, Message, File as DBFile, Session as DBSession
)
from auth import (
    auth_manager, UserRegisterRequest, UserLoginRequest, UserResponse, SessionResponse
)
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

# Update service configuration (server checks GitHub, clients download via server)
UPDATE_GITHUB_REPO = os.getenv("UPDATE_GITHUB_REPO", "")  # Format: owner/repo
UPDATE_ASSET_NAME = os.getenv("UPDATE_ASSET_NAME", "EncryptedChat.exe")
UPDATE_CACHE_DIR = Path("updates")
UPDATE_CACHE_DIR.mkdir(exist_ok=True)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # room_id -> {user_id -> connection_count}
        self.room_user_connections: Dict[int, Dict[int, int]] = {}
        # room_id -> {user_id -> unix timestamp}
        self.room_user_last_seen: Dict[int, Dict[int, float]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: int, user_id: int) -> bool:
        await websocket.accept()
        prior_count = (self.room_user_connections.get(room_id) or {}).get(user_id, 0)
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        if room_id not in self.room_user_connections:
            self.room_user_connections[room_id] = {}
        self.room_user_connections[room_id][user_id] = self.room_user_connections[room_id].get(user_id, 0) + 1
        self.touch(room_id, user_id)
        return prior_count == 0
    
    def disconnect(self, websocket: WebSocket, room_id: int, user_id: int) -> bool:
        user_went_offline = False
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

        if room_id in self.room_user_connections:
            current = self.room_user_connections[room_id].get(user_id, 0)
            if current <= 1:
                self.room_user_connections[room_id].pop(user_id, None)
                user_went_offline = True
            else:
                self.room_user_connections[room_id][user_id] = current - 1
            if not self.room_user_connections[room_id]:
                del self.room_user_connections[room_id]

        if room_id in self.room_user_last_seen:
            self.room_user_last_seen[room_id].pop(user_id, None)
            if not self.room_user_last_seen[room_id]:
                del self.room_user_last_seen[room_id]

        return user_went_offline

    def touch(self, room_id: int, user_id: int):
        if room_id not in self.room_user_last_seen:
            self.room_user_last_seen[room_id] = {}
        self.room_user_last_seen[room_id][user_id] = time.time()

    def list_online_user_ids(self, room_id: int, max_age_seconds: int = 60) -> List[int]:
        now = time.time()
        last_seen = self.room_user_last_seen.get(room_id) or {}
        fresh_ids = {
            user_id
            for user_id, seen_at in last_seen.items()
            if (now - float(seen_at)) <= float(max_age_seconds)
        }
        # Backward compatibility: older clients may not send heartbeat yet,
        # but they still hold active websocket connections.
        connected_ids = set((self.room_user_connections.get(room_id) or {}).keys())
        return list(fresh_ids | connected_ids)
    
    async def broadcast(self, room_id: int, message: dict):
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()


def _delete_message_files_from_disk(message: Message):
    """Remove message attachment files from disk (best effort)."""
    for file_obj in list(message.files or []):
        try:
            if file_obj.file_path:
                p = Path(file_obj.file_path)
                if p.exists() and p.is_file():
                    p.unlink()
        except Exception:
            # Keep deletion flow resilient even if one file cannot be removed.
            pass


def _hard_delete_message(db: Session, message: Message):
    """Permanently delete a message and any files attached to it."""
    _delete_message_files_from_disk(message)
    db.delete(message)


def _purge_soft_deleted_messages(db: Session):
    """Cleanup legacy soft-deleted messages so they no longer consume storage."""
    stale = db.query(Message).filter(
        Message.deleted_at != None,
        Message.message_type.in_(["text", "image", "file", "bot"]),
    ).all()
    if not stale:
        return
    for msg in stale:
        _hard_delete_message(db, msg)
    db.commit()


def _parse_version_tuple(value: str) -> tuple:
    """Parse semantic-ish version text into a comparable integer tuple."""
    parts = [int(p) for p in re.findall(r"\d+", str(value or ""))[:3]]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _is_newer_version(latest: str, current: str) -> bool:
    return _parse_version_tuple(latest) > _parse_version_tuple(current)


def _extract_release_version(release_json: dict) -> str:
    tag = str(release_json.get("tag_name") or "").strip()
    # Strip common tag prefixes: "version_", "version", "v"
    lower = tag.lower()
    if lower.startswith("version_"):
        tag = tag[8:]
    elif lower.startswith("version"):
        tag = tag[7:]
    elif lower.startswith("v"):
        tag = tag[1:]
    return tag or "0.0.0"


def _pick_release_asset(release_json: dict) -> Optional[dict]:
    assets = release_json.get("assets") or []
    if not isinstance(assets, list):
        return None

    # Hard requirement: updater serves executables only.
    configured_name = str(UPDATE_ASSET_NAME or "").strip()
    if configured_name and not configured_name.lower().endswith(".exe"):
        raise RuntimeError("UPDATE_ASSET_NAME must be an .exe file")

    # Prefer explicit configured asset, then any .exe asset.
    for asset in assets:
        name = str(asset.get("name", "")).strip()
        if not name.lower().endswith(".exe"):
            continue
        if name.lower() == configured_name.lower():
            return asset
    for asset in assets:
        if str(asset.get("name", "")).strip().lower().endswith(".exe"):
            return asset
    return None


def _fetch_latest_release() -> dict:
    """Return normalized latest release metadata from GitHub."""
    if not UPDATE_GITHUB_REPO or "/" not in UPDATE_GITHUB_REPO:
        raise RuntimeError("UPDATE_GITHUB_REPO is not configured (expected owner/repo)")

    url = f"https://api.github.com/repos/{UPDATE_GITHUB_REPO}/releases/latest"
    response = requests.get(url, timeout=15, headers={"Accept": "application/vnd.github+json"})
    if response.status_code != 200:
        raise RuntimeError(f"GitHub release check failed ({response.status_code})")

    parsed = response.json()
    release_json = parsed if isinstance(parsed, dict) else {}
    asset = _pick_release_asset(release_json)
    if not asset:
        raise RuntimeError("No EXE asset found in latest GitHub release")

    return {
        "tag_name": str(release_json.get("tag_name", "")),
        "version": _extract_release_version(release_json),
        "name": str(release_json.get("name", "")),
        "published_at": release_json.get("published_at"),
        "body": str(release_json.get("body", "")),
        "asset_name": str(asset.get("name", UPDATE_ASSET_NAME)),
        "asset_url": str(asset.get("browser_download_url", "")),
    }


def _ensure_cached_release_exe(release_info: dict) -> Path:
    """Download latest release EXE to local cache and return its path."""
    version = release_info.get("version", "0.0.0")
    asset_name = release_info.get("asset_name", UPDATE_ASSET_NAME)
    asset_url = release_info.get("asset_url", "")
    if not asset_url:
        raise RuntimeError("Release asset URL missing")
    if not str(asset_name).lower().endswith(".exe"):
        raise RuntimeError("Latest release asset is not an EXE")

    target_path = UPDATE_CACHE_DIR / f"{version}_{asset_name}"
    if target_path.exists() and target_path.stat().st_size > 0:
        return target_path

    with requests.get(asset_url, timeout=60, stream=True) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download release EXE ({resp.status_code})")
        with open(target_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

    return target_path


def ensure_room_encryption_key(db: Session, room: Room) -> bytes:
    """Ensure room has a persistent encryption key in DB and loaded in memory."""
    if room.encryption_key:
        key_bytes = bytes(room.encryption_key)
        encryption_manager.set_room_key(room.id, key_bytes)
        return key_bytes

    key_text = encryption_manager.generate_room_key(room.id)
    key_bytes = key_text.encode()
    room.encryption_key = key_bytes
    db.commit()
    db.refresh(room)
    return key_bytes


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
        # Save bot message to the database so it persists in history
        db = SessionLocal()
        try:
            bot_user_id = self._get_or_create_bot_user_id()
            # Encrypt content for consistency with user messages
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
            print(f"[DEBUG] _post_bot_message: Saved bot message id={message.id} room_id={room_id} user_id={bot_user_id} content={content}")
            await manager.broadcast(room_id, {
                "type": "message_new",
                "id": message.id,
                "user_id": bot_user_id,
                "username": "ImageBot",
                "content": content,
                "message_type": "bot",
                "created_at": message.created_at.isoformat()
            })
            print(f"[DEBUG] _post_bot_message: Broadcasted bot message id={message.id} room_id={room_id}")
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
            error_streak = 0
            while True:
                image_post = await asyncio.to_thread(image_bot.fetch_buffered_image, tag_pool)
                if not image_post or not image_post.get("url"):
                    fallback_tag = random.choice(tag_pool) if tag_pool else "rating:explicit"
                    fallback_images = await asyncio.to_thread(image_bot.fetch_images, fallback_tag, 1)
                    if fallback_images:
                        image_post = fallback_images[0]

                if image_post and image_post.get("url"):
                    msg = (
                        f"Tags: {image_bot.format_tags_for_log(image_post.get('tags', ''), max_tags=20)}\n"
                        f"Query: {image_post.get('query_tag', 'rating:explicit')}\n"
                        f"{image_post['url']}"
                    )
                    await self._post_bot_message(room_id, msg)
                    miss_count = 0
                    error_streak = 0
                else:
                    error_streak += 1
                    miss_count += 1
                    if miss_count in {1, 5}:
                        status = "No image result right now. Retrying..."
                        if error_streak > 10:
                            status += " (experiencing API issues, check back soon)"
                        await self._post_bot_message(room_id, status)
                
                # Adaptive backoff: if error streak is high, sleep longer
                sleep_time = interval * (1 + min(error_streak // 3, 4))
                await asyncio.sleep(sleep_time)
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

    # Ensure every room has a persistent key and load into memory.
    all_rooms = db.query(Room).all()
    for room in all_rooms:
        ensure_room_encryption_key(db, room)

    # Remove any previously soft-deleted rows/files from older builds.
    _purge_soft_deleted_messages(db)
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
            "created_by": r.created_by,
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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    user, error = auth_manager.verify_token(db, authorization.split(" ")[1])
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    existing = db.query(Room).filter(Room.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists")
    
    room = Room(name=name, is_private=is_private, created_by=user.id)
    db.add(room)
    db.commit()
    db.refresh(room)
    ensure_room_encryption_key(db, room)

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

    if not room.is_private:
        raise HTTPException(status_code=400, detail="Invites are only required for private rooms")

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
        content=f"{user.username} is online",
        message_type="system"
    )
    db.add(system_msg)
    db.commit()
    
    await manager.broadcast(room_id, {
        "type": "user_joined",
        "room_id": room_id,
        "username": user.username,
        "message": f"{user.username} has joined the room"
    })
    await manager.broadcast(room_id, {
        "type": "system_message",
        "room_id": room_id,
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
        "room_id": room_id,
        "username": user.username,
        "message": f"{user.username} has left the room"
    })
    await manager.broadcast(room_id, {
        "type": "system_message",
        "room_id": room_id,
        "message": f"{user.username} is offline"
    })
    
    return {"message": "Left room successfully"}


@app.post("/api/rooms/{room_id}/invite")
async def invite_user_to_room(
    room_id: int,
    username: str,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Invite a user to a room. Only the room creator can do this."""
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
        raise HTTPException(status_code=403, detail="Only the room creator can invite users")

    target = db.query(User).filter(User.username == username).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found")

    existing = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id == target.id
    ).first()
    if existing:
        return {"message": f"{username} is already a member of this room"}

    pending_invite = db.query(RoomInvite).filter(
        RoomInvite.room_id == room_id,
        RoomInvite.invited_user_id == target.id,
        RoomInvite.status == "pending"
    ).first()
    if pending_invite:
        return {"message": f"Invite already pending for {username}"}

    db.add(RoomInvite(
        room_id=room_id,
        inviter_user_id=user.id,
        invited_user_id=target.id,
        status="pending"
    ))
    db.commit()

    system_msg_text = f"{username} was invited to the room by {user.username}"
    system_msg = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, system_msg_text),
        message_type="system"
    )
    db.add(system_msg)
    db.commit()

    await manager.broadcast(room_id, {
        "type": "system_message",
        "room_id": room_id,
        "message": system_msg_text,
    })

    return {"message": f"Invite sent to {username}"}


@app.get("/api/invites/pending", response_model=List[Dict])
async def get_pending_invites(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """List pending room invites for the authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    invites = db.query(RoomInvite).filter(
        RoomInvite.invited_user_id == user.id,
        RoomInvite.status == "pending"
    ).order_by(RoomInvite.created_at.asc()).all()

    payload = []
    for inv in invites:
        room = db.query(Room).filter(Room.id == inv.room_id).first()
        inviter = db.query(User).filter(User.id == inv.inviter_user_id).first()
        if not room or not inviter:
            continue
        payload.append({
            "invite_id": inv.id,
            "room_id": room.id,
            "room_name": room.name,
            "inviter_username": inviter.username,
            "created_at": inv.created_at,
        })

    return payload


@app.post("/api/invites/{invite_id}/respond")
async def respond_to_invite(
    invite_id: int,
    action: str = Query(...),  # accept|decline
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Accept or decline a pending room invite."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)

    normalized = str(action or "").strip().lower()
    if normalized not in {"accept", "decline"}:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'decline'")

    invite = db.query(RoomInvite).filter(RoomInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.invited_user_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot respond to this invite")

    if invite.status != "pending":
        return {"message": f"Invite already {invite.status}"}

    room = db.query(Room).filter(Room.id == invite.room_id).first()
    inviter = db.query(User).filter(User.id == invite.inviter_user_id).first()
    if not room or not inviter:
        raise HTTPException(status_code=404, detail="Room or inviter no longer exists")

    if normalized == "accept":
        existing_member = db.query(RoomMember).filter(
            RoomMember.room_id == room.id,
            RoomMember.user_id == user.id
        ).first()
        if not existing_member:
            db.add(RoomMember(room_id=room.id, user_id=user.id))
        invite.status = "accepted"
        invite.responded_at = datetime.utcnow()
        db.commit()

        notice = f"{user.username} accepted an invite to the room"
        db.add(Message(
            room_id=room.id,
            user_id=inviter.id,
            content=encryption_manager.encrypt_message(room.id, notice),
            message_type="system"
        ))
        db.commit()

        await manager.broadcast(room.id, {
            "type": "system_message",
            "room_id": room.id,
            "message": notice,
        })
        return {"message": f"Joined private room '{room.name}'"}

    invite.status = "declined"
    invite.responded_at = datetime.utcnow()
    db.commit()
    return {"message": f"Declined invite to '{room.name}'"}


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

    online_user_ids = manager.list_online_user_ids(room_id, max_age_seconds=60)
    if not online_user_ids:
        return []

    members = db.query(RoomMember).filter(
        RoomMember.room_id == room_id,
        RoomMember.user_id.in_(online_user_ids)
    ).all()
    return [{"id": m.user.id, "username": m.user.username, "joined_at": m.joined_at} for m in members]


# ================================
# MESSAGE ENDPOINTS
# ================================

@app.get("/api/rooms/{room_id}/messages")
async def get_messages(
    room_id: int,
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request: Request = None,
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

    print(f"[DEBUG] get_messages: fetched {len(messages)} messages for room {room_id}")
    for msg in messages:
        try:
            decrypted = encryption_manager.decrypt_message(room_id, msg.content)
        except Exception as e:
            decrypted = f"[DECRYPT ERROR] {e}"
        print(f"[DEBUG] Message id={msg.id} type={msg.message_type} user={msg.user_id} content={decrypted} files={[f.id for f in getattr(msg, 'files', [])]}")

    result = []
    # Always use request.base_url for file_url if possible
    base_url = str(request.base_url).rstrip("/") if request and hasattr(request, "base_url") else None
    for msg in reversed(messages):  # Reverse to get chronological order
        try:
            decrypted = encryption_manager.decrypt_message(room_id, msg.content)
            payload = {
                "id": msg.id,
                "user_id": msg.user_id,
                "username": msg.user.username,
                "content": decrypted,
                "message_type": msg.message_type,
                "created_at": msg.created_at
            }

            if msg.files:
                file_obj = msg.files[0]
                payload["file_id"] = file_obj.id
                payload["filename"] = file_obj.filename
                payload["file_type"] = file_obj.file_type
                payload["file_size"] = file_obj.file_size
                if base_url:
                    payload["file_url"] = f"{base_url}/api/files/{file_obj.id}"
                else:
                    # Fallback: try to build absolute URL from config or environment
                    from os import environ
                    host = environ.get("SERVER_HOST", "localhost")
                    port = environ.get("SERVER_PORT", "8000")
                    payload["file_url"] = f"http://{host}:{port}/api/files/{file_obj.id}"

            result.append(payload)
        except Exception as e:
            # Skip messages that can't be decrypted
            pass
    return result


@app.delete("/api/messages/{message_id}")
async def delete_message(
    message_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Delete a message permanently, including any attached files."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split(" ")[1]
    user, error = auth_manager.verify_token(db, token)
    if error:
        raise HTTPException(status_code=401, detail=error)
    
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Only the sender can delete user-generated message content.
    if message.user_id != user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own messages")

    if str(message.message_type or "").lower() not in {"text", "image", "file", "bot"}:
        raise HTTPException(status_code=403, detail="System messages cannot be deleted")
    
    _hard_delete_message(db, message)
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

    Any room member can clear recent messages, including presence/system lines.
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
        Message.deleted_at == None
    )

    target_messages = query.order_by(Message.created_at.desc()).limit(count).all()

    print(f"[DEBUG] clear_room_messages: count={count}, found={len(target_messages)} messages to delete: {[m.id for m in target_messages]}")

    if not target_messages:
        return {"deleted": 0, "message": "No matching messages to clear"}

    deleted_ids = []
    for msg in target_messages:
        deleted_ids.append(msg.id)
        _hard_delete_message(db, msg)

    db.commit()

    print(f"[DEBUG] clear_room_messages: actually deleted {len(deleted_ids)} messages: {deleted_ids}")

    for msg_id in deleted_ids:
        await manager.broadcast(room_id, {
            "type": "message_deleted",
            "message_id": msg_id
        })

    return {
        "deleted": len(deleted_ids),
        "message": f"Cleared {len(deleted_ids)} message(s)",
        "scope": "room"
    }


# ================================
# FILE/IMAGE ENDPOINTS
# ================================

@app.post("/api/upload")
async def upload_file(
    room_id: int,
    file: UploadFile = File(...),
    request: Request = None,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Upload a file attachment (images and non-images)."""
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
        raise HTTPException(status_code=403, detail="Not a member of this room")
    
    file_extension = Path(file.filename or "").suffix.lower()
    normalized_content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    guessed_content_type = (mimetypes.guess_type(file.filename or "")[0] or "").lower()

    # Accept arbitrary file types; infer a best-effort content-type.
    effective_content_type = normalized_content_type or guessed_content_type or "application/octet-stream"
    
    # Save file
    unique_filename = f"{user.id}_{datetime.utcnow().timestamp()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    is_image = effective_content_type.startswith("image/") or file_extension in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
    message_type = "image" if is_image else "file"
    message_text = "[Image]" if is_image else f"[File] {file.filename}"

    # Create message with file metadata
    message = Message(
        room_id=room_id,
        user_id=user.id,
        content=encryption_manager.encrypt_message(room_id, message_text),
        message_type=message_type
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    print(f"[DEBUG] upload_file: Created message id={message.id} type={message.message_type} room_id={room_id} user_id={user.id}")
    
    # Store file metadata
    db_file = DBFile(
        message_id=message.id,
        filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=effective_content_type
    )
    db.add(db_file)
    db.commit()
    print(f"[DEBUG] upload_file: Saved file id={db_file.id} for message id={message.id} filename={db_file.filename}")
    
    file_url = f"/api/files/{db_file.id}"
    if request:
        file_url = f"{str(request.base_url).rstrip('/')}/api/files/{db_file.id}"

    await manager.broadcast(room_id, {
        "type": "message_new",
        "id": message.id,
        "user_id": user.id,
        "room_id": room_id,
        "username": user.username,
        "content": message_text,
        "message_type": message_type,
        "file_id": db_file.id,
        "filename": db_file.filename,
        "file_type": db_file.file_type,
        "file_size": db_file.file_size,
        "file_url": file_url,
        "created_at": message.created_at.isoformat()
    })
    
    return {
        "message_id": message.id,
        "file_id": db_file.id,
        "filename": db_file.filename,
        "file_type": db_file.file_type,
        "file_size": db_file.file_size,
        "message_type": message_type,
        "file_url": file_url,
    }


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
    
    results = image_bot.search_tags(query, limit=150)
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


@app.post("/api/bot/blacklist/clear")
async def clear_blacklist():
    """Clear all blacklist tags."""
    removed = image_bot.clear_blacklist_tags()
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


def _ensure_bot_room_access(db: Session, user: User, room_id: int) -> Room:
    """Validate that user can control/view bot stream state for room."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.is_private:
        member = db.query(RoomMember).filter(
            RoomMember.user_id == user.id,
            RoomMember.room_id == room_id
        ).first()
        if not member and room.created_by != user.id:
            raise HTTPException(status_code=403, detail="You do not have access to this private room")

    return room


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

    _ensure_bot_room_access(db, user, room_id)

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

    _ensure_bot_room_access(db, user, room_id)

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

    _ensure_bot_room_access(db, user, room_id)

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

    _ensure_bot_room_access(db, user, room_id)

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

    _ensure_bot_room_access(db, user, room_id)

    status = bot_stream_manager.get_status(room_id)
    return {"room_id": room_id, **status}


# ================================
# WEBSOCKET ENDPOINT
# ================================

@app.websocket("/ws/rooms/{room_id}/{token}")
async def websocket_endpoint(room_id: int, token: str, websocket: WebSocket):
    """WebSocket endpoint for real-time messaging."""
    client_host = getattr(websocket.client, "host", "unknown") if websocket.client else "unknown"
    print(f"WebSocket connect attempt: room={room_id} client={client_host}")

    # Verify user
    db = next(get_db())
    user, error = auth_manager.verify_token(db, token)
    if error:
        print(f"WebSocket reject: room={room_id} client={client_host} reason=invalid_token detail={error}")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Check room exists
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        print(f"WebSocket reject: room={room_id} user={user.username} client={client_host} reason=room_not_found")
        await websocket.close(code=4004, reason="Room not found")
        return
    
    # Check websocket room access. Public rooms auto-admit on connect if needed.
    member = db.query(RoomMember).filter(
        RoomMember.user_id == user.id,
        RoomMember.room_id == room_id
    ).first()
    if not member:
        if room.is_private and room.created_by != user.id:
            print(
                f"WebSocket reject: room={room_id} user={user.username} client={client_host} "
                f"reason=private_room_not_member"
            )
            await websocket.close(code=4003, reason="Not a member of this room")
            return
        if not room.is_private:
            print(
                f"WebSocket auto-join: room={room_id} user={user.username} client={client_host} "
                f"reason=public_room_missing_membership"
            )
            member = RoomMember(user_id=user.id, room_id=room_id)
            db.add(member)
            db.commit()

    print(
        f"WebSocket accept: room={room_id} user={user.username} client={client_host} "
        f"private={room.is_private}"
    )
    
    became_online = await manager.connect(websocket, room_id, user.id)

    if became_online:
        await manager.broadcast(room_id, {
            "type": "user_joined",
            "room_id": room_id,
            "username": user.username,
            "message": f"{user.username} has joined the room"
        })
        await manager.broadcast(room_id, {
            "type": "system_message",
            "room_id": room_id,
            "message": f"{user.username} is online"
        })
    
    try:
        while True:
            data = await websocket.receive_json()
            manager.touch(room_id, user.id)

            if data.get("type") == "heartbeat":
                continue
            
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
        user_went_offline = manager.disconnect(websocket, room_id, user.id)

        if user_went_offline:
            still_member = db.query(RoomMember).filter(
                RoomMember.user_id == user.id,
                RoomMember.room_id == room_id
            ).first()
            if still_member:
                await manager.broadcast(room_id, {
                    "type": "user_left",
                    "room_id": room_id,
                    "username": user.username,
                    "message": f"{user.username} has left the room"
                })
                await manager.broadcast(room_id, {
                    "type": "system_message",
                    "room_id": room_id,
                    "message": f"{user.username} is offline"
                })
        db.close()


# ================================
# HEALTH CHECK
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/update/check")
async def check_for_update(current_version: str = Query("0.0.0")):
    """Check GitHub latest release from the server and report update availability."""
    if not UPDATE_GITHUB_REPO or "/" not in UPDATE_GITHUB_REPO:
        return {
            "configured": False,
            "update_available": False,
            "current_version": current_version,
            "latest_version": current_version,
            "release_name": "",
            "published_at": None,
            "notes": "",
            "asset_name": UPDATE_ASSET_NAME,
            "repo": UPDATE_GITHUB_REPO,
            "detail": "Update server is not configured",
        }

    try:
        latest = _fetch_latest_release()
        latest_version = latest.get("version", "0.0.0")
        return {
            "configured": True,
            "update_available": _is_newer_version(latest_version, current_version),
            "current_version": current_version,
            "latest_version": latest_version,
            "release_name": latest.get("name", ""),
            "published_at": latest.get("published_at"),
            "notes": latest.get("body", ""),
            "asset_name": latest.get("asset_name", UPDATE_ASSET_NAME),
            "repo": UPDATE_GITHUB_REPO,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Update check failed: {e}")


@app.get("/api/update/download")
async def download_latest_update():
    """Download latest EXE from GitHub to server cache and stream it to the client."""
    try:
        latest = _fetch_latest_release()
        asset_name = str(latest.get("asset_name", UPDATE_ASSET_NAME))
        if not asset_name.lower().endswith(".exe"):
            raise RuntimeError("Refusing to serve non-EXE update asset")
        exe_path = _ensure_cached_release_exe(latest)
        return FileResponse(
            path=str(exe_path),
            media_type="application/octet-stream",
            filename=asset_name,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Update download failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, ssl_keyfile=None, ssl_certfile=None)
