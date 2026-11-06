import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.env import load_env_file


class EnvironmentFileTests(unittest.TestCase):
    def test_loads_values_and_preserves_existing_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text(
                "# Configuration\nGOOGLE_PLACES_API_KEY='test-key'\nPORT=8001\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"PORT": "8000"}, clear=True):
                load_env_file(path)
                self.assertEqual(os.environ["GOOGLE_PLACES_API_KEY"], "test-key")
                self.assertEqual(os.environ["PORT"], "8000")

    def test_missing_file_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            load_env_file(Path(directory) / ".env")

    def test_invalid_line_reports_location_without_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("invalid setting\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, r"\.env, línea 1"):
                load_env_file(path)


if __name__ == "__main__":
    unittest.main()
