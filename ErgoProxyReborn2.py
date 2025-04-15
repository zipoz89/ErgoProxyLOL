import threading
import time
import random

# ----- Script 1: Virtual Toggle Key (using keyboard and mouse modules) -----
import keyboard  # pip install keyboard
import mouse     # pip install mouse

RANGE_TOGGLE_KEY = 'c'       # The key that toggles the virtual press.
VIRTUAL_KEY = 'p'      # The key to be virtually pressed/released.

CAMERA_SPACE_TOGGLE_KEY = '['       # 


range_toggle_state = False   # Global toggle state
camera_space_toggle_state = False   # Global toggle state

def toggle_range_virtual_key():
    global range_toggle_state
    if range_toggle_state:
        keyboard.release(VIRTUAL_KEY)
        print(f"Released virtual key '{VIRTUAL_KEY}'")
        range_toggle_state = False
    else:
        keyboard.press(VIRTUAL_KEY)
        print(f"Pressed virtual key '{VIRTUAL_KEY}'")
        range_toggle_state = True

# def toggle_cpace_virtual_key():
#     global camera_space_toggle_state
#     print(f"halooo")
#     if camera_space_toggle_state:
#         print(f"camera space local")
#         release_localSpace()
#         camera_space_toggle_state = False
#     else:
#         keyboard.press(VIRTUAL_KEY)
#         print(f"Precamera space world")
#         camera_space_toggle_state = True


# ----- Script 2: Dynamic Key Mapping with Double-Click Reset (using pynput) -----
from pynput import keyboard as pkb, mouse as pmouse  # pip install pynput

DEBUG = True
def log(msg):
    if DEBUG:
        print(msg)

# Parameters for double-click behavior and delay
REHOLD_DELAY_MIN = 0.01
REHOLD_DELAY_MAX = 0.02
double_click_threshold = 0.3

# Controllers for keyboard and mouse events
kbd_controller = pkb.Controller()
# mouse_controller not used in the code below, but you could use pmouse.Controller() if needed

# --- Space-O Functionality ---
o_pressed = False
def press_localSpace():
    global o_pressed
    if not o_pressed:
        kbd_controller.press('l')
        o_pressed = True
        log("Pressed l")
def release_localSpace():
    global o_pressed
    if o_pressed:
        kbd_controller.release('l')
        o_pressed = False
        log("Released l")

# Dynamic key mapping (example: pressing 'q','w','e','r' with Shift held triggers proxy keys)
key_mapping = {
    'q': '5',
    'w': '6',
    'e': '7',
    'r': '8'
}
active_monitored = set()  # Keys currently active
shift_pressed = False

# Variables for double-click detection
double_click_last_time = None
double_click_timer = None
double_click_keys_snapshot = []

def rehold_proxies(keys_snapshot):
    for ch in keys_snapshot:
        if ch in active_monitored and shift_pressed:
            delay = random.uniform(REHOLD_DELAY_MIN, REHOLD_DELAY_MAX)
            threading.Timer(delay, lambda c=ch: (
                kbd_controller.press(key_mapping[c]),
                log(f"Re-pressed proxy for '{c}' (mapped to '{key_mapping[c]}') after double-click")
            )).start()

def on_click(x, y, button, pressed):
    global double_click_last_time, double_click_timer, double_click_keys_snapshot
    log(f"Mouse event: {button}, pressed: {pressed} at ({x}, {y})")
    if pressed and button in (pmouse.Button.left, pmouse.Button.right):
        if shift_pressed and active_monitored:
            current_time = time.time()
            if (double_click_last_time is None or 
                (current_time - double_click_last_time) > double_click_threshold):
                double_click_last_time = current_time
                double_click_keys_snapshot = list(active_monitored)
                log("First mouse click detected for double-click sequence, snapshot: " + str(double_click_keys_snapshot))
                for ch in double_click_keys_snapshot:
                    try:
                        kbd_controller.release(key_mapping[ch])
                        log(f"Released proxy for '{ch}' (mapped to '{key_mapping[ch]}') on first click")
                    except Exception as e:
                        log(f"Error releasing proxy for '{ch}': {e}")
                double_click_timer = threading.Timer(double_click_threshold, 
                                                       lambda: (rehold_proxies(double_click_keys_snapshot),
                                                                log("Timer expired: proxies re-held for keys " + str(double_click_keys_snapshot))))
                double_click_timer.start()
            else:
                if double_click_timer is not None:
                    double_click_timer.cancel()
                    double_click_timer = None
                log("Second mouse click detected in double-click sequence")
                rehold_proxies(double_click_keys_snapshot)
                double_click_last_time = None
                double_click_keys_snapshot = []

def on_press(key):
    global shift_pressed
    if key == CAMERA_SPACE_TOGGLE_KEY:
        camera_space_toggle_state = not camera_space_toggle_state
        log('CAMERA_SPACE_TOGGLE_KEY')
    if key in (pkb.Key.shift, pkb.Key.shift_r):
        shift_pressed = True
        log("Shift pressed")
    # if key == pkb.Key.space and camera_space_toggle_state:
    #     release_localSpace()
    try:
        char = key.char.lower()
    except AttributeError:
        return
    if char in key_mapping:
        if shift_pressed and char not in active_monitored:
            active_monitored.add(char)
            kbd_controller.press(key_mapping[char])
            log(f"Pressed proxy '{key_mapping[char]}' for '{char}' because Shift is held")

def on_release(key):
    global shift_pressed
    if key in (pkb.Key.shift, pkb.Key.shift_r):
        shift_pressed = False
        log("Shift released")
        for ch in list(active_monitored):
            try:
                kbd_controller.release(key_mapping[ch])
                log(f"Released proxy '{key_mapping[ch]}' for '{ch}' due to Shift release")
            except Exception as e:
                log(f"Error releasing proxy for '{ch}': {e}")
        active_monitored.clear()
    # if key == pkb.Key.space and camera_space_toggle_state:
    #     press_localSpace()
    try:
        char = key.char.lower()
    except AttributeError:
        return
    if char in key_mapping and char in active_monitored:
        try:
            kbd_controller.release(key_mapping[char])
            log(f"Released proxy '{key_mapping[char]}' for '{char}' because key was released")
        except Exception as e:
            log(f"Error releasing proxy for '{char}': {e}")
        active_monitored.remove(char)


# ----- Main Execution: Run Both Functionalities Concurrently -----
if __name__ == '__main__':
    keyboard.add_hotkey(RANGE_TOGGLE_KEY, toggle_range_virtual_key)
    # keyboard.add_hotkey(CAMERA_SPACE_TOGGLE_KEY, toggle_cpace_virtual_key)
    keyboard_listener = pkb.Listener(on_press=on_press, on_release=on_release)
    mouse_listener = pmouse.Listener(on_click=on_click)
    keyboard_listener.start()
    mouse_listener.start()
    keyboard_listener.join()
    mouse_listener.join()
    keyboard.wait()  # Keep this loop running
