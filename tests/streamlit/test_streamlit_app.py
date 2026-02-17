import importlib
import json
import sys
import types

import pytest
from PIL import Image


class FakeSessionState:
    def __init__(self, initial=None):
        object.__setattr__(self, "_data", dict(initial or {}))

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getattr__(self, key):
        if key in self._data:
            return self._data[key]
        raise AttributeError(key)

    def __setattr__(self, key, value):
        if key == "_data":
            object.__setattr__(self, key, value)
        else:
            self._data[key] = value


class DummyContext:
    def __init__(self, st):
        self._st = st

    def __enter__(self):
        return self._st

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeStreamlit(types.ModuleType):
    def __init__(self, pressed=None, initial_state=None):
        super().__init__("streamlit")
        self.session_state = FakeSessionState(initial_state)
        self._pressed = set(pressed or set())
        self._calls = []
        self._rerun_called = False
        self.sidebar = DummyContext(self)

    @staticmethod
    def _normalize_label(label):
        return "".join(ch for ch in label if ord(ch) < 128).strip()

    def _record(self, name, *args, **kwargs):
        self._calls.append((name, args, kwargs))

    def set_page_config(self, **kwargs):
        self._record("set_page_config", kwargs)

    def title(self, text):
        self._record("title", text)

    def markdown(self, text, **kwargs):
        self._record("markdown", text, kwargs)

    def header(self, text):
        self._record("header", text)

    def subheader(self, text):
        self._record("subheader", text)

    def info(self, text):
        self._record("info", text)

    def warning(self, text):
        self._record("warning", text)

    def success(self, text):
        self._record("success", text)

    def error(self, text):
        self._record("error", text)

    def text(self, text):
        self._record("text", text)

    def write(self, text):
        self._record("write", text)

    def caption(self, text):
        self._record("caption", text)

    def image(self, *args, **kwargs):
        self._record("image", args, kwargs)

    def button(self, label, key=None, **kwargs):
        self._record("button", label, key, kwargs)
        if key and key in self._pressed:
            return True
        normalized = self._normalize_label(label)
        return label in self._pressed or normalized in self._pressed

    def checkbox(self, label, value=False, **kwargs):
        self._record("checkbox", label, value, kwargs)
        return value

    def number_input(self, label, value=0, **kwargs):
        self._record("number_input", label, value, kwargs)
        return value

    def text_input(self, label, value="", key=None, **kwargs):
        self._record("text_input", label, value, key, kwargs)
        return value

    def columns(self, spec):
        count = len(spec) if isinstance(spec, (list, tuple)) else spec
        self._record("columns", spec)
        return [DummyContext(self) for _ in range(count)]

    def expander(self, *args, **kwargs):
        self._record("expander", args, kwargs)
        return DummyContext(self)

    def spinner(self, *args, **kwargs):
        self._record("spinner", args, kwargs)
        return DummyContext(self)

    def rerun(self):
        self._record("rerun")
        self._rerun_called = True


def _load_app(monkeypatch, fake_st, overrides=None):
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    import st_app.streamlit_utils as streamlit_utils

    streamlit_utils = importlib.reload(streamlit_utils)
    for name, value in (overrides or {}).items():
        setattr(streamlit_utils, name, value)
    monkeypatch.setitem(sys.modules, "streamlit_utils", streamlit_utils)

    import st_app.streamlit_app as streamlit_app

    streamlit_app = importlib.reload(streamlit_app)
    return streamlit_app, streamlit_utils


def _make_image(path):
    image = Image.new("RGB", (10, 10), color=(255, 0, 0))
    image.save(path)


def _find_call_text(calls, name):
    for call_name, args, _ in calls:
        if call_name == name:
            for item in args:
                if isinstance(item, str):
                    return item
    return ""


def _has_call_with_text(calls, name, text):
    normalized_text = FakeStreamlit._normalize_label(text)
    for call_name, args, _ in calls:
        if call_name != name:
            continue
        for item in args:
            if isinstance(item, str):
                normalized_item = FakeStreamlit._normalize_label(item)
                if text in item or normalized_text in normalized_item:
                    return True
    return False


def test_initial_state_shows_no_images_message(monkeypatch):
    fake_st = FakeStreamlit()
    _load_app(monkeypatch, fake_st)

    assert fake_st.session_state.current_folder is None
    assert fake_st.session_state.image_files == []
    assert _has_call_with_text(
        fake_st._calls, "info", "Please load a folder"
    )


def test_load_folder_with_no_images_warns(monkeypatch, tmp_path):
    fake_st = FakeStreamlit(pressed={"Load Folder"})

    def _browse_folder():
        return str(tmp_path)

    def _load_folder_images(_folder):
        return []

    _load_app(
        monkeypatch,
        fake_st,
        overrides={
            "browse_folder": _browse_folder,
            "load_folder_images": _load_folder_images,
        },
    )

    assert fake_st.session_state.current_folder == str(tmp_path)
    assert fake_st.session_state.image_files == []
    assert _has_call_with_text(fake_st._calls, "warning", "No images found")
    assert fake_st._rerun_called is True


def test_load_folder_reads_predictions(monkeypatch, tmp_path):
    image_path = tmp_path / "test.jpg"
    _make_image(image_path)

    predictions = {
        "images": [
            {
                "file": str(image_path),
                "detections": [
                    {
                        "category": "deer",
                        "conf": 0.9,
                        "class_probs": {"deer": 0.9, "elk": 0.1},
                    }
                ],
            }
        ]
    }
    predictions_path = tmp_path / "predictions.json"
    predictions_path.write_text(json.dumps(predictions))

    fake_st = FakeStreamlit(pressed={"Load Folder"})

    def _browse_folder():
        return str(tmp_path)

    def _load_folder_images(_folder):
        return [str(image_path)]

    _load_app(
        monkeypatch,
        fake_st,
        overrides={
            "browse_folder": _browse_folder,
            "load_folder_images": _load_folder_images,
        },
    )

    assert fake_st.session_state.predictions_data is not None
    assert fake_st.session_state.show_predictions is True
    assert _has_call_with_text(
        fake_st._calls, "subheader", "Detection Results"
    )


def test_copy_button_invokes_copy(monkeypatch, tmp_path):
    image_path = tmp_path / "image.jpg"
    _make_image(image_path)

    destination = tmp_path / "dest"

    fake_st = FakeStreamlit(
        pressed={"copy1"},
        initial_state={
            "image_files": [str(image_path)],
            "current_image_index": 0,
            "folder_1": str(destination),
        },
    )

    calls = []

    def _copy_image_to_folder(path, folder):
        calls.append((path, folder))
        return True

    _load_app(
        monkeypatch,
        fake_st,
        overrides={"copy_image_to_folder": _copy_image_to_folder},
    )

    assert calls == [(str(image_path), str(destination))]
