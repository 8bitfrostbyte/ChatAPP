import sqlite3
from datetime import datetime

def print_room_messages(db_path, room_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, room_id, user_id, message_type, content, created_at, deleted_at
        FROM messages
        WHERE room_id=?
        ORDER BY created_at DESC
        LIMIT 50;
    """, (room_id,))
    rows = cur.fetchall()
    print(f"Messages for room {room_id} (most recent first):")
    for row in rows:
        id, room_id, user_id, msg_type, content, created_at, deleted_at = row
        print(f"id={id} user={user_id} type={msg_type} deleted={deleted_at is not None} created={created_at}\n  content={content}")
    conn.close()

if __name__ == "__main__":
    # Adjust the path if needed
    db_path = "encrypted-chat-app/server/chat_app.db"
    room_id = 8  # Change if needed
    print_room_messages(db_path, room_id)
