import unittest

from news_engine.claude_script import _schema


def _refs(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for child in value.values():
            yield from _refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _refs(child)


class ClaudeSchemaTests(unittest.TestCase):
    def test_schema_is_self_contained_for_claude_json_schema(self):
        schema = _schema()
        self.assertNotIn("$defs", schema)
        self.assertEqual(list(_refs(schema)), [])


if __name__ == "__main__":
    unittest.main()
