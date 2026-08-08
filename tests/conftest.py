"""
Shared fixtures for the daemon's tests.

The daemon is a single executable script rather than an importable package, so it
is loaded by path. It is reloaded for every test because the tests replace module
level functions to stand in for adb, udev, gvfs and zenity, and a shared instance
would let one test's stubs leak into the next.
"""

import pathlib
import importlib.util
import importlib.machinery

import pytest


MODULE_PATH = pathlib.Path(__file__).resolve().parent.parent / "bin" / "android-automount"


@pytest.fixture
def am(tmp_path):
	"""Load a private copy of the daemon, pointed at throwaway directories."""
	loader = importlib.machinery.SourceFileLoader("android_automount", str(MODULE_PATH))
	spec = importlib.util.spec_from_loader("android_automount", loader)
	module = importlib.util.module_from_spec(spec)
	loader.exec_module(module)
	module.NAME_CACHE = tmp_path / "cache" / "device-names.json"
	module.MOUNT_ROOT = tmp_path / "mnt"
	module.ADB_RECHECK_INTERVAL = 0.01
	return module


@pytest.fixture
def phone():
	"""The udev properties of an Android phone plugged in without USB debugging."""
	return {
		"ACTION": "add",
		"DEVTYPE": "usb_device",
		"ID_USB_INTERFACES": ":060101:",
		"ID_VENDOR": "Xiaomi",
		"ID_MODEL": "REDMI_Note_15_Pro+_5G",
		"ID_SERIAL_SHORT": "aba6a48f",
		"DEVPATH": "/devices/pci0000:00/usb3/3-1",
	}
