import unittest
import os
import storage
from unfollower import parse_count_string, InstagramUnfollower


class TestCleaner(unittest.TestCase):
    def test_parse_count_string(self):
        self.assertEqual(parse_count_string("500"), 500)
        self.assertEqual(parse_count_string("1.2K"), 1200)
        self.assertEqual(parse_count_string("2M"), 2000000)
        self.assertEqual(parse_count_string("1,540"), 1540)
        self.assertEqual(parse_count_string(""), 0)

    def test_storage_whitelist(self):
        test_user = "senior_dev_test_user"
        storage.add_whitelist(test_user)
        wl = storage.get_whitelist()
        self.assertIn(test_user, wl)

        storage.remove_whitelist(test_user)
        wl_after = storage.get_whitelist()
        self.assertNotIn(test_user, wl_after)

    def test_storage_scan_and_logs(self):
        my_user = "tester"
        targets = ["target1", "target2"]
        storage.save_scan_results(my_user, targets)
        loaded = storage.get_last_scan(my_user)
        self.assertEqual(loaded, targets)

        storage.log_action(my_user, "target1", "unfollow", "success", "Unit test log")
        logs = storage.get_recent_logs(limit=5)
        self.assertTrue(any(row["target_username"] == "target1" for row in logs))

    def test_dry_run_unfollow(self):
        unfollower = InstagramUnfollower(dry_run=True)
        unfollower.my_username = "test_actor"
        success, msg = unfollower.unfollow_user("fake_target")
        self.assertTrue(success)
        self.assertIn("[SIMULATION]", msg)

    def test_binary_search_fallback(self):
        import config
        binary = config.find_brave_binary()
        self.assertTrue(isinstance(binary, str))
        self.assertTrue(len(binary) > 0)

    def test_scan_safety_check(self):
        unfollower = InstagramUnfollower(dry_run=True)
        unfollower.my_username = "tester"
        # Mock get_profile_info to return (uid, 100 following, 50 followers)
        unfollower.get_profile_info = lambda uname: ("123", 100, 50)
        # Mock fetch_user_list_api to simulate following=10 users, followers=0 users (API failure)
        unfollower.fetch_user_list_api = lambda uid, ltype, total, cb=None: (
            ["u1", "u2"] if ltype == "following" else []
        )
        # Mock current_page.goto
        class DummyPage:
            def goto(self, *args, **kwargs):
                pass
        unfollower.page = DummyPage()

        with self.assertRaises(RuntimeError) as ctx:
            unfollower.scan_non_followers()
        self.assertIn("Gagal mengambil daftar followers", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
