"""Runtime path fixes for the frozen PySide6 CRM executable."""

from __future__ import annotations

import os
import sys


def _prepend_env_path(name: str, value: str) -> None:
    current = os.environ.get(name, "")
    parts = [part for part in current.split(os.pathsep) if part]
    if value not in parts:
        os.environ[name] = os.pathsep.join([value, *parts])


base_dir = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
pyside_dir = os.path.join(base_dir, "PySide6")
plugins_dir = os.path.join(pyside_dir, "plugins")
platforms_dir = os.path.join(plugins_dir, "platforms")
qml_dir = os.path.join(pyside_dir, "qml")

if os.path.isdir(pyside_dir):
    _prepend_env_path("PATH", pyside_dir)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(pyside_dir)

if os.path.isdir(base_dir):
    _prepend_env_path("PATH", base_dir)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(base_dir)

if os.path.isdir(plugins_dir):
    os.environ["QT_PLUGIN_PATH"] = plugins_dir

if os.path.isdir(platforms_dir):
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms_dir

if os.path.isdir(qml_dir):
    os.environ["QML2_IMPORT_PATH"] = qml_dir
