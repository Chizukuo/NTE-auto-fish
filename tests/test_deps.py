import unittest

from modules.deps import ensure_dependencies, get_missing_dependencies


class TestDeps(unittest.TestCase):
    def test_get_missing_dependencies_returns_empty_for_importable_module(self):
        missing = get_missing_dependencies({"sys": "sys"})
        self.assertEqual(missing, [])

    def test_ensure_dependencies_raises_for_missing_module(self):
        with self.assertRaises(RuntimeError):
            ensure_dependencies({"__nonexistent_mod__": "nonexistent-package"})


if __name__ == "__main__":
    unittest.main()
