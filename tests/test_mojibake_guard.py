import unittest

from tools.check_mojibake import scan_paths


class MojibakeGuardTest(unittest.TestCase):
    def test_critical_ui_and_runtime_files_are_utf8_clean(self):
        findings = scan_paths(
            [
                "run.py",
                "database.py",
                "profileManagment.py",
                "static",
                "templates",
                "scripts",
                "tests",
                "doc",
            ]
        )
        formatted = "\n".join(
            f"{path}:{line_number}: {pattern}: {line}"
            for path, line_number, pattern, line in findings
        )
        self.assertEqual([], findings, formatted)


if __name__ == "__main__":
    unittest.main()
