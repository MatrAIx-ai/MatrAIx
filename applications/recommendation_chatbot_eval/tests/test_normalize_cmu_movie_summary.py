import json
import tempfile
import unittest
from pathlib import Path

from scripts.normalize_cmu_movie_summary import normalize_cmu_movie_summary


class NormalizeCmuMovieSummaryTest(unittest.TestCase):
    def test_normalize_cmu_movie_summary_writes_catalog_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "MovieSummaries"
            raw_dir.mkdir()
            (raw_dir / "movie.metadata.tsv").write_text(
                "\t".join(
                    [
                        "54166",
                        "/m/0f4yh",
                        "Raiders of the Lost Ark",
                        "1981-06-12",
                        "389925971",
                        "115.0",
                        '{"/m/02h40lc": "English Language"}',
                        '{"/m/09c7w0": "United States of America"}',
                        '{"/m/0jtdp": "Adventure", "/m/02kdv5l": "Action"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (raw_dir / "plot_summaries.txt").write_text(
                "54166\tAn archaeologist races to find a powerful artifact before rivals do.\n",
                encoding="utf-8",
            )
            output_path = Path(tmpdir) / "items.jsonl"

            count = normalize_cmu_movie_summary(raw_dir, output_path)

            self.assertEqual(count, 1)
            item = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(item["item_id"], "cmu:54166")
            self.assertEqual(item["domain"], "movie")
            self.assertEqual(item["title"], "Raiders of the Lost Ark")
            self.assertEqual(item["description"], "An archaeologist races to find a powerful artifact before rivals do.")
            self.assertEqual(item["categories"], ["Adventure", "Action"])
            self.assertEqual(item["metadata"]["release_year"], 1981)
            self.assertEqual(item["metadata"]["runtime_minutes"], 115)
            self.assertEqual(item["metadata"]["languages"], ["English Language"])
            self.assertEqual(item["metadata"]["countries"], ["United States of America"])
            self.assertEqual(item["signals"]["box_office_revenue"], 389925971)
            self.assertEqual(item["source"]["dataset"], "cmu_movie_summary_corpus")

    def test_normalize_cmu_movie_summary_sanitizes_surrogate_escaped_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "MovieSummaries"
            raw_dir.mkdir()
            (raw_dir / "movie.metadata.tsv").write_text(
                "\t".join(
                    [
                        "31099422",
                        "/m/0g5qjk",
                        "We Have a Pope",
                        "2011",
                        "",
                        "102.0",
                        '{"/m/x": "\\ud801\\udc16"}',
                        '{}',
                        '{"/m/07s9rl0": "Drama"}',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (raw_dir / "plot_summaries.txt").write_text(
                "31099422\tA conclave chooses a reluctant pope.\n",
                encoding="utf-8",
            )
            output_path = Path(tmpdir) / "items.jsonl"

            normalize_cmu_movie_summary(raw_dir, output_path)

            item = json.loads(output_path.read_text(encoding="utf-8"))
            json.dumps(item, ensure_ascii=False).encode("utf-8")
            self.assertNotIn("\\ud801", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
