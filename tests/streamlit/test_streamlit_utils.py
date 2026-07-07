import importlib
import sys
import types


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__("streamlit")
        self.warnings = []
        self.errors = []

    def warning(self, message):
        self.warnings.append(message)

    def error(self, message):
        self.errors.append(message)


def _non_main_thread():
    return object()


def _main_thread():
    return object()


def test_browse_folder_skips_tk_on_macos_background_thread(monkeypatch):
    fake_st = FakeStreamlit()
    monkeypatch.setitem(sys.modules, "streamlit", fake_st)

    import app.streamlit_utils as streamlit_utils

    streamlit_utils = importlib.reload(streamlit_utils)
    monkeypatch.setattr(streamlit_utils, "TKINTER_AVAILABLE", True)
    monkeypatch.setattr(streamlit_utils.sys, "platform", "darwin")
    monkeypatch.setattr(
        streamlit_utils.threading,
        "current_thread",
        _non_main_thread,
    )
    monkeypatch.setattr(
        streamlit_utils.threading,
        "main_thread",
        _main_thread,
    )

    class _TkSentinel:
        def Tk(self):
            raise AssertionError("Tk should not be created on a background thread")

    monkeypatch.setattr(streamlit_utils, "tk", _TkSentinel())

    assert streamlit_utils.browse_folder() is None
    assert fake_st.warnings
    assert "background thread" in fake_st.warnings[0]
    assert not fake_st.errors