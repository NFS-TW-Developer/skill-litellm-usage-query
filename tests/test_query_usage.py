import importlib.util
import pathlib
import tempfile
import unittest


def load_module():
    script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "query_usage.py"
    spec = importlib.util.spec_from_file_location("query_usage", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


query_usage = load_module()


class QueryUsageTests(unittest.TestCase):
    def test_load_dotenv_returns_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = pathlib.Path(tmpdir) / ".env"
            env_path.write_text(
                "LITELLM_BASE_URL=https://example.com/\nLITELLM_API_KEY=sk-test123\n",
                encoding="utf-8",
            )
            values = query_usage.load_dotenv(env_path)

        self.assertEqual(values["LITELLM_BASE_URL"], "https://example.com/")
        self.assertEqual(values["LITELLM_API_KEY"], "sk-test123")

    def test_build_parser_uses_env_values(self):
        parser = query_usage.build_parser(
            {"LITELLM_BASE_URL": "https://example.com/", "LITELLM_API_KEY": "sk-test123"},
            pathlib.Path(".env"),
        )
        args = parser.parse_args(["--start-date", "2026-06-01", "--end-date", "2026-06-02"])
        self.assertEqual(args.base_url, "https://example.com/")
        self.assertEqual(args.api_key, "sk-test123")

    def test_format_timezone_slug(self):
        self.assertEqual(
            query_usage.format_timezone_slug(-480),
            "utc-plus-08-00",
        )

    def test_default_chart_output(self):
        output = query_usage.default_chart_output(
            "model-spend",
            "2026-06-01",
            "2026-06-05",
            -480,
        )
        self.assertEqual(
            output.as_posix(),
            "reports/model-spend-2026-06-01_to_2026-06-05-utc-plus-08-00.png",
        )

    def test_aggregate_records_collects_api_keys_and_model_groups(self):
        row = {
            "date": "2026-06-01",
            "metrics": {"spend": 1.5, "total_tokens": 100, "api_requests": 2},
            "breakdown": {
                "api_keys": {
                    "key-1": {
                        "metrics": {"spend": 1.5, "total_tokens": 100, "api_requests": 2},
                        "metadata": {"key_alias": "demo"},
                    }
                },
                "model_groups": {
                    "gpt-5.4": {
                        "metrics": {"spend": 1.5, "total_tokens": 100, "api_requests": 2},
                        "metadata": {},
                    }
                },
            },
        }
        result = query_usage.aggregate_records([row], "2026-06-01")
        self.assertIn("key-1", result["api_key_breakdown"])
        self.assertIn("gpt-5.4", result["model_group_breakdown"])

    def test_filter_records_for_day_keeps_only_matching_date(self):
        records = [
            {"date": "2026-06-06", "metrics": {"spend": 10}},
            {"date": "2026-06-07", "metrics": {"spend": 20}},
            {"metrics": {"spend": 30}},
        ]
        filtered = query_usage.filter_records_for_day(records, "2026-06-07")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["date"], "2026-06-07")

    def test_compress_pie_data_adds_others(self):
        labels, values = query_usage.compress_pie_data(
            ["a", "b", "c", "d"],
            [4, 3, 2, 1],
            2,
        )
        self.assertEqual(labels, ["a", "b", "Others"])
        self.assertEqual(values, [4, 3, 3])

    def test_api_key_format_status(self):
        self.assertEqual(query_usage.api_key_format_status(None), "missing")
        self.assertEqual(
            query_usage.api_key_format_status("sk-abc12345"),
            "looks-valid(len=11)",
        )
        self.assertEqual(
            query_usage.api_key_format_status("bad key"),
            "looks-suspicious(len=7)",
        )

    def test_mask_api_key(self):
        self.assertEqual(query_usage.mask_api_key(None), "missing")
        self.assertEqual(query_usage.mask_api_key("abcd"), "set(len=4)")
        self.assertEqual(
            query_usage.mask_api_key("sk-abc12345"),
            "set(len=11, prefix=sk-a, suffix=2345)",
        )


if __name__ == "__main__":
    unittest.main()
