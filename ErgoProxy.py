import threading
import random
import time
from pynput import keyboard, mouse

### DEBUGGING (set to False to disable logging) ###
DEBUG = True
def log(msg):
    if DEBUG:
        print(msg)

### PARAMETERS ###

# Shift Mode (dynamic mapping + double-click)
REHOLD_DELAY_MIN = 0.01   # seconds before re-holding each proxy key
REHOLD_DELAY_MAX = 0.05   # seconds before re-holding each proxy key
double_click_threshold = 0.3  # seconds: maximum interval for a double-click

# Normal Mode (auto-repeat on tap)
tap_threshold   = 0.1   # maximum duration (seconds) to consider a press a "tap"o
repeat_delay    = 0.5   # delay (seconds) after tap before auto-repeat starts
repeat_count    = 10    # number of auto-repeat presses
repeat_interval = 0.05  # interval (seconds) between auto-repeat presses

### CONTROLLERS ###
kbd = keyboard.Controller()
mouse_controller = mouse.Controller()

### SPACE - O FUNCTIONALITY ###
o_pressed = False
def press_o():
    global o_pressed
    if not o_pressed:
        kbd.press('o')
        o_pressed = True
        log("Pressed O")
def release_o():
    global o_pressed
    if o_pressed:
        kbd.release('o')
        o_pressed = False
        log("Released O")
# Start with O held down.
press_o()

### KEY MAPPING ###
# In Shift mode, map letters to proxy keys (e.g. Q -> Numpad 1, etc.)
key_mapping = {
    'q': '6',
    'w': '7',
    'e': '8',
    'r': "9"
}

### STATE TRACKING ###
active_monitored = set()   # Keys currently active in Shift mode (e.g. 'q', 'w', etc.)
shift_pressed = False      # True when either Shift key is held down
normal_press_times = {}    # Records physical press time for each key (normal mode)

# To prevent auto-repeat simulated events from re-triggering auto-repeat,
# we maintain a set of keys that are currently being simulated.o o o
auto_repeat_simulating = set()

# Double-click tracking for Shift mode:
double_click_last_time = None
double_click_timer = None
double_click_keys_snapshot = []

### FUNCTIONS ###

def rehold_proxies(keys_snapshot):
    """Re-press proxy keys for each key in snapshot if still active and Shift is held."""
    for ch in keys_snapshot:
        if ch in active_monitored and shift_pressed:
            delay = random.uniform(REHOLD_DELAY_MIN, REHOLD_DELAY_MAX)
            threading.Timer(delay, lambda c=ch: (
                kbd.press(key_mapping[c]),
                log(f"Re-pressed proxy for '{c}' after double-click")
            )).start()

def auto_repeat(char):
    """Simulate auto-repeat for the given character key.
    This function marks the key as being simulated so that listener events are ignored."""
    auto_repeat_simulating.add(char)
    time.sleep(repeat_delay)
    log(f"Auto-repeat: repeating '{char}' {repeat_count} times")
    for _ in range(repeat_count):
        kbd.press(char)
        kbd.release(char)
        time.sleep(repeat_interval)
    auto_repeat_simulating.discard(char)

### KEYBOARD EVENT HANDLERS ###

def on_press(key):
    global shift_pressed
    # Try to extract a lowercase character (if applicable)
    try:
        char = key.char.lower()
    except AttributeError:
        char = None

    # If this key is auto-repeated (simulated), ignore it.
    if char and char in auto_repeat_simulating:
        return

    # Detect Shift press (either left or right)
    if key in (keyboard.Key.shift, keyboard.Key.shift_r):
        shift_pressed = True
        log("Shift pressed")
    
    # Space - O behavior
    if key == keyboard.Key.space:
        release_o()
        return
    
    # Process mapped keys:
    if char in key_mapping:
        if shift_pressed:
            # SHIFT MODE: Only process a physical press
            if char not in active_monitored:
                active_monitored.add(char)
                kbd.press(key_mapping[char])
                log(f"Shift-mode: Pressed proxy '{key_mapping[char]}' for '{char}'")
        else:
            # NORMAL MODE: Record physical press time (only if not already simulating)
            if char not in auto_repeat_simulating:
                normal_press_times[char] = time.time()
                log(f"Normal-mode: Recorded press time for '{char}'")

def on_release(key):
    global shift_pressed, double_click_last_time, double_click_timer
    try:
        char = key.char.lower()
    except AttributeError:
        char = None

    if key in (keyboard.Key.shift, keyboard.Key.shift_r):
        shift_pressed = False
        log("Shift released")
        # Release all active proxies in Shift mode.
        for ch in list(active_monitored):
            try:
                kbd.release(key_mapping[ch])
                log(f"Shift-mode: Released proxy for '{ch}' due to shift release")
            except Exception as e:
                log(f"Error releasing proxy for '{ch}': {e}")
        active_monitored.clear()
        return

    if key == keyboard.Key.space:
        press_o()
        return

    if char and char in key_mapping:
        if shift_pressed:
            # SHIFT MODE: On key release, release its proxy.
            if char in active_monitored:
                kbd.release(key_mapping[char])
                active_monitored.remove(char)
                log(f"Shift-mode: Released proxy '{key_mapping[char]}' for '{char}' on key release")
        else:
            # NORMAL MODE (Auto-repeat on tap):
            # Ignore release if this key is currently being auto-repeated.
            if char in auto_repeat_simulating:
                return
            press_time = normal_press_times.get(char)
            if press_time is not None:
                duration = time.time() - press_time
                if duration < tap_threshold:
                    log(f"Normal-mode: '{char}' tapped (duration {duration:.2f}s), scheduling auto-repeat")
                    threading.Thread(target=auto_repeat, args=(char,), daemon=True).start()
                else:
                    log(f"Normal-mode: '{char}' held for {duration:.2f}s; auto-repeat not triggered")
                normal_press_times.pop(char, None)

### MOUSE EVENT HANDLER (for Shift-mode double-click) ###
def on_click(x, y, button, pressed):
    global double_click_last_time, double_click_timer, double_click_keys_snapshot
    log(f"Mouse event: {button}, pressed: {pressed} at ({x}, {y})")
    if pressed and button in (mouse.Button.left, mouse.Button.right):
        if shift_pressed and active_monitored:
            current_time = time.time()
            if (double_click_last_time is None or 
                (current_time - double_click_last_time) > double_click_threshold):
                # First click of potential double-click.
                double_click_last_time = current_time
                double_click_keys_snapshot = list(active_monitored)
                log("Shift-mode: First mouse click detected for double-click, snapshot: " + str(double_click_keys_snapshot))
                for ch in double_click_keys_snapshot:
                    try:
                        kbd.release(key_mapping[ch])
                        log(f"Shift-mode: Released proxy for '{ch}' on first mouse click")
                    except Exception as e:
                        log(f"Error releasing proxy for '{ch}': {e}")
                double_click_timer = threading.Timer(double_click_threshold, 
                                                       lambda: (rehold_proxies(double_click_keys_snapshot),
                                                                log("Shift-mode: Double-click timer expired, re-holding proxies")))
                double_click_timer.start()
            else:
                # Second click detected within threshold.
                if double_click_timer is not None:
                    double_click_timer.cancel()
                    double_click_timer = None
                double_click_last_time = None
                log("Shift-mode: Second mouse click detected for double-click")
                rehold_proxies(double_click_keys_snapshot)
                double_click_keys_snapshot = []

### SETUP LISTENERS ###
keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
mouse_listener    = mouse.Listener(on_click=on_click)

keyboard_listener.start()
mouse_listener.start()

keyboard_listener.join()
mouse_listener.join()
