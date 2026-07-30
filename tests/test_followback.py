import unittest

from followback import find_following_back, find_not_following_back


class FindNotFollowingBackTests(unittest.TestCase):
    def test_returns_following_users_missing_from_followers(self) -> None:
        followers = {"alice", "bob"}
        following = {"alice", "bob", "carol", "dave"}

        self.assertEqual(find_not_following_back(followers, following), ["carol", "dave"])

    def test_deduplicates_and_sorts_results(self) -> None:
        followers = ["alice", "bob"]
        following = ["dave", "carol", "dave", "bob"]

        self.assertEqual(find_not_following_back(followers, following), ["carol", "dave"])


class FindFollowingBackTests(unittest.TestCase):
    def test_returns_following_users_present_in_followers(self) -> None:
        followers = {"alice", "bob"}
        following = {"alice", "bob", "carol", "dave"}

        self.assertEqual(find_following_back(followers, following), ["alice", "bob"])

    def test_deduplicates_and_sorts_results(self) -> None:
        followers = ["alice", "bob", "bob"]
        following = ["dave", "carol", "bob", "alice"]

        self.assertEqual(find_following_back(followers, following), ["alice", "bob"])


if __name__ == "__main__":
    unittest.main()
