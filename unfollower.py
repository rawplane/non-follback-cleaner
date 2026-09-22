import os
import time
import random
import re
from typing import Set, List, Tuple, Optional, Callable, Dict

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

import config
import storage


def parse_count_string(text: str) -> int:
    """Converts Instagram count strings ('628', '1,170', '1.2K', '1M') to integer."""
    if not text:
        return 0
    t = text.strip().upper().replace(",", "")
    try:
        if "K" in t:
            return int(float(t.replace("K", "").strip()) * 1000)
        if "M" in t:
            return int(float(t.replace("M", "").strip()) * 1000000)
        t = t.replace(".", "")
        return int(re.sub(r"[^\d]", "", t) or 0)
    except Exception:
        return 0


class InstagramUnfollower:
    def __init__(self, dry_run: bool = config.DEFAULT_DRY_RUN):
        self.dry_run = dry_run
        self.playwright: Optional[Playwright] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.whitelist: Set[str] = config.load_whitelist()
        self.my_username: str = config.INSTAGRAM_USERNAME
        self.user_id: Optional[str] = None
        self.user_ids: Dict[str, str] = {}

    def init_browser(self):
        """Initializes Brave Browser via Playwright Persistent Context."""
        if self.context and self.page:
            return

        user_data_dir = os.path.abspath(config.AUTOMATION_PROFILE_DIR)
        os.makedirs(user_data_dir, exist_ok=True)

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-notifications",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate,OptimizationHints,MediaRouter",
            "--start-maximized"
        ]

        self.playwright = sync_playwright().start()
        
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            executable_path=config.BRAVE_BINARY_PATH if os.path.exists(config.BRAVE_BINARY_PATH) else None,
            headless=config.HEADLESS_MODE,
            args=args,
            viewport=None,
            ignore_default_args=["--enable-automation"]
        )

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(config.PAGE_TIMEOUT_SECONDS * 1000)

    @property
    def current_page(self) -> Page:
        if self.page is None:
            self.init_browser()
        assert self.page is not None
        return self.page

    @property
    def current_context(self) -> BrowserContext:
        if self.context is None:
            self.init_browser()
        assert self.context is not None
        return self.context

    def is_logged_in(self) -> bool:
        """Checks whether Instagram session cookie or auth elements exist."""
        if not self.context or not self.page:
            return False

        try:
            cookies = {
                str(c.get("name", "")): str(c.get("value", ""))
                for c in self.current_context.cookies("https://www.instagram.com")
            }
            if cookies.get("sessionid"):
                return True
        except Exception:
            pass

        try:
            current_url = (self.current_page.url or "").lower()
            if "accounts/login" in current_url or "accounts/emailsignup" in current_url:
                return False

            nav_count = self.current_page.locator(
                "//a[contains(@href, '/') and (.//span[text()='Profile' or text()='Profil' or text()='Home' or text()='Beranda'] or .//svg[@aria-label='Home' or @aria-label='Beranda' or @aria-label='Direct'])]"
            ).count()
            if nav_count > 0:
                return True
        except Exception:
            pass

        return False

    def check_login(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Ensures active login session in Brave."""
        self.init_browser()
        if status_callback:
            status_callback("Memeriksa sesi login Instagram...")

        self.current_page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        time.sleep(2)

        if self.is_logged_in():
            return True

        if status_callback:
            status_callback("Sesi login belum aktif. Silakan login pada jendela browser Brave yang terbuka...")

        max_wait = 300
        start_time = time.time()
        while time.time() - start_time < max_wait:
            time.sleep(2)
            if self.is_logged_in():
                time.sleep(1)
                return True

        return False

    def get_my_username(self) -> str:
        """Extracts username of logged-in account."""
        if self.my_username:
            return self.my_username

        self.init_browser()
        try:
            detected = self.current_page.evaluate(r"""() => {
                const links = document.querySelectorAll('a[role="link"], a');
                const excluded = ['explore', 'reels', 'direct', 'stories', 'accounts', 'popular', 'legal', 'about', 'your_activity', 'archive', 'emailsignup'];
                for (let i = 0; i < links.length; i++) {
                    const href = links[i].getAttribute('href') || '';
                    const match = href.match(/^\/([a-zA-Z0-9_\.]+)\/?$/);
                    if (match) {
                        const u = match[1].toLowerCase();
                        if (!excluded.includes(u)) {
                            if (links[i].querySelector('img') || links[i].querySelector('svg[aria-label*="Profile"]') || links[i].querySelector('svg[aria-label*="Profil"]')) {
                                return match[1];
                            }
                        }
                    }
                }
                return null;
            }""")
            if detected:
                self.my_username = detected
                return self.my_username
        except Exception:
            pass

        # Fallback to cookies
        try:
            cookies = {
                str(c.get("name", "")): str(c.get("value", ""))
                for c in self.current_context.cookies("https://www.instagram.com")
            }
            ds_user_id = cookies.get("ds_user_id")
            if ds_user_id:
                self.user_id = ds_user_id
        except Exception:
            pass

        return self.my_username or "unknown_user"

    def get_profile_info(self, username: str) -> Tuple[str, int, int]:
        """Fetches User ID, Total Following, and Followers count via internal API."""
        self.init_browser()
        try:
            info = self.current_page.evaluate(r"""async (uname) => {
                try {
                    const r = await fetch('https://www.instagram.com/api/v1/users/web_profile_info/?username=' + uname, {
                        headers: {
                            'X-IG-App-ID': '936619743392459',
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    const d = await r.json();
                    if (d.data && d.data.user) {
                        return {
                            success: true,
                            id: String(d.data.user.id),
                            following_count: d.data.user.edge_follow.count,
                            followers_count: d.data.user.edge_followed_by.count
                        };
                    }
                    return { success: false, error: 'User data not found' };
                } catch (e) {
                    return { success: false, error: e.toString() };
                }
            }""", username)

            if info and info.get("success"):
                uid = str(info["id"])
                if username.lower() == self.my_username.lower():
                    self.user_id = uid
                self.user_ids[username.lower()] = uid
                return uid, int(info["following_count"]), int(info["followers_count"])
        except Exception:
            pass

        return "", 0, 0

    def fetch_user_list_api(
        self,
        user_id: str,
        list_type: str,
        target_count: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """Collects 100% of Following or Followers via internal GraphQL / REST API endpoints."""
        collected_users: List[str] = []
        max_id = ""
        page = 1

        while True:
            try:
                res = self.current_page.evaluate(r"""async ([userId, listType, maxId]) => {
                    function getCookie(name) {
                        const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
                        return match ? decodeURIComponent(match[3]) : null;
                    }

                    const csrfToken = getCookie('csrftoken') || '';
                    const headers = {
                        'X-CSRFToken': csrfToken,
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-ASBD-ID': '129477'
                    };

                    if (listType === 'followers') {
                        const variables = { id: userId, first: 50 };
                        if (maxId) variables.after = maxId;

                        const url = 'https://www.instagram.com/graphql/query/?query_hash=5aefa9893005572d237da5068082d8d5&variables=' + encodeURIComponent(JSON.stringify(variables));
                        try {
                            const r = await fetch(url, { headers });
                            const d = await r.json();
                            const edge = (d.data && d.data.user && d.data.user.edge_followed_by) || {};
                            const edges = edge.edges || [];
                            const parsed = edges.map(e => ({
                                username: (e.node?.username || '').toLowerCase(),
                                id: String(e.node?.id || '')
                            }));
                            const pageInfo = edge.page_info || {};
                            return {
                                success: true,
                                users: parsed,
                                next_max_id: pageInfo.has_next_page ? pageInfo.end_cursor : null
                            };
                        } catch (err) {
                            return { success: false, error: err.toString() };
                        }
                    } else {
                        const url = 'https://www.instagram.com/api/v1/friendships/' + userId + '/following/?count=200' + (maxId ? '&max_id=' + encodeURIComponent(maxId) : '');
                        try {
                            const r = await fetch(url, { headers });
                            const d = await r.json();
                            const rawUsers = d.users || [];
                            const parsed = rawUsers.map(u => ({
                                username: (u.username || '').toLowerCase(),
                                id: String(u.pk || u.id || u.pk_id || '')
                            }));
                            return {
                                success: true,
                                users: parsed,
                                next_max_id: d.next_max_id || null
                            };
                        } catch (err) {
                            return { success: false, error: err.toString() };
                        }
                    }
                }""", [user_id, list_type, max_id])

                if not res or not res.get("success"):
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

                if progress_callback:
                    progress_callback(len(collected_users), target_count)

                next_max_id = res.get("next_max_id")
                if next_max_id and len(batch) > 0:
                    max_id = str(next_max_id)
                    time.sleep(0.2 + random.uniform(0.05, 0.15))
                    page += 1
                else:
                    break

            except Exception:
                break

        return collected_users

    def scan_non_followers(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> Tuple[List[str], List[str], List[str]]:
        """Scans Following and Followers, calculating non-follback list."""
        self.init_browser()
        my_user = self.get_my_username()
        self.whitelist = config.load_whitelist()

        self.current_page.goto(f"https://www.instagram.com/{my_user}/", wait_until="domcontentloaded")
        time.sleep(2)

        user_id, following_total, followers_total = self.get_profile_info(my_user)

        # 1. Fetch Following
        def cb_following(cur, total):
            if progress_callback:
                progress_callback("following", cur, total)

        following = self.fetch_user_list_api(user_id, "following", following_total, cb_following)
        time.sleep(0.5)

        # 2. Fetch Followers
        def cb_followers(cur, total):
            if progress_callback:
                progress_callback("followers", cur, total)

        followers = self.fetch_user_list_api(user_id, "followers", followers_total, cb_followers)

        followers_set = set(followers)
        non_followers = [
            u for u in following
            if u not in followers_set and u not in self.whitelist
        ]

        # Save to SQLite
        storage.save_scan_results(my_user, non_followers)

        return following, followers, non_followers

    def unfollow_api(self, target_user_id: str) -> Tuple[bool, str]:
        """Calls direct Instagram friendship destroy endpoint inside authenticated browser origin."""
        try:
            res = self.current_page.evaluate(r"""async (uid) => {
                function getCookie(name) {
                    const match = document.cookie.match(new RegExp('(^|;\\s*)(' + name + ')=([^;]*)'));
                    return match ? decodeURIComponent(match[3]) : null;
                }

                const csrfToken = getCookie('csrftoken') || '';
                try {
                    const response = await fetch('https://www.instagram.com/api/v1/friendships/destroy/' + uid + '/', {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': csrfToken,
                            'X-IG-App-ID': '936619743392459',
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-ASBD-ID': '129477',
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }
                    });
                    const data = await response.json();
                    return { status_code: response.status, data: data };
                } catch (err) {
                    return { status_code: 0, error: err.toString() };
                }
            }""", target_user_id)

            if not res:
                return False, "No response from API"

            status_code = res.get("status_code", 0)
            data = res.get("data", {})

            if status_code == 200 and data.get("status") == "ok":
                return True, "Success via Direct API"

            if data.get("message") == "feedback_required" or data.get("spam") is True:
                return False, "[WARNING] Instagram Action Block: Try Again Later / Feedback Required"

            if status_code == 429:
                return False, "[WARNING] Instagram Rate Limit 429"

            return False, f"API Response ({status_code}): {data.get('message', 'Failed')}"
        except Exception as e:
            return False, f"API Exception: {e}"

    def unfollow_ui(self, target_username: str) -> Tuple[bool, str]:
        """Fallback unfollow using Playwright page interaction."""
        try:
            self.current_page.goto(f"https://www.instagram.com/{target_username}/", wait_until="domcontentloaded")
            time.sleep(1.5)

            following_btn = self.current_page.locator(
                "//button[normalize-space()='Following' or normalize-space()='Mengikuti' or contains(., 'Following') or contains(., 'Mengikuti')]"
            ).first

            if following_btn.count() == 0 or not following_btn.is_visible():
                return False, f"Account @{target_username} is not followed or button not found"

            following_btn.click()
            time.sleep(1.0)

            confirm_btn = self.current_page.locator(
                "//button[normalize-space()='Unfollow' or normalize-space()='Batal Mengikuti' or normalize-space()='Berhenti Mengikuti']"
            ).first

            if confirm_btn.count() == 0 or not confirm_btn.is_visible():
                # Check for action block modal
                block = self.current_page.locator("//div[@role='dialog'][contains(., 'Try Again Later') or contains(., 'Coba Lagi Nanti')]").first
                if block.count() > 0 and block.is_visible():
                    return False, "[WARNING] Instagram Action Block (Try Again Later)"
                return False, "Unfollow confirm button did not appear"

            confirm_btn.click()
            time.sleep(1.0)
            return True, "Success via Web UI"
        except Exception as e:
            return False, f"UI Fallback Error: {e}"

    def unfollow_user(self, target_username: str) -> Tuple[bool, str]:
        """Unfollows an account via Direct API with automatic UI fallback."""
        target_username = target_username.strip().lstrip("@")
        target_lower = target_username.lower()

        if self.dry_run:
            sim_delay = random.uniform(1.0, 2.0)
            time.sleep(sim_delay)
            storage.log_action(self.my_username, target_username, "unfollow", "dry_run", "Simulated")
            return True, f"[SIMULATION] Unfollowed @{target_username} (Delay: {sim_delay:.1f}s)"

        if target_lower in self.whitelist:
            storage.log_action(self.my_username, target_username, "unfollow", "skipped", "Whitelist protected")
            return False, f"Skipped: @{target_username} in Whitelist"

        self.init_browser()

        # Step 1: Resolve target user ID
        target_uid = self.user_ids.get(target_lower)
        if not target_uid:
            target_uid, _, _ = self.get_profile_info(target_username)

        # Step 2: Try Direct API
        if target_uid:
            success, msg = self.unfollow_api(target_uid)
            if success:
                delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
                time.sleep(delay)
                storage.log_action(self.my_username, target_username, "unfollow", "success", msg)
                return True, f"Successfully unfollowed @{target_username} (API) (Delay: {delay:.1f}s)"
            elif "[WARNING]" in msg:
                storage.log_action(self.my_username, target_username, "unfollow", "blocked", msg)
                return False, msg

        # Step 3: Fallback UI
        success, msg = self.unfollow_ui(target_username)
        if success:
            delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
            time.sleep(delay)
            storage.log_action(self.my_username, target_username, "unfollow", "success", msg)
            return True, f"Successfully unfollowed @{target_username} (UI) (Delay: {delay:.1f}s)"

        storage.log_action(self.my_username, target_username, "unfollow", "failed", msg)
        return False, msg

    def close(self):
        """Cleans up Playwright context and browser process."""
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        finally:
            self.context = None
            self.page = None
            self.playwright = None
