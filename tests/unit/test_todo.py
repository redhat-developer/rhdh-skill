"""Tests for todo functionality."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_config_dir(monkeypatch):
    """Create a temporary data directory using RHDH_SKILLS_DATA_DIR env var."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / "data"
        config_dir.mkdir()
        monkeypatch.setenv("RHDH_SKILLS_DATA_DIR", str(config_dir))
        yield config_dir


class TestSlugify:
    """Tests for slugify function."""

    def test_lowercase(self):
        from rhdh.todo import slugify

        assert slugify("Hello World") == "hello-world"

    def test_removes_special_chars(self):
        from rhdh.todo import slugify

        assert slugify("Check @person's license!") == "check-person-s-license"

    def test_limits_length(self):
        from rhdh.todo import slugify

        long_title = "A" * 100
        slug = slugify(long_title)
        assert len(slug) <= 50


class TestListTodos:
    """Tests for list_todos function."""

    def test_creates_file_if_not_exists(self, temp_config_dir):
        from rhdh.todo import get_todo_file, list_todos

        list_todos()
        assert get_todo_file().exists()

    def test_returns_empty_list_for_new_file(self, temp_config_dir):
        from rhdh.todo import list_todos

        todos = list_todos()
        assert todos == []

    def test_parses_pending_todo(self, temp_config_dir):
        from rhdh.todo import get_todo_file, list_todos

        get_todo_file().write_text("""# Todos

---

## [ ] Test todo
**Created:** 2025-01-01

Description here.

---
""")
        todos = list_todos()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
        assert todos[0].done is False

    def test_parses_done_todo(self, temp_config_dir):
        from rhdh.todo import get_todo_file, list_todos

        get_todo_file().write_text("""# Todos

---

## [x] Completed todo
**Created:** 2025-01-01
**Completed:** 2025-01-02

Done!

---
""")
        todos = list_todos()
        assert len(todos) == 1
        assert todos[0].done is True
        assert todos[0].completed == "2025-01-02"

    def test_excludes_template_section(self, temp_config_dir):
        from rhdh.todo import get_todo_file, list_todos

        get_todo_file().write_text("""# Todos

---

## [ ] Real todo
**Created:** 2025-01-01

---

<!-- TEMPLATE
## [ ] Template title
**Created:** date

---
-->
""")
        todos = list_todos()
        assert len(todos) == 1
        assert todos[0].title == "Real todo"

    def test_filter_pending_only(self, temp_config_dir):
        from rhdh.todo import get_todo_file, list_todos

        get_todo_file().write_text("""# Todos

---

## [ ] Pending
**Created:** 2025-01-01

---

## [x] Done
**Created:** 2025-01-01

---
""")
        todos = list_todos(include_done=False)
        assert len(todos) == 1
        assert todos[0].title == "Pending"


class TestAddTodo:
    """Tests for add_todo function."""

    def test_adds_todo_with_title(self, temp_config_dir):
        from rhdh.todo import add_todo, list_todos

        add_todo("New task")
        todos = list_todos()
        assert len(todos) == 1
        assert todos[0].title == "New task"

    def test_adds_context(self, temp_config_dir):
        from rhdh.todo import add_todo, list_todos

        add_todo("New task", context="test-workspace")
        todos = list_todos()
        assert todos[0].context == "test-workspace"

    def test_prepends_new_todos(self, temp_config_dir):
        from rhdh.todo import add_todo, list_todos

        add_todo("First")
        add_todo("Second")
        todos = list_todos()
        # Most recent should be first in the file
        assert todos[0].title == "Second"
        assert todos[1].title == "First"


class TestMarkDone:
    """Tests for mark_done function."""

    def test_marks_todo_done(self, temp_config_dir):
        from rhdh.todo import add_todo, list_todos, mark_done

        add_todo("Task to complete")
        todo = mark_done("task-to")
        assert todo is not None
        assert todo.done is True

        todos = list_todos()
        assert todos[0].done is True

    def test_returns_none_for_unknown_slug(self, temp_config_dir):
        from rhdh.todo import mark_done

        result = mark_done("nonexistent")
        assert result is None


class TestAddNote:
    """Tests for add_note function."""

    def test_adds_note_to_todo(self, temp_config_dir):
        from rhdh.todo import add_note, add_todo, get_todo_file

        add_todo("Task with notes")
        add_note("task-with", "This is a note")

        content = get_todo_file().read_text()
        assert "This is a note" in content

    def test_returns_none_for_unknown_slug(self, temp_config_dir):
        from rhdh.todo import add_note

        result = add_note("nonexistent", "note")
        assert result is None


class TestGetTodo:
    """Tests for get_todo function."""

    def test_exact_match(self, temp_config_dir):
        from rhdh.todo import add_todo, get_todo

        add_todo("Specific task")
        todo = get_todo("specific-task")
        assert todo is not None
        assert todo.title == "Specific task"

    def test_partial_match(self, temp_config_dir):
        from rhdh.todo import add_todo, get_todo

        add_todo("Specific task")
        todo = get_todo("spec")
        assert todo is not None
        assert todo.title == "Specific task"

    def test_returns_none_when_not_found(self, temp_config_dir):
        from rhdh.todo import get_todo

        todo = get_todo("nonexistent")
        assert todo is None
