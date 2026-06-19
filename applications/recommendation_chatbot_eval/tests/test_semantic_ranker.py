import json
import os
import unittest
from unittest.mock import patch

from recbot.semantic_ranker import SemanticProfileRankingTool


class FakeCorpus:
    def __init__(self):
        self.items = {
            1: {
                "id": 1,
                "title": "Batman Begins",
                "display_text": "Batman Begins. Superhero action crime film with a dark vigilante origin.",
                "tags": "Action, Superhero, Crime",
                "visited_num": 10,
            },
            2: {
                "id": 2,
                "title": "The Dark Knight",
                "display_text": "The Dark Knight. Superhero crime thriller about Batman facing a chaotic villain.",
                "tags": "Action, Superhero, Crime, Thriller",
                "visited_num": 100,
            },
            3: {
                "id": 3,
                "title": "The Orchard House",
                "display_text": "The Orchard House. Warm family drama on a quiet farm.",
                "tags": "Drama, Family",
                "visited_num": 50,
            },
            4: {
                "id": 4,
                "title": "Saw",
                "display_text": "Saw. Violent horror thriller built around traps.",
                "tags": "Horror, Thriller",
                "visited_num": 90,
            },
        }
        self.title_to_id = {item["title"]: item_id for item_id, item in self.items.items()}

    def fuzzy_match(self, value, col):
        if col != "title":
            raise ValueError("only title fuzzy matching is supported in the fake corpus")
        if isinstance(value, str):
            return self._match_one(value)
        return [self._match_one(item) for item in value]

    def _match_one(self, value):
        value_lower = value.lower()
        for title in self.title_to_id:
            if value_lower in title.lower() or title.lower() in value_lower:
                return title
        return value

    def convert_title_2_info(self, titles, col_names=None):
        if isinstance(titles, str):
            item_ids = [self.title_to_id[titles]]
            scalar = True
        else:
            item_ids = [self.title_to_id[title] for title in titles]
            scalar = False
        values = {"id": item_ids}
        if scalar:
            return {"id": item_ids[0]}
        return values

    def convert_id_2_info(self, item_id, col_names=None):
        if isinstance(item_id, int):
            item_ids = [item_id]
            scalar = True
        else:
            item_ids = list(item_id)
            scalar = False
        if isinstance(col_names, str):
            columns = [col_names]
        elif col_names is None:
            columns = ["title", "display_text", "tags", "visited_num"]
        else:
            columns = col_names
        result = {column: [self.items[item][column] for item in item_ids] for column in columns}
        if scalar:
            return {column: values[0] for column, values in result.items()}
        return result


class FakeBuffer:
    def __init__(self, candidates, similarity=None):
        self.memory = list(candidates)
        self.similarity = similarity
        self.tracker = []

    def get(self):
        return list(self.memory)

    def push(self, tool, candidates):
        self.memory = list(candidates)

    def track(self, tool, input=None, output=None):
        self.tracker.append({"tool": tool, "input": input, "output": output})


class SemanticProfileRankingToolTest(unittest.TestCase):
    def test_popularity_schema_matches_native_popularity_behavior(self):
        buffer = FakeBuffer([1, 2, 3])
        tool = SemanticProfileRankingTool(
            "Movie Candidates Ranking Tool",
            "rank movies",
            FakeCorpus(),
            buffer,
            rec_num=3,
        )

        output = tool.run(json.dumps({"schema": "popularity", "prefer": [], "unwanted": []}))

        self.assertEqual(buffer.memory, [2, 3, 1])
        self.assertIn("popularities", output)
        self.assertEqual(buffer.tracker[-1]["tool"], "Movie Candidates Ranking Tool")

    def test_similarity_schema_uses_buffer_similarity_scores(self):
        buffer = FakeBuffer([1, 2, 3], similarity=[0.2, 0.9, 0.4])
        tool = SemanticProfileRankingTool(
            "Movie Candidates Ranking Tool",
            "rank movies",
            FakeCorpus(),
            buffer,
            rec_num=3,
        )

        tool.run(json.dumps({"schema": "similarity", "prefer": [], "unwanted": []}))

        self.assertEqual(buffer.memory, [2, 3, 1])

    def test_preference_schema_mimics_native_profile_reranking_without_checkpoint(self):
        buffer = FakeBuffer([1, 2, 3, 4])
        tool = SemanticProfileRankingTool(
            "Movie Candidates Ranking Tool",
            "rank movies",
            FakeCorpus(),
            buffer,
            rec_num=2,
        )

        with patch.dict(
            os.environ,
            {"MATRAIX_CURRENT_USER_REQUEST": "I want a dark superhero crime movie."},
        ):
            output = tool.run(
                json.dumps(
                    {
                        "schema": "preference",
                        "prefer": ["Batman Begins"],
                        "unwanted": ["Saw"],
                    }
                )
            )

        self.assertEqual(buffer.memory[0], 2)
        self.assertNotIn(1, buffer.memory)
        self.assertNotIn(4, buffer.memory)
        self.assertIn("semantic profile", output)
        self.assertEqual(len(buffer.tracker), 1)


if __name__ == "__main__":
    unittest.main()
