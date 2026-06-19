import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from recbot.catalog_resources import ensure_recai_resource_dir, load_catalog_items


class CatalogResourcesTest(unittest.TestCase):
    def _write_catalog(self, directory: str) -> Path:
        catalog = Path(directory) / "items.jsonl"
        items = [
            {
                "item_id": "movie:aurora_station",
                "domain": "movie",
                "title": "Aurora Station",
                "description": "A cerebral science fiction thriller on an orbital station.",
                "display_text": "Aurora Station. Genres: Science Fiction, Thriller. Plot: A signal predicts accidents in orbit.",
                "categories": ["Science Fiction", "Thriller"],
                "metadata": {"release_year": 2014, "runtime_minutes": 112},
                "signals": {"popularity": 0.72},
                "source": {"dataset": "fixture"},
            },
            {
                "item_id": "movie:nebula_code",
                "domain": "movie",
                "title": "Nebula Code",
                "description": "A science fiction mystery about engineers decoding a signal.",
                "display_text": "Nebula Code. Genres: Science Fiction, Mystery. Plot: Engineers decode a distant signal.",
                "categories": ["Science Fiction", "Mystery"],
                "metadata": {"release_year": 2016, "runtime_minutes": 108},
                "signals": {"popularity": 0.61},
                "source": {"dataset": "fixture"},
            },
            {
                "item_id": "movie:orchard_house",
                "domain": "movie",
                "title": "The Orchard House",
                "description": "A warm family drama on a farm.",
                "display_text": "The Orchard House. Genres: Drama, Family. Plot: Three generations rebuild relationships.",
                "categories": ["Drama", "Family"],
                "metadata": {"release_year": 2008, "runtime_minutes": 96},
                "signals": {"popularity": 0.44},
                "source": {"dataset": "fixture"},
            },
        ]
        with catalog.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(json.dumps(item) + "\n")
        return catalog

    def test_load_catalog_items_rejects_empty_catalog(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.jsonl"
            path.write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "catalog is empty"):
                load_catalog_items(path)

    def test_ensure_recai_resource_dir_writes_native_resource_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = self._write_catalog(tmpdir)
            output_dir = Path(tmpdir) / "recai_resources" / "movie"

            spec = ensure_recai_resource_dir(catalog, output_dir, "movie")

            self.assertEqual(spec.domain, "movie")
            self.assertTrue(spec.item_info_file.exists())
            self.assertTrue(spec.table_col_desc_file.exists())
            self.assertTrue(spec.settings_file.exists())
            self.assertTrue(spec.item_sim_file.exists())
            self.assertIn("external_id", spec.use_cols)
            self.assertIn("tags", spec.categorical_cols)

            settings = json.loads(spec.settings_file.read_text(encoding="utf-8"))
            self.assertEqual(settings["GAME_INFO_FILE"], "item_info.csv")
            self.assertEqual(settings["TABLE_COL_DESC_FILE"], "table_col_desc.json")
            self.assertEqual(settings["ITEM_SIM_FILE"], "item_sim.npy")
            self.assertEqual(settings["USE_COLS"], spec.use_cols)
            self.assertEqual(settings["CATEGORICAL_COLS"], ["tags"])
            self.assertIn("MODEL_CKPT_FILE", settings)

            with spec.item_info_file.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][0], "0")
            self.assertEqual(rows[0][1], "__dummy__")
            self.assertEqual(rows[1][0], "1")
            self.assertEqual(rows[1][1], "movie:aurora_station")
            self.assertEqual(rows[1][2], "Aurora Station")
            self.assertIn("Science Fiction", rows[1][3])
            self.assertEqual(rows[2][0], "2")

            column_desc = json.loads(spec.table_col_desc_file.read_text(encoding="utf-8"))
            for column in spec.use_cols:
                self.assertIn(column, column_desc)

            item_sim = np.load(spec.item_sim_file)
            self.assertEqual(item_sim.shape, (4, 4))
            self.assertAlmostEqual(float(item_sim[1, 1]), 1.0)
            self.assertAlmostEqual(float(item_sim[2, 2]), 1.0)
            self.assertAlmostEqual(float(item_sim[3, 3]), 1.0)
            self.assertTrue(np.allclose(item_sim, item_sim.T))
            self.assertGreater(item_sim[1, 2], item_sim[1, 3])


if __name__ == "__main__":
    unittest.main()
