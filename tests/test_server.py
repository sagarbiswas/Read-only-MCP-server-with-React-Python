import tempfile
import unittest
from pathlib import Path

from autosys_log_mcp.server import search_log_files


class SearchLogFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.job_dir = self.root / "18062025" / "DAILY_JOB"
        self.job_dir.mkdir(parents=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_searches_case_insensitively_in_nested_files(self):
        nested = self.job_dir / "archive"
        nested.mkdir()
        (nested / "run.log").write_text(
            "job started\nERROR: step failed\n", encoding="utf-8"
        )

        result = search_log_files(
            self.root, "18062025", "DAILY_JOB", "error"
        )

        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["match_count"], 1)
        self.assertEqual(
            result["matches"][0]["file"], str(Path("archive") / "run.log")
        )
        self.assertEqual(result["matches"][0]["line"], 2)
        self.assertFalse(result["truncated"])

    def test_respects_case_sensitivity_and_result_limit(self):
        (self.job_dir / "first.log").write_text(
            "Error one\nError two\n", encoding="utf-8"
        )

        result = search_log_files(
            self.root,
            "18062025",
            "DAILY_JOB",
            "error",
            case_sensitive=True,
            max_results=1,
        )
        self.assertEqual(result["match_count"], 0)
        self.assertFalse(result["truncated"])

        result = search_log_files(
            self.root,
            "18062025",
            "DAILY_JOB",
            "Error",
            max_results=1,
        )
        self.assertEqual(result["match_count"], 1)
        self.assertTrue(result["truncated"])

    def test_rejects_invalid_date_and_job_path(self):
        with self.assertRaisesRegex(ValueError, "DDMMYYYY"):
            search_log_files(self.root, "2025-06-18", "DAILY_JOB", "ERROR")
        with self.assertRaisesRegex(ValueError, "single valid folder"):
            search_log_files(self.root, "18062025", "..\\other", "ERROR")

    def test_missing_job_directory_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            search_log_files(self.root, "18062025", "MISSING_JOB", "ERROR")

    def test_searches_with_date_job_or_text_filters_independently(self):
        (self.job_dir / "run.log").write_text(
            "ERROR: nightly run failed\njob completed\n", encoding="utf-8"
        )
        other_job = self.root / "19062025" / "DAILY_JOB"
        other_job.mkdir(parents=True)
        (other_job / "run.log").write_text("ERROR: other day\n", encoding="utf-8")

        by_date = search_log_files(self.root, date="18062025")
        self.assertEqual(by_date["match_count"], 2)

        by_job = search_log_files(self.root, job_name="DAILY_JOB")
        self.assertEqual(by_job["match_count"], 3)

        by_text = search_log_files(self.root, search_text="error")
        self.assertEqual(by_text["match_count"], 2)

    def test_requires_at_least_one_filter(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            search_log_files(self.root)


if __name__ == "__main__":
    unittest.main()
