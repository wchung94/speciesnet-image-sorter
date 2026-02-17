# Tests

This directory contains unit tests for the SpeciesNetImageSorter application.

## Running Tests

To run all tests:
```bash
uv run pytest
```

To run tests with verbose output:
```bash
uv run pytest -v
```

To run a specific test file:
```bash
uv run pytest tests/test_file_operations.py
```

To run a specific test:
```bash
uv run pytest tests/test_file_operations.py::TestFileOperations::test_copy_current_image_to_new_folder
```

## Test Structure

- `test_file_operations.py` - Tests for file copying functionality
- `test_image_loader.py` - Tests for image loading and folder scanning
- `test_folder_buttonwidget.py` - Tests for folder tab widgets
- `test_thumbnail_creator.py` - Tests for thumbnail generation
- `test_logs_window.py` - Tests for logging handler
- `test_worker.py` - Tests for background worker threads
- `conftest.py` - Shared pytest fixtures

## Test Coverage

The tests cover:
- File operations (copying images)
- Image loading from folders
- Folder widget management
- Thumbnail creation
- Log message handling
- Background worker execution

## Notes

- Tests use PyQt6's QApplication which requires proper cleanup
- Some tests use temporary directories that are automatically cleaned up
- Worker tests may take a few seconds as they run actual subprocesses
