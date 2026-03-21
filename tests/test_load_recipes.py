"""Tests for recipe file loading."""
import os
import tempfile
from pathlib import Path

import pytest


class TestLoadRecipes:
    def test_loads_md_files_sorted_by_name(self, tmp_path):
        """Recipes load in filename order."""
        (tmp_path / "02_b.md").write_text("# Recipe B\nContent B")
        (tmp_path / "01_a.md").write_text("# Recipe A\nContent A")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "# Recipe A" in result
        assert "# Recipe B" in result
        assert result.index("Recipe A") < result.index("Recipe B")

    def test_raises_on_empty_directory(self, tmp_path):
        """Must fail loudly if no recipe files found."""
        from prompts import _load_recipes
        with pytest.raises(FileNotFoundError, match="No .md files"):
            _load_recipes(recipes_dir=tmp_path)

    def test_ignores_non_md_files(self, tmp_path):
        (tmp_path / "01_a.md").write_text("# Recipe A")
        (tmp_path / "notes.txt").write_text("not a recipe")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "Recipe A" in result
        assert "not a recipe" not in result

    def test_replaces_today_placeholder(self, tmp_path):
        """Recipe files use {today} as a placeholder for the current date."""
        from datetime import date
        (tmp_path / "01_test.md").write_text('orderDate: "{today}"')

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert date.today().isoformat() in result
        assert "{today}" not in result

    def test_concatenates_with_separator(self, tmp_path):
        (tmp_path / "01_a.md").write_text("# A")
        (tmp_path / "02_b.md").write_text("# B")

        from prompts import _load_recipes
        result = _load_recipes(recipes_dir=tmp_path)

        assert "# A\n\n# B" in result
