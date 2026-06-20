import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.generate_item_similarity import generate_item_similarity


class GenerateItemSimilarityTest(unittest.TestCase):
    def test_generate_item_similarity_writes_dense_recai_matrix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resource_dir = Path(tmpdir)
            item_info = resource_dir / "item_info.parquet"
            pd.DataFrame(
                [
                    {
                        "id": 0,
                        "title": "__dummy__",
                        "tags": "__dummy__",
                        "description": "",
                        "display_text": "",
                    },
                    {
                        "id": 1,
                        "title": "Aurora Station",
                        "tags": "Science Fiction, Mystery",
                        "description": "A station crew investigates a signal in orbit.",
                        "display_text": "Science fiction mystery in orbit.",
                    },
                    {
                        "id": 2,
                        "title": "Nebula Code",
                        "tags": "Science Fiction, Mystery",
                        "description": "Engineers decode a distant signal.",
                        "display_text": "Science fiction mystery about a distant signal.",
                    },
                    {
                        "id": 3,
                        "title": "The Orchard House",
                        "tags": "Drama, Family",
                        "description": "A warm family drama on a farm.",
                        "display_text": "Family drama on a farm.",
                    },
                ]
            ).to_parquet(item_info, index=False)
            output = resource_dir / "item_sim.npy"

            stats = generate_item_similarity(
                item_info,
                output,
                block_size=2,
                dtype=np.float16,
                max_features=None,
                min_df=1,
                force=True,
            )

            similarity = np.load(output, allow_pickle=False)
            self.assertEqual(stats["shape"], [4, 4])
            self.assertEqual(similarity.shape, (4, 4))
            self.assertEqual(similarity.dtype, np.float16)
            self.assertAlmostEqual(float(similarity[1, 1]), 1.0)
            self.assertAlmostEqual(float(similarity[2, 2]), 1.0)
            self.assertAlmostEqual(float(similarity[3, 3]), 1.0)
            self.assertTrue(np.allclose(similarity, similarity.T))
            self.assertGreater(similarity[1, 2], similarity[1, 3])


if __name__ == "__main__":
    unittest.main()
