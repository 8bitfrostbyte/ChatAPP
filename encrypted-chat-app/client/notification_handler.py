"""
Notification and sound handler for Windows.
"""

from playsound import playsound
from PyQt6.QtWidgets import QMessageBox, QMainWindow
from PyQt6.QtCore import QTimer
import os
from typing import Optional
from pathlib import Path


class NotificationHandler:
    """Handles desktop notifications and sound alerts."""
    
    def __init__(
        self,
        parent: Optional[QMainWindow] = None,
        sound_enabled: bool = True,
        custom_sound_path: Optional[str] = None,
    ):
        self.parent = parent
        self.sound_enabled = sound_enabled
        self.notification_sound = None
        self.custom_sound_path = custom_sound_path
        self.setup_sounds()
    
    def setup_sounds(self):
        """Setup notification sounds."""
        self.notification_sound = None

        if self.custom_sound_path and os.path.exists(self.custom_sound_path):
            self.notification_sound = self.custom_sound_path
            return

        # Try to find a notification sound file
        # If not found, we'll create a simple beep using the system
        sound_path = Path(__file__).parent / "sounds" / "notification.mp3"
        if sound_path.exists():
            self.notification_sound = str(sound_path)

    def set_custom_sound(self, sound_path: Optional[str]):
        """Set a custom notification sound file path."""
        self.custom_sound_path = sound_path
        self.setup_sounds()
    
    def show_notification(self, title: str, message: str, duration: int = 3000):
        """Show a system notification."""
        if not self.parent:
            return
        
        # Try to use Windows toast notifications if available
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=duration // 1000, threaded=True)
        except ImportError:
            # Fallback: use PyQt dialog
            self._show_qt_notification(title, message, duration)
    
    def _show_qt_notification(self, title: str, message: str, duration: int):
        """Show notification using PyQt."""
        if not self.parent:
            return
        
        # Create a simple notification window
        msg_box = QMessageBox(self.parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Auto-close after duration
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(msg_box.accept)
        timer.start(duration)
        
        msg_box.exec()
    
    def play_sound(self):
        """Play notification sound."""
        if not self.sound_enabled:
            return
        
        try:
            if self.notification_sound and os.path.exists(self.notification_sound):
                playsound(self.notification_sound)
            else:
                import winsound
                try:
                    # Soft Windows "asterisk" info ding, played async (non-blocking)
                    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                except Exception:
                    winsound.Beep(440, 80)  # quiet fallback
        except Exception as e:
            print(f"Failed to play sound: {e}")
    
    def set_sound_enabled(self, enabled: bool):
        """Enable/disable notification sounds."""
        self.sound_enabled = enabled
    
    def notify_message_received(self, username: str, preview: str = ""):
        """Play sound for a message received from another user."""
        self.play_sound()

    def notify_user_joined(self, username: str):
        pass

    def notify_user_left(self, username: str):
        pass
