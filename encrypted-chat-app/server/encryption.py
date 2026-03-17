"""
Encryption module for message and data encryption.
Uses Fernet (symmetric encryption) for E2E encryption.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os
from typing import Dict

class EncryptionManager:
    """Manages encryption/decryption for messages and files."""
    
    def __init__(self):
        self.room_keys: Dict[int, Fernet] = {}
    
    def generate_room_key(self, room_id: int) -> str:
        """Generate a unique encryption key for a room."""
        key = Fernet.generate_key()
        self.room_keys[room_id] = Fernet(key)
        return key.decode()
    
    def get_room_key(self, room_id: int) -> Fernet:
        """Get the Fernet cipher for a room, or create if doesn't exist."""
        if room_id not in self.room_keys:
            self.generate_room_key(room_id)
        return self.room_keys[room_id]
    
    def set_room_key(self, room_id: int, key: bytes) -> None:
        """Set the encryption key for a room."""
        self.room_keys[room_id] = Fernet(key)
    
    def encrypt_message(self, room_id: int, message: str) -> str:
        """Encrypt a message for a specific room."""
        cipher = self.get_room_key(room_id)
        encrypted = cipher.encrypt(message.encode())
        return encrypted.decode()
    
    def decrypt_message(self, room_id: int, encrypted_message: str) -> str:
        """Decrypt a message for a specific room."""
        try:
            cipher = self.get_room_key(room_id)
            decrypted = cipher.decrypt(encrypted_message.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def derive_password_key(self, password: str, salt: bytes = None) -> tuple:
        """Derive an encryption key from a password using PBKDF2."""
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt
    
    def encrypt_password_protected(self, data: str, password: str) -> tuple:
        """Encrypt data with a password-derived key."""
        key, salt = self.derive_password_key(password)
        cipher = Fernet(key)
        encrypted = cipher.encrypt(data.encode())
        return encrypted.decode(), salt.hex()
    
    def decrypt_password_protected(self, encrypted_data: str, password: str, salt_hex: str) -> str:
        """Decrypt password-protected data."""
        salt = bytes.fromhex(salt_hex)
        key, _ = self.derive_password_key(password, salt)
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()


# Global encryption manager instance
encryption_manager = EncryptionManager()
