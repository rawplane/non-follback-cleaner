import os
import shutil

# ==============================================================================
# BRAVE BROWSER CONFIGURATION ON LINUX MINT
# ==============================================================================

# Custom Automation Profile Directory Location
# This profile permanently and securely stores your Instagram login session
# without interfering with or being affected by your main Brave browser.
AUTOMATION_PROFILE_DIR = os.path.expanduser("~/.config/auto-unfollow-ig-brave")

# Profile Name used
BRAVE_PROFILE_DIR = "Default"

# Location of Brave Browser binary in Linux Mint / Debian-based Linux
def find_brave_binary() -> str:
    possible_paths = [
        "/usr/bin/brave-browser",
        "/usr/bin/brave-browser-stable",
        "/opt/brave.com/brave/brave-browser",
        "/usr/bin/brave",
        os.path.expanduser("~/.local/share/flatpak/exports/bin/com.brave.Browser"),
        "/var/lib/flatpak/exports/bin/com.brave.Browser",
        "/snap/bin/brave",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Fallback to shutil.which if available in PATH
    which_path = shutil.which("brave-browser") or shutil.which("brave")
    if which_path:
        return which_path

    return "/usr/bin/brave-browser"

BRAVE_BINARY_PATH = find_brave_binary()

# Display browser window while automation runs (False = visible window, True = background/headless)
HEADLESS_MODE = False

# Manual Remote Debugging Mode (Optional):
USE_REMOTE_DEBUGGING = False
REMOTE_DEBUGGING_PORT = 9222


# ==============================================================================
# INSTAGRAM & AUTO UNFOLLOW CONFIGURATION
# ==============================================================================

# Your Instagram Username (leave empty "" to auto-detect upon login)
INSTAGRAM_USERNAME = ""

# Maximum number of accounts to unfollow in a single batch.
# IMPORTANT: Instagram limits unfollows to around 15-25 accounts per batch/session
# to avoid Action Blocks ("Try Again Later"). After 1 batch completes,
# you can directly choose to continue to the next batch without closing the browser & without re-scanning.
MAX_UNFOLLOW_LIMIT = 25

# Random wait time (seconds) between unfollow actions (Safety Human-like Delay)
# Prevents automatic bot detection by Instagram (minimum 8-18 seconds recommended)
MIN_DELAY_SECONDS = 1
MAX_DELAY_SECONDS = 2

# Scroll delay time for follower/following modal (seconds)
SCROLL_DELAY_SECONDS = 1.8

# Web element timeout wait time (seconds)
PAGE_TIMEOUT_SECONDS = 25

# Default Simulation Mode (Dry Run)
# True  = Simulation only without actual unfollow clicks.
# False = Real execution.
DEFAULT_DRY_RUN = False


# ==============================================================================
# WHITELIST LIST (ACCOUNTS THAT WILL NEVER BE UNFOLLOWED)
# ==============================================================================

# External file to store the whitelist (one username per line)
WHITELIST_FILE = "whitelist.txt"

# Additional whitelist directly in config (all lowercase, without @ symbol)
# Example: ["instagram", "natgeo", "close_friend"]
CONFIG_WHITELIST = [
    # "instagram",
    # "cristiano",
]


def load_whitelist() -> set:
    """Reads the whitelist set from file and config."""
    whitelist = {u.strip().lower().lstrip("@") for u in CONFIG_WHITELIST if u.strip()}
    
    if os.path.exists(WHITELIST_FILE):
        try:
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    clean_line = line.strip().lower()
                    if clean_line and not clean_line.startswith("#"):
                        whitelist.add(clean_line.lstrip("@"))
        except Exception as e:
            print(f"[Warning] Failed to read {WHITELIST_FILE}: {e}")
            
    return whitelist
