# 🚀 Auto Unfollow Instagram (Non-Follback Cleaner) - Brave Browser on Linux Mint

Smart Python automation script to detect and unfollow Instagram accounts that **do not follow back (non-follback)** using a logged-in **Brave Browser** profile session on **Linux Mint**.

---

## 🌟 Key Features

- **Continuous Batch Unfollow (No Re-Scan & No Browser Restart)**:
  After 1 batch (e.g., 25 accounts) completes unfollowing, you can instantly proceed to the next batch or add a break delay without exiting the program, reopening the browser, or re-scanning followers/following from scratch.
- **Permanent Automation Profile Session**: Login sessions are permanently stored in an isolated automation directory so your main Brave browser can be used freely anytime.
- **Automatic Username Detection**: Automatically detects the logged-in Instagram account.
- **Accurate & Fast Non-Follback Detection**: Scans all *Followers* & *Following* via internal Web API/GraphQL instantly.
- **Whitelist Support**: Important accounts (friends, family, idols, brands) listed in `whitelist.txt` will never be unfollowed.
- **Simulation Mode (Dry-Run)**: Test the scanning process and view unfollow simulations without actual clicks.
- **Safety Features (Anti-Ban & Anti Action-Block)**:
  - Random safety delay between unfollow actions.
  - Batch processing (default: 25 accounts) and automatic Action Block (*Try Again Later*) detection.
- **Multi-language UI Support**: Supports both Indonesian and English Instagram user interfaces.
- **Export Results**: Automatically saves non-follback account lists to a `.txt` file complete with scan timestamp.

---

## 📁 Directory Structure

```
auto-unfollow-ig/
├── config.py             # Configuration file (Brave Linux Mint settings, limits, delays, whitelist)
├── unfollower.py         # Core Instagram scraping & unfollowing module
├── main.py               # Main program with colorful interactive CLI menu
├── whitelist.txt         # List of protected accounts
├── requirements.txt      # Required Python dependencies
└── README.md             # Complete documentation and instructions
```

---

## 🛠️ System Requirements

- **OS**: Linux Mint / Ubuntu / Debian-based
- **Python**: Python 3.9+
- **Browser**: Brave Browser (`/usr/bin/brave-browser`)

---

## 📦 Installation & Usage

1. **Open Terminal in Project Directory**:
   ```bash
   cd unfollow-ig
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Main Program**:
   ```bash
   python3 main.py
   ```

---

## 🎮 CLI Menu Options

```
======================================================================
     AUTO UNFOLLOW INSTAGRAM (NON-FOLLBACK DETECTOR & CLEANER)
     Brave Browser Edition (Linux Mint)
======================================================================

SELECT MENU:
 [1] 🔍 Scan & Display Non-Follback Accounts (Analysis Only)
 [2] 🧪 Run Auto Unfollow (DRY-RUN / Simulation)
 [3] 🚀 Run Auto Unfollow (REAL MODE)
 [4] 📋 View & Manage Whitelist (Protected Accounts)
 [5] ⚙️  Check Configuration & Brave Linux Mint Guide
 [0] 🚪 Exit
```

- **Menu 1**: Scans your followers & following, matches non-followers, displays results on screen, and exports to a `.txt` file.
- **Menu 2**: Simulates step-by-step unfollow execution (batch) without real clicks.
- **Menu 3**: Performs real unfollow actions per batch with options to proceed to the next batch immediately or take a break delay.
- **Menu 4**: Views accounts protected by `whitelist.txt`.
- **Menu 5**: Views configuration details and automation profile directory info.

---

## ⚙️ Settings in `config.py`

| Parameter | Description | Default |
| :--- | :--- | :--- |
| `AUTOMATION_PROFILE_DIR` | Dedicated automation profile directory | `~/.config/auto-unfollow-ig-brave` |
| `BRAVE_PROFILE_DIR` | Profile name used | `"Default"` |
| `HEADLESS_MODE` | Hide browser window | `False` |
| `MAX_UNFOLLOW_LIMIT` | Max unfollow accounts per batch | `25` |
| `MIN_DELAY_SECONDS` | Minimum delay between unfollows | `1` second |
| `MAX_DELAY_SECONDS` | Maximum delay between unfollows | `2` seconds |
| `WHITELIST_FILE` | Protected accounts list file | `"whitelist.txt"` |

---

## 🛡️ Safety Tips to Avoid Instagram Action Blocks

1. **Use Batching**: Perform unfollows gradually per batch (e.g., 25 accounts per batch).
2. **Add Delays Between Batches**: Use pause/break options (e.g., `J 30` to rest for 30-60 seconds) before continuing to the next batch.
3. **Populate Whitelist**: Add close friends, public figures, or business accounts to `whitelist.txt`.

