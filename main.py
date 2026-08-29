import os
import sys
import time
import re
from datetime import datetime

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    GREEN = Fore.GREEN
    CYAN = Fore.CYAN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    MAGENTA = Fore.MAGENTA
    BOLD = Style.BRIGHT
    RESET = Style.RESET_ALL
except ImportError:
    GREEN = ""
    CYAN = ""
    YELLOW = ""
    RED = ""
    MAGENTA = ""
    BOLD = ""
    RESET = ""

import config
from unfollower import InstagramUnfollower


def print_banner():
    banner = f"""
{CYAN}{BOLD}======================================================================
     AUTO UNFOLLOW INSTAGRAM (NON-FOLLBACK DETECTOR & CLEANER)
     Brave Browser Edition (Linux Mint)
======================================================================{RESET}
"""
    print(banner)


def show_menu():
    print(f"{BOLD}SELECT MENU:{RESET}")
    print(f" {GREEN}[1]{RESET} 🔍 Scan & Display Non-Follback Accounts (Analysis Only)")
    print(f" {YELLOW}[2]{RESET} 🧪 Run Auto Unfollow ({BOLD}DRY-RUN / Simulation{RESET})")
    print(f" {RED}[3]{RESET} 🚀 Run Auto Unfollow ({BOLD}REAL MODE{RESET})")
    print(f" {CYAN}[4]{RESET} 📋 View & Manage Whitelist (Protected Accounts)")
    print(f" {MAGENTA}[5]{RESET} ⚙️  Check Configuration & Brave Linux Mint Guide")
    print(f" [0] 🚪 Exit")
    print()


def view_whitelist():
    print(f"\n{CYAN}{BOLD}=== WHITELIST LIST (PROTECTED ACCOUNTS) ==={RESET}")
    whitelist = config.load_whitelist()
    if not whitelist:
        print(f"{YELLOW}Whitelist is currently empty. You can add usernames to 'whitelist.txt'.{RESET}")
    else:
        print(f"Total accounts in Whitelist: {len(whitelist)}")
        for idx, user in enumerate(sorted(whitelist), 1):
            print(f"  {idx}. @{user}")
    print(f"\n{GREEN}[i] Edit file '{config.WHITELIST_FILE}' to add/remove accounts.{RESET}\n")


def check_config_info():
    print(f"\n{MAGENTA}{BOLD}=== SYSTEM CONFIGURATION INFORMATION ==={RESET}")
    print(f"• Automation Profile  : {config.AUTOMATION_PROFILE_DIR}")
    print(f"• Browser Profile     : {config.BRAVE_PROFILE_DIR}")
    print(f"• Brave Binary Path   : {config.BRAVE_BINARY_PATH}")
    print(f"• Display Mode        : {'Headless' if config.HEADLESS_MODE else 'GUI (Open Window)'}")
    print(f"• Max Unfollow / Batch: {config.MAX_UNFOLLOW_LIMIT} accounts")
    print(f"• Random Safety Delay : {config.MIN_DELAY_SECONDS}s - {config.MAX_DELAY_SECONDS}s")
    print(f"• Whitelist File      : {config.WHITELIST_FILE}")
    print()
    print(f"{BOLD}Batch & Account Safety Features:{RESET}")
    print(f"1. Each batch processes up to {config.MAX_UNFOLLOW_LIMIT} accounts.")
    print(f"2. After one batch finishes, you can immediately proceed to the next batch")
    print(f"   {GREEN}without closing the browser and without re-scanning from scratch{RESET}.")
    print(f"3. You can also add a rest break delay between batches for account safety.")
    print()


def save_results_to_file(non_followers: list, my_username: str):
    """Saves scan results to a txt file for user reference."""
    filename = f"non_followers_{my_username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Non-Follback Account List for @{my_username}\n")
            f.write(f"# Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total: {len(non_followers)} accounts\n\n")
            for u in non_followers:
                f.write(f"{u}\n")
        print(f"\n{GREEN}[✓] Non-follback list successfully saved to file: {filename}{RESET}")
    except Exception as e:
        print(f"{YELLOW}[!] Failed to save scan result file: {e}{RESET}")


def run_process(mode: str):
    """
    mode:
    - 'scan': scan and display only
    - 'dry_run': scan then simulate unfollow
    - 'real': scan then real unfollow
    """
    is_dry_run = (mode != "real")
    unfollower = InstagramUnfollower(dry_run=is_dry_run)

    try:
        print(f"\n{CYAN}[*] Initializing Brave Browser...{RESET}")
        unfollower.init_driver()

        # Check login status
        if not unfollower.check_login():
            print(f"{RED}[✗] Process cancelled because user is not logged in.{RESET}")
            return

        my_user = unfollower.get_my_username()
        print(f"\n{GREEN}{BOLD}[*] Starting account scan for: @{my_user}{RESET}")

        # Scan Following & Followers
        following, followers, non_followers = unfollower.scan_non_followers()

        print("\n" + "="*50)
        print(f"{BOLD}INSTAGRAM SCAN RESULTS:{RESET}")
        print(f"• Total Following (You follow) : {CYAN}{len(following)}{RESET}")
        print(f"• Total Followers (Follow you) : {GREEN}{len(followers)}{RESET}")
        print(f"• Not Following Back           : {RED}{len(non_followers)}{RESET}")
        print("="*50)

        if not non_followers:
            print(f"\n{GREEN}[✓] Great! All accounts you follow are following back, or protected by whitelist.{RESET}\n")
            return

        # Save scan results to log file
        save_results_to_file(non_followers, my_user)

        # Display non-follback list
        print(f"\n{YELLOW}{BOLD}List of Accounts Not Following Back ({len(non_followers)} accounts):{RESET}")
        for i, u in enumerate(non_followers[:50], 1):
            print(f"  {i}. @{u}")
        if len(non_followers) > 50:
            print(f"  ... and {len(non_followers) - 50} other accounts (saved to txt file).")

        if mode == "scan":
            print(f"\n{GREEN}[✓] Scan complete! Use Menu 2 or 3 to proceed with unfollowing.{RESET}\n")
            return

        # Initial confirmation for Real Mode before starting execution
        if mode == "real":
            print(f"\n{RED}{BOLD}[REAL MODE WARNING]{RESET}")
            print(f"You are about to start {RED}REAL UNFOLLOWING{RESET} in batches.")
            print(f"Each batch will process up to {config.MAX_UNFOLLOW_LIMIT} accounts.")
            confirm = input(f"Type '{BOLD}YES{RESET}' (or 'YA') to start or press Enter to cancel: ").strip()
            if confirm.upper() not in ["YES", "Y", "YA"]:
                print(f"{YELLOW}[!] Cancelled by user.{RESET}\n")
                return

        remaining_targets = list(non_followers)
        total_success = 0
        total_failed = 0
        batch_number = 1
        action_blocked = False

        while remaining_targets and not action_blocked:
            batch_limit = config.MAX_UNFOLLOW_LIMIT
            current_batch = remaining_targets[:batch_limit]
            
            print("\n" + "="*55)
            print(f"{CYAN}{BOLD}BATCH #{batch_number}: Processing {len(current_batch)} accounts (Remaining queue: {len(remaining_targets)} accounts){RESET}")
            print("="*55)

            for idx, target in enumerate(current_batch, 1):
                global_idx = total_success + total_failed + 1
                print(f"\n[{idx}/{len(current_batch)}] (Total Account #{global_idx}) Processing @{target}...")
                success, msg = unfollower.unfollow_user(target)
                if success:
                    total_success += 1
                    print(f"  {GREEN}[✓] {msg}{RESET}")
                else:
                    total_failed += 1
                    print(f"  {YELLOW}[!] {msg}{RESET}")
                    if "[WARNING]" in msg or "Action Block" in msg or "restricted by Instagram" in msg or "[PERINGATAN]" in msg:
                        action_blocked = True
                        print(f"\n{RED}{BOLD}[!] ACCOUNT SAFETY WARNING:{RESET}")
                        print(f"{RED}Instagram temporarily restricted unfollow actions (Action Block).{RESET}")
                        print(f"{YELLOW}Automation stopped to protect your account.{RESET}\n")
                        break

            # Remove processed accounts from queue list
            remaining_targets = remaining_targets[len(current_batch):]

            if action_blocked:
                break

            # If all accounts have finished processing
            if not remaining_targets:
                print(f"\n{GREEN}{BOLD}[✓] All non-follback accounts ({len(non_followers)} accounts) have been processed!{RESET}")
                break

            # Display summary of completed batch
            print("\n" + "-"*50)
            print(f"{BOLD}Batch #{batch_number} Complete!{RESET}")
            print(f"• Total successfully unfollowed so far: {GREEN}{total_success}{RESET}")
            print(f"• Remaining accounts to unfollow     : {CYAN}{len(remaining_targets)}{RESET} accounts")
            print("-" * 50)

            # Prompt user to continue to next batch without exiting browser & without re-scanning
            next_count = min(config.MAX_UNFOLLOW_LIMIT, len(remaining_targets))
            print(f"\n{BOLD}[?] Continue to Batch #{batch_number + 1} (next {next_count} accounts)?{RESET}")
            print(f" {GREEN}[Y / Enter]{RESET} Proceed immediately now (no browser restart & no re-scan)")
            print(f" {YELLOW}[J <seconds>]{RESET} Take a rest break first (e.g. 'J 30' for 30s delay) then continue")
            print(f" {RED}[N]{RESET}        Done / Stop (return to main menu)")

            choice = input(f"\n{BOLD}Your choice [Y/n/delay]: {RESET}").strip().lower()

            if choice in ["", "y", "ya", "yes", "1", "continue", "lanjut"]:
                batch_number += 1
                continue
            elif choice.startswith("j"):
                # Parse delay time (e.g. "j 30", "delay 60", "j30")
                match = re.search(r"\d+", choice)
                delay_sec = int(match.group()) if match else 30
                print(f"\n{YELLOW}[*] Taking a break for {delay_sec} seconds...{RESET}")
                try:
                    for s in range(delay_sec, 0, -1):
                        print(f"    Resuming in {s} seconds...", end="\r")
                        time.sleep(1)
                    print(f"    Resuming to Batch #{batch_number + 1} now!             ")
                except KeyboardInterrupt:
                    print(f"\n{YELLOW}[!] Break skipped, proceeding directly to next batch.{RESET}")
                batch_number += 1
                continue
            elif choice in ["n", "no", "tidak", "cancel", "batal", "0", "exit", "keluar"]:
                print(f"\n{YELLOW}[*] Process stopped by user. Remaining {len(remaining_targets)} accounts kept in list.{RESET}")
                break
            else:
                print(f"\n{YELLOW}[*] Session ended. Returning to main menu.{RESET}")
                break

        print("\n" + "="*50)
        print(f"{BOLD}TOTAL EXECUTION SUMMARY:{RESET}")
        print(f"• Total Batches Executed : {BOLD}{batch_number}{RESET}")
        print(f"• Successfully Unfollowed: {GREEN}{total_success}{RESET}")
        print(f"• Failed / Skipped       : {YELLOW}{total_failed}{RESET}")
        print(f"• Remaining Accounts     : {CYAN}{len(remaining_targets)}{RESET}")
        print(f"• Mode                   : {YELLOW if is_dry_run else RED}{'DRY RUN (Simulation)' if is_dry_run else 'REAL MODE'}{RESET}")
        print("="*50 + "\n")

    except KeyboardInterrupt:
        print(f"\n{YELLOW}[!] Process interrupted by user (Ctrl+C).{RESET}\n")
    except Exception as e:
        print(f"\n{RED}[✗] An error occurred: {e}{RESET}\n")
    finally:
        unfollower.close()


def main():
    while True:
        print_banner()
        show_menu()
        choice = input(f"{BOLD}Enter choice [0-5]: {RESET}").strip()

        if choice == "1":
            run_process(mode="scan")
        elif choice == "2":
            run_process(mode="dry_run")
        elif choice == "3":
            run_process(mode="real")
        elif choice == "4":
            view_whitelist()
        elif choice == "5":
            check_config_info()
        elif choice == "0":
            print(f"\n{GREEN}Thank you for using Auto Unfollow IG! Goodbye.{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{RED}[!] Invalid choice, please try again.{RESET}\n")

        input(f"{CYAN}Press Enter to return to main menu...{RESET}")


if __name__ == "__main__":
    main()
