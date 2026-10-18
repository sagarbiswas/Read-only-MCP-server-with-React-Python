import unittest

from autosys_log_mcp.web import SearchRequestHandler


class SearchRequestParsingTests(unittest.TestCase):
    def test_accepts_any_combination_of_optional_filters(self):
        filters = SearchRequestHandler._parse_search_request(
            {"job_name": "DAILY_JOB", "max_results": 25}
        )

        self.assertIsNone(filters["date"])
        self.assertEqual(filters["job_name"], "DAILY_JOB")
        self.assertIsNone(filters["search_text"])
        self.assertEqual(filters["max_results"], 25)

    def test_normalizes_empty_filter_values(self):
        filters = SearchRequestHandler._parse_search_request(
            {"date": "", "job_name": " ", "search_text": ""}
        )

        self.assertIsNone(filters["date"])
        self.assertIsNone(filters["job_name"])
        self.assertIsNone(filters["search_text"])

    def test_rejects_invalid_result_limits(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 1000"):
            SearchRequestHandler._parse_search_request({"max_results": 1001})
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            SearchRequestHandler._parse_search_request({"max_results": True})


if __name__ == "__main__":
    unittest.main()
