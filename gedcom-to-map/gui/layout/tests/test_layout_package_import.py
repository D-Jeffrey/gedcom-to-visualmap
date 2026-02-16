"""Regression tests for gui.layout package import behavior.

These tests ensure `gui.layout` can be imported in environments where
wxPython is not installed (for example, Ubuntu core CI lanes).
"""

import builtins
import importlib
import sys


def test_gui_layout_import_without_wx(monkeypatch):
    """Importing gui.layout should not fail when wx is unavailable."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    # Force a fresh import path through gui.layout.__init__
    for key in list(sys.modules.keys()):
        if key == "gui.layout" or key.startswith("gui.layout."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.layout")

    assert module is not None
    assert hasattr(module, "__all__")
    assert isinstance(module.__all__, list)


def test_gui_actions_import_without_wx(monkeypatch):
    """Importing gui.actions should not fail when wx is unavailable."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    for key in list(sys.modules.keys()):
        if key == "gui.actions" or key.startswith("gui.actions."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.actions")

    assert module is not None
    assert hasattr(module, "__all__")
    assert isinstance(module.__all__, list)


def test_gui_actions_file_operations_import_without_wx(monkeypatch):
    """Importing gui.actions.file_operations should not require wx."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    for key in list(sys.modules.keys()):
        if key == "gui.actions" or key.startswith("gui.actions."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.actions.file_operations")

    assert module is not None


def test_gui_core_import_without_wx(monkeypatch):
    """Importing gui.core should not fail when wx is unavailable."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    for key in list(sys.modules.keys()):
        if key == "gui.core" or key.startswith("gui.core."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.core")

    assert module is not None
    assert hasattr(module, "__all__")
    assert isinstance(module.__all__, list)


def test_gui_panels_import_without_wx(monkeypatch):
    """Importing gui.panels should not fail when wx is unavailable."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    for key in list(sys.modules.keys()):
        if key == "gui.panels" or key.startswith("gui.panels."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.panels")

    assert module is not None
    assert hasattr(module, "__all__")
    assert isinstance(module.__all__, list)


def test_gui_processors_import_without_wx(monkeypatch):
    """Importing gui.processors should not fail when wx is unavailable."""

    original_import = builtins.__import__

    def blocked_wx_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("No module named 'wx'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_wx_import)

    for key in list(sys.modules.keys()):
        if key == "gui.processors" or key.startswith("gui.processors."):
            sys.modules.pop(key, None)

    module = importlib.import_module("gui.processors")

    assert module is not None
    assert hasattr(module, "__all__")
    assert isinstance(module.__all__, list)
