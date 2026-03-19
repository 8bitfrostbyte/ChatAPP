"""
Client-side encryption for E2EE chat (Fernet symmetric encryption).
"""

from cryptography.fernet import Fernet
import base64

class ClientEncryptionManager:
    def __init__(self):
        self.room_keys = {}  # room_id: Fernet

    def set_room_key(self, room_id, key_b64):
        self.room_keys[room_id] = Fernet(key_b64.encode() if isinstance(key_b64, str) else key_b64)

    def encrypt(self, room_id, plaintext):
        cipher = self.room_keys.get(room_id)
        if not cipher:
            raise ValueError("No key for room")
        return cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, room_id, ciphertext):
        cipher = self.room_keys.get(room_id)
        if not cipher:
            raise ValueError("No key for room")
        return cipher.decrypt(ciphertext.encode()).decode()

client_encryption_manager = ClientEncryptionManager()
