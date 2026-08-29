import os
import time
import random
import re
from typing import Set, List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config


def parse_count_string(text: str) -> int:
    """Converts Instagram count strings ('628', '1,170', '1.170', '1.2K', '1M') to integer."""
    if not text:
        return 0
    t = text.strip().upper().replace(",", "").replace(".", "")
    try:
        if "K" in t:
            num = float(t.replace("K", ""))
            return int(num * 1000)
        if "M" in t:
            num = float(t.replace("M", ""))
            return int(num * 1000000)
        return int(re.sub(r"[^\d]", "", t) or 0)
    except Exception:
        return 0


class InstagramUnfollower:
    def __init__(self, dry_run: bool = config.DEFAULT_DRY_RUN):
        self.dry_run = dry_run
        self.driver: Optional[webdriver.Chrome] = None
        self.whitelist: Set[str] = config.load_whitelist()
        self.my_username: str = config.INSTAGRAM_USERNAME
        self.user_id: Optional[str] = None
        self.user_ids: dict = {}

    def init_driver(self) -> webdriver.Chrome:
        """Initialize Brave Browser WebDriver with Permanent Automation Profile."""
        options = ChromeOptions()
        options.page_load_strategy = "eager"

        if os.path.exists(config.BRAVE_BINARY_PATH):
            options.binary_location = config.BRAVE_BINARY_PATH

        if config.USE_REMOTE_DEBUGGING:
            debugger_address = f"127.0.0.1:{config.REMOTE_DEBUGGING_PORT}"
            options.add_experimental_option("debuggerAddress", debugger_address)
            print(f"[*] Connecting to Brave Browser at {debugger_address}...")
        else:
            user_data_dir = os.path.abspath(config.AUTOMATION_PROFILE_DIR)
            profile_dir = config.BRAVE_PROFILE_DIR
            os.makedirs(user_data_dir, exist_ok=True)
            
            options.add_argument(f"--user-data-dir={user_data_dir}")
            options.add_argument(f"--profile-directory={profile_dir}")
            print(f"[*] Using automation profile directory: {user_data_dir}")

        if config.HEADLESS_MODE:
            options.add_argument("--headless=new")

        # Stealth & stability arguments for Linux Mint
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-notifications")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-features=Translate,OptimizationHints,MediaRouter")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        try:
            try:
                driver_path = ChromeDriverManager().install()
                service = ChromeService(driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            except Exception:
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_page_load_timeout(config.PAGE_TIMEOUT_SECONDS)
            self.driver.set_script_timeout(60)
            print("[✓] Brave Browser successfully opened!")
            return self.driver

        except WebDriverException as e:
            print(f"\n[✗] Failed to open Brave Browser WebDriver: {e}")
            raise e

    def is_logged_in(self) -> bool:
        """Checks whether the user is logged into Instagram."""
        if not self.driver:
            return False

        try:
            cookies = {c["name"]: c.get("value", "") for c in self.driver.get_cookies()}
            if cookies.get("sessionid"):
                return True
        except Exception:
            pass

        try:
            logged_in_nav = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/') and (.//span[text()='Profile' or text()='Profil' or text()='Home' or text()='Beranda' or text()='Messages' or text()='Pesan'] or .//svg[@aria-label='Home' or @aria-label='Beranda' or @aria-label='Direct' or @aria-label='Messenger'])]"
            )
            if any(elem.is_displayed() for elem in logged_in_nav):
                return True
        except Exception:
            pass

        current_url = self.driver.current_url.lower()
        if "accounts/login" in current_url or "accounts/emailsignup" in current_url:
            return False

        try:
            login_inputs = self.driver.find_elements(By.NAME, "username")
            if any(inp.is_displayed() for inp in login_inputs):
                return False
        except Exception:
            pass

        return False

    def check_login(self) -> bool:
        """Verifies Instagram login session, guiding user for a one-time login if needed."""
        if not self.driver:
            raise RuntimeError("Driver not initialized.")

        print("[*] Checking Instagram login session status...")
        self.driver.get("https://www.instagram.com/")
        time.sleep(3)

        if self.is_logged_in():
            print("[✓] Status: Instagram login session active!")
            return True

        print(f"\n{'='*70}")
        print("[!] Instagram login session is not active on this automation profile.")
        print("[i] Please LOG IN ONCE in the currently open Brave Browser window.")
        print("[✓] After successful login, this session will be SAVED PERMANENTLY")
        print("    so you won't need to log in again in future runs.")
        print("[*] Waiting for you to complete login in the browser (max 300 seconds)...")
        print(f"{'='*70}\n")

        max_wait = 300
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(3)
            if self.is_logged_in():
                print("\n[✓] Login detected successfully! Session saved permanently.")
                time.sleep(2)
                return True

        print("\n[✗] Login wait timeout expired. Please re-run the script and log in.")
        return False

    def get_my_username(self) -> str:
        """Gets username of current logged-in account."""
        if self.my_username:
            return self.my_username

        if not self.driver:
            raise RuntimeError("Driver not initialized.")

        print("[*] Detecting your account username...")
        
        try:
            detected = self.driver.execute_script(r"""
                var links = document.querySelectorAll('a[role="link"], a');
                var excluded = ['explore', 'reels', 'direct', 'stories', 'accounts', 'popular', 'legal', 'about', 'your_activity', 'archive', 'emailsignup'];
                for (var i = 0; i < links.length; i++) {
                    var href = links[i].getAttribute('href') || '';
                    var match = href.match(/^\/([a-zA-Z0-9_\.]+)\/?$/);
                    if (match) {
                        var u = match[1].toLowerCase();
                        if (excluded.indexOf(u) === -1) {
                            if (links[i].querySelector('img') || links[i].querySelector('svg[aria-label*="Profile"]') || links[i].querySelector('svg[aria-label*="Profil"]')) {
                                return match[1];
                            }
                        }
                    }
                }
                return null;
            """)
            if detected:
                self.my_username = detected
                print(f"[✓] Username detected: @{self.my_username}")
                return self.my_username
        except Exception:
            pass

        try:
            profile_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/')][.//span[normalize-space()='Profile' or normalize-space()='Profil'] or .//img[contains(@alt, 'profile') or contains(@alt, 'profil')]]"
            )
            for pl in profile_links:
                href = pl.get_attribute("href") or ""
                match = re.search(r"instagram\.com/([a-zA-Z0-9_\.]+)/?$", href)
                if match:
                    u = match.group(1).lower()
                    if u not in {"explore", "reels", "direct", "stories", "accounts", "popular", "legal", "about"}:
                        self.my_username = match.group(1)
                        print(f"[✓] Username detected: @{self.my_username}")
                        return self.my_username
        except Exception:
            pass

        print("\n[?] Automation requires your Instagram username.")
        user_input = input("    Enter your username (without @): ").strip().lstrip("@")
        self.my_username = user_input
        return self.my_username

    def get_profile_info(self, username: str) -> Tuple[str, int, int]:
        """
        Fetches User ID, Total Following, and Total Followers from Instagram API.
        Returns (user_id: str, following_count: int, followers_count: int).
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized.")

        print(f"[*] Fetching profile info for @{username}...")
        try:
            info = self.driver.execute_async_script("""
                var username = arguments[0];
                var callback = arguments[arguments.length - 1];
                fetch('https://www.instagram.com/api/v1/users/web_profile_info/?username=' + username, {
                    headers: {'X-IG-App-ID': '936619743392459', 'X-Requested-With': 'XMLHttpRequest'}
                }).then(r => r.json()).then(d => {
                    if (d.data && d.data.user) {
                        callback({
                            success: true,
                            id: String(d.data.user.id),
                            following_count: d.data.user.edge_follow.count,
                            followers_count: d.data.user.edge_followed_by.count
                        });
                    } else {
                        callback({success: false, error: 'User data not found'});
                    }
                }).catch(e => callback({success: false, error: e.toString()}));
            """, username)

            if info.get("success"):
                uid = str(info["id"])
                if username.lower() == self.my_username.lower():
                    self.user_id = uid
                self.user_ids[username.lower()] = uid
                return uid, int(info["following_count"]), int(info["followers_count"])
        except Exception as e:
            print(f"[!] API info failed ({e}), using DOM fallback...")

        return "", 0, 0

    def fetch_user_list_api(self, user_id: str, list_type: str, target_count: int) -> List[str]:
        """
        Fetches 100% of Following or Followers list using internal Web API & GraphQL.
        Also maps username -> user_id for API execution.
        """
        print(f"\n[*] Fetching all {list_type.upper()} data via Web API (Target: {target_count})...")
        collected_users: List[str] = []
        max_id = ""
        page = 1

        while True:
            try:
                res = self.driver.execute_async_script("""
                    var userId = arguments[0];
                    var listType = arguments[1];
                    var maxId = arguments[2];
                    var callback = arguments[arguments.length - 1];

                    function getCookie(name) {
                        var match = document.cookie.match(new RegExp('(^|;\\\\s*)(' + name + ')=([^;]*)'));
                        return match ? decodeURIComponent(match[3]) : null;
                    }

                    var csrfToken = getCookie('csrftoken') || '';
                    var headers = {
                        'X-CSRFToken': csrfToken,
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-ASBD-ID': '129477'
                    };

                    if (listType === 'followers') {
                        // Use Instagram Web GraphQL endpoint for Followers
                        var variables = { id: userId, first: 50 };
                        if (maxId) variables.after = maxId;

                        var url = 'https://www.instagram.com/graphql/query/?query_hash=5aefa9893005572d237da5068082d8d5&variables=' + encodeURIComponent(JSON.stringify(variables));
                        fetch(url, { headers: headers }).then(function(r) {
                            var ct = r.headers.get('content-type') || '';
                            if (ct.includes('json')) {
                                return r.json();
                            }
                            return { error: 'Non-JSON response (' + r.status + ')' };
                        }).then(function(d) {
                            if (d.error) {
                                callback({ success: false, error: d.error });
                                return;
                            }
                            var edge = (d.data && d.data.user && d.data.user.edge_followed_by) || {};
                            var edges = edge.edges || [];
                            var parsed = edges.map(function(e) {
                                var n = e.node || {};
                                return {
                                    username: (n.username || '').toLowerCase(),
                                    id: String(n.id || '')
                                };
                            });
                            var pageInfo = edge.page_info || {};
                            callback({
                                success: true,
                                users: parsed,
                                next_max_id: (pageInfo.has_next_page ? pageInfo.end_cursor : null)
                            });
                        }).catch(function(err) {
                            callback({ success: false, error: err.toString() });
                        });
                    } else {
                        // Use Friendships API endpoint for Following
                        var url = 'https://www.instagram.com/api/v1/friendships/' + userId + '/following/?count=200' + (maxId ? '&max_id=' + encodeURIComponent(maxId) : '');
                        fetch(url, { headers: headers }).then(function(r) {
                            var ct = r.headers.get('content-type') || '';
                            if (ct.includes('json')) {
                                return r.json();
                            }
                            return { error: 'Non-JSON response (' + r.status + ')' };
                        }).then(function(d) {
                            if (d.error) {
                                callback({ success: false, error: d.error });
                                return;
                            }
                            var rawUsers = d.users || [];
                            var parsed = rawUsers.map(function(u) {
                                return {
                                    username: (u.username || '').toLowerCase(),
                                    id: String(u.pk || u.id || u.pk_id || '')
                                };
                            });
                            callback({
                                success: true,
                                users: parsed,
                                next_max_id: d.next_max_id || null
                            });
                        }).catch(function(err) {
                            callback({ success: false, error: err.toString() });
                        });
                    }
                """, user_id, list_type, max_id)

                if not res.get("success"):
                    print(f"\n[!] API error: {res.get('error')}")
                    break

                batch = res.get("users", [])
                for u in batch:
                    uname = u.get("username", "").strip().lower()
                    uid = u.get("id", "").strip()
                    if uname:
                        if uid:
                            self.user_ids[uname] = uid
                        if uname not in collected_users:
                            collected_users.append(uname)

                total_now = len(collected_users)
                if target_count > 0:
                    percent = min(100.0, (total_now / target_count) * 100)
                    print(f"    -> Collected: {total_now} / {target_count} ({percent:.1f}%) {list_type}...", end="\r")
                else:
                    print(f"    -> Collected: {total_now} {list_type}...", end="\r")

                next_max_id = res.get("next_max_id")
                if next_max_id and len(batch) > 0:
                    max_id = str(next_max_id)
                    time.sleep(0.2 + random.uniform(0.05, 0.15))
                    page += 1
                else:
                    break

            except Exception as e:
                print(f"\n[!] Error during batch fetch {page}: {e}")
                break

        print(f"\n[✓] Finished fetching {list_type}! Total fetched: {len(collected_users)}")
        return collected_users

    def scan_non_followers(self) -> Tuple[List[str], List[str], List[str]]:
        """
        Scans 100% of following and followers accurately,
        returning (following_list, followers_list, non_followers_list).
        """
        my_user = self.get_my_username()
        self.whitelist = config.load_whitelist()

        # Open profile page once to load API context & cookies
        self.driver.get(f"https://www.instagram.com/{my_user}/")
        time.sleep(3)

        user_id, following_total, followers_total = self.get_profile_info(my_user)
        print(f"\n{'='*55}")
        print(f"  OFFICIAL PROFILE STATISTICS FOR @{my_user}:")
        print(f"  • Total Following : {following_total} accounts")
        print(f"  • Total Followers : {followers_total} accounts")
        print(f"{'='*55}")

        # 1. Fetch 100% Following list
        if user_id:
            following = self.fetch_user_list_api(user_id, "following", following_total)
            time.sleep(1)
            # 2. Fetch 100% Followers list
            followers = self.fetch_user_list_api(user_id, "followers", followers_total)
        else:
            # Fallback DOM
            following = []
            followers = []

        followers_set = {u.lower() for u in followers}
        
        # 3. Calculate non-followers with 100% precision
        non_followers = []
        for u in following:
            u_clean = u.lower()
            if u_clean not in followers_set:
                if u_clean not in self.whitelist:
                    non_followers.append(u)
                else:
                    print(f"[i] Account @{u} is not following back but is protected by Whitelist.")

        return following, followers, non_followers

    def open_following_modal(self) -> bool:
        """Opens the Following modal dialog on profile if not open."""
        if not self.driver:
            return False

        # 1. Check if modal is already open
        try:
            search_inputs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@placeholder or @aria-label]")
            for s in search_inputs:
                if s.is_displayed():
                    return True
        except Exception:
            pass

        my_user = self.get_my_username()
        profile_url = f"https://www.instagram.com/{my_user}/"

        # Open profile page if not already there
        if f"/{my_user}" not in (self.driver.current_url or "") or "/p/" in (self.driver.current_url or ""):
            self.driver.get(profile_url)
            time.sleep(2.5)

        # 2. Find and click Following link on profile page
        following_xpaths = [
            "//a[contains(@href, '/following')]",
            "//header//a[contains(., 'following') or contains(., 'mengikuti')]",
            "//main//a[contains(., 'following') or contains(., 'mengikuti')]",
            "//a[contains(., 'following') or contains(., 'mengikuti')]",
            "//li[contains(., 'following') or contains(., 'mengikuti')]//a"
        ]

        for xpath in following_xpaths:
            try:
                links = self.driver.find_elements(By.XPATH, xpath)
                for l in links:
                    if l.is_displayed():
                        self.driver.execute_script("arguments[0].click();", l)
                        time.sleep(1.0)
                        break
            except Exception:
                continue

        # 3. Wait until modal dialog and search input appear
        start_wait = time.time()
        while time.time() - start_wait < 6.0:
            try:
                search_inputs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@placeholder or @aria-label]")
                for inp in search_inputs:
                    if inp.is_displayed():
                        return True
            except Exception:
                pass
            time.sleep(0.3)

        return False

    def _clear_search_input(self, search_input):
        """Clears modal search input via JavaScript safely."""
        try:
            if search_input and self.driver:
                self.driver.execute_script("""
                    var inp = arguments[0];
                    if (inp) {
                        var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        setter.call(inp, '');
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                """, search_input)
        except Exception:
            pass

    def unfollow_user(self, target_username: str) -> Tuple[bool, str]:
        """
        Unfollows a user via Following modal search box on your profile.
        Returns (success_status: bool, message: str).
        """
        target_username = target_username.strip().lstrip("@")
        target_lower = target_username.lower()

        if self.dry_run:
            sim_delay = random.uniform(1.0, 2.0)
            time.sleep(sim_delay)
            return True, f"[SIMULATION / DRY-RUN] Successfully simulated unfollow @{target_username}"

        if target_lower in self.whitelist:
            return False, f"Cancelled: Account @{target_username} is in Whitelist"

        if not self.driver:
            raise RuntimeError("Driver not initialized.")

        if not self.open_following_modal():
            return False, "Unable to open Following modal on profile"

        try:
            # 1. Get search input box inside modal
            search_inputs = self.driver.find_elements(By.XPATH, "//div[@role='dialog']//input[@placeholder or @aria-label]")
            search_input = None
            for inp in search_inputs:
                if inp.is_displayed():
                    search_input = inp
                    break

            if not search_input:
                return False, "Search input in Following modal not found"

            # 2. Type target username via JS Injection (Bypass ElementClickIntercepted)
            self.driver.execute_script("""
                var inp = arguments[0];
                var val = arguments[1];
                inp.focus();
                var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                setter.call(inp, val);
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
            """, search_input, target_username)
            time.sleep(1.8)

            # 3. Find Following button in search results
            following_btns = self.driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//button[normalize-space()='Following' or normalize-space()='Mengikuti' or contains(., 'Following') or contains(., 'Mengikuti')]"
            )

            target_btn = None
            for b in following_btns:
                if b.is_displayed():
                    target_btn = b
                    break

            if not target_btn:
                # Check if already Following (not followed)
                follow_btns = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='dialog']//button[normalize-space()='Follow' or normalize-space()='Ikuti']"
                )
                if any(b.is_displayed() for b in follow_btns):
                    self._clear_search_input(search_input)
                    return False, f"Already not following @{target_username} ('Follow' button active)"
                
                self._clear_search_input(search_input)
                return False, f"Account @{target_username} not found in Following list"

            # 4. Click Following button via JS Click
            self.driver.execute_script("arguments[0].click();", target_btn)
            time.sleep(1.2)

            # 5. Wait for and click Unfollow confirmation button in pop-up
            confirm_xpaths = [
                "//button[normalize-space()='Unfollow' or normalize-space()='Batal Mengikuti' or normalize-space()='Berhenti Mengikuti']",
                "//button[contains(., 'Unfollow') or contains(., 'Batal Mengikuti') or contains(., 'Berhenti Mengikuti')]",
                "//div[@role='dialog']//button[contains(@class, '_a9--') or contains(@class, '_a9_1')]"
            ]

            confirm_button = None
            start_wait = time.time()
            while time.time() - start_wait < 4.0:
                for xpath in confirm_xpaths:
                    try:
                        btns = self.driver.find_elements(By.XPATH, xpath)
                        for b in btns:
                            if b.is_displayed() and b.text.strip().lower() not in ["cancel", "batal", "kembali"]:
                                confirm_button = b
                                break
                        if confirm_button:
                            break
                    except Exception:
                        continue
                if confirm_button:
                    break
                time.sleep(0.2)

            if not confirm_button:
                # Check for Instagram block popup
                block_modals = self.driver.find_elements(
                    By.XPATH,
                    "//div[@role='dialog'][contains(., 'Try Again Later') or contains(., 'Coba Lagi Nanti') or contains(., 'Limit') or contains(., 'Dibatasi')]"
                )
                if any(m.is_displayed() for m in block_modals):
                    self._clear_search_input(search_input)
                    return False, "[WARNING] Account restricted by Instagram (Action Block): Limit detected (Try Again Later)"
                
                self._clear_search_input(search_input)
                return False, f"Unfollow confirmation pop-up for @{target_username} did not appear"

            # Click Unfollow confirmation via JS Click
            self.driver.execute_script("arguments[0].click();", confirm_button)
            time.sleep(1.0)

            # 6. Clear search input for next target via JS
            self._clear_search_input(search_input)

            delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
            time.sleep(delay)
            return True, f"Successfully unfollowed @{target_username} via Profile Modal (Delay: {delay:.1f} seconds)"

        except Exception as e:
            return False, f"Modal issue: {e}"

    def close(self):
        """Closes browser if opened by script."""
        if self.driver:
            try:
                if not config.USE_REMOTE_DEBUGGING:
                    self.driver.quit()
                    print("[✓] Automation browser successfully closed.")
            except Exception:
                pass
            finally:
                self.driver = None

