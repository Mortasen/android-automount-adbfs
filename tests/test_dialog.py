"""Tests for the USB debugging dialog: how it is built, answered, and withdrawn."""

import pytest


class FakeDialog:
	"""Stands in for the zenity process so each outcome can be replayed."""

	def __init__(self, returncode, output=""):
		self.returncode = returncode
		self.output = output

	def poll(self):
		return self.returncode

	def communicate(self):
		return self.output, ""

	def terminate(self):
		self.returncode = -15


@pytest.fixture
def answered(am, phone):
	"""Replay a dialog that exits with a given status, without drawing anything."""
	am.pin_dialog_above_other_windows = lambda: None
	am.debugging_became_available = lambda properties, before: False

	def replay(returncode, output=""):
		am.subprocess.Popen = lambda *args, **kwargs: FakeDialog(returncode, output)
		return am.ask_about_disabled_debugging("Test Phone", phone, set())

	return replay


def test_dialog_names_the_device_and_offers_two_ways_out(am):
	command = am.build_debugging_dialog("Test Phone")
	assert command[0] == "zenity"
	assert f"--title={am.DIALOG_TITLE}" in command
	assert f"--ok-label={am.MTP_BUTTON_LABEL}" in command
	assert "--cancel-label=Don't mount" in command
	assert any(part.startswith("--text=") and "Test Phone" in part for part in command)


def test_the_retry_button_is_gone(am):
	command = am.build_debugging_dialog("Test Phone")
	assert not any(part.startswith("--extra-button") for part in command)


def test_dialog_text_explains_that_it_closes_itself(am):
	text = am.debugging_dialog_text("Test Phone")
	assert "pick one of the options below" in text
	assert "closed automatically as soon as USB debugging is enabled" in text


def test_the_affirmative_button_mounts_over_mtp(am, answered):
	assert answered(0) == am.CHOICE_MOUNT_MTP


def test_dismissing_mounts_nothing(am, answered):
	assert answered(1) == am.CHOICE_DECLINE


def test_closing_the_window_mounts_nothing(am, answered):
	assert answered(5) == am.CHOICE_DECLINE


def test_a_withdrawn_dialog_is_not_a_refusal(am, answered):
	"""A dialog we took down ourselves must not be recorded as the user saying no."""
	assert answered(-15) == am.CHOICE_RESOLVED


def test_dialog_stands_while_the_phone_is_present_and_unreachable(am, phone):
	am.debugging_became_available = lambda properties, before: False
	am.usb_device_present = lambda properties: True
	assert am.dialog_no_longer_applies(phone, set()) == ""


def test_dialog_is_withdrawn_once_adb_reaches_the_phone(am, phone):
	am.debugging_became_available = lambda properties, before: True
	assert am.dialog_no_longer_applies(phone, set()) == "it became reachable over adb"


def test_dialog_is_withdrawn_when_the_phone_is_unplugged(am, phone):
	am.debugging_became_available = lambda properties, before: False
	am.usb_device_present = lambda properties: False
	assert am.dialog_no_longer_applies(phone, set()) == "it was unplugged"


def test_re_enumeration_is_not_mistaken_for_an_unplug(am, phone):
	"""Enabling debugging also removes the old device path, so adb gets a second look."""
	looks = []

	def adb_arrives_late(properties, before):
		looks.append(1)
		return len(looks) > 1

	am.debugging_became_available = adb_arrives_late
	am.usb_device_present = lambda properties: False
	assert am.dialog_no_longer_applies(phone, set()) == "it became reachable over adb"


def test_presence_is_read_from_the_real_device_path(am, phone):
	assert not am.usb_device_present(dict(phone, DEVPATH="/devices/nowhere/usb9/9-9"))
	assert not am.usb_device_present({})


def test_the_dialog_window_is_found_by_title(am):
	am.run_text = lambda command: (
		"0x04000007  0 host Some Editor\n"
		f"0x06e00008  1 host {am.DIALOG_TITLE}\n"
	)
	assert am.find_dialog_window() == "0x06e00008"


def test_unrelated_windows_are_not_pinned(am):
	am.run_text = lambda command: "0x04000007  0 host Some Editor\n"
	assert am.find_dialog_window() == ""
