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


if __name__ == "__main__":
    unittest.main()
