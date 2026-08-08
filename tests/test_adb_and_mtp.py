"""Tests for talking to the adb server and for locating a phone's MTP volume."""

import socket

import pytest


def test_device_list_is_parsed_into_states(am):
	payload = "ABC123\tdevice\nXYZ789\tunauthorized\n"
	assert am.parse_device_list(payload) == {"ABC123": "device", "XYZ789": "unauthorized"}


def test_an_empty_device_list_is_not_an_error(am):
	assert am.parse_device_list("") == {}


def test_lines_without_a_state_are_ignored(am):
	assert am.parse_device_list("List of devices attached\nABC\tdevice\n") == {"ABC": "device"}


def test_a_short_read_is_reported_rather_than_silently_truncated(am):
	server, client = socket.socketpair()
	client.sendall(b"OK")
	client.close()
	with pytest.raises(ConnectionError):
		am.receive_exactly(server, 4)


def test_a_rejected_request_raises(am):
	server, client = socket.socketpair()
	client.sendall(b"FAIL")
	with pytest.raises(ConnectionError):
		am.send_adb_request(server, "host:track-devices")


def test_mtp_volume_is_found_by_serial(am):
	am.run_text = lambda command: (
		"Volume(1): REDMI Note 15 Pro+ 5G\n"
		"  activation_root=mtp://Xiaomi_REDMI_Note_15_Pro+_5G_1a2b3c4d/\n"
		"  activation_root=google-drive://someone@example.com/\n"
	)
	assert am.find_mtp_address("1a2b3c4d") == "mtp://Xiaomi_REDMI_Note_15_Pro+_5G_1a2b3c4d/"
	assert am.find_mtp_address("nomatch") == ""


def test_an_empty_serial_does_not_match_every_volume(am):
	am.run_text = lambda command: "  activation_root=mtp://Some_Phone_1234/\n"
	assert am.find_mtp_address("") == ""


def test_non_mtp_volumes_are_never_returned(am):
	am.run_text = lambda command: "  activation_root=google-drive://1a2b3c4d@example.com/\n"
	assert am.find_mtp_address("1a2b3c4d") == ""


def test_waiting_gives_up_rather_than_blocking_forever(am):
	am.find_mtp_address = lambda serial: ""
	am.MTP_POLL_INTERVAL = 0.01
	assert am.wait_for_mtp_contents("1a2b3c4d", 0.05) == ""


def test_waiting_returns_the_address_once_storage_appears(am):
	looks = []

	def storage_appears_late(address):
		looks.append(1)
		return len(looks) > 1

	am.find_mtp_address = lambda serial: "mtp://phone/"
	am.mtp_storage_visible = storage_appears_late
	am.phone_left_the_bus = lambda serial: False
	am.MTP_POLL_INTERVAL = 0.01
	assert am.wait_for_mtp_contents("1a2b3c4d", 1.0) == "mtp://phone/"


def test_a_real_usb_serial_is_found_on_the_bus(am):
	"""Matched against whatever is actually plugged into this machine."""
	serials = [am.read_sysfs(path) for path in am.USB_DEVICES.glob("*/serial")]
	attached = [serial for serial in serials if serial]
	if not attached:
		pytest.skip("no USB device on this machine exposes a serial")
	assert am.usb_serial_attached(attached[0])


def test_an_unknown_serial_is_not_on_the_bus(am):
	assert not am.usb_serial_attached("nosuchserial0000")


def test_an_empty_serial_never_matches(am):
	assert not am.usb_serial_attached("")


def test_unreadable_sysfs_attributes_read_as_empty(am):
	assert am.read_sysfs(am.Path("/sys/bus/usb/devices/nosuchdevice/serial")) == ""


def test_a_present_phone_has_not_left_the_bus(am):
	am.usb_serial_attached = lambda serial: True
	assert not am.phone_left_the_bus("1a2b3c4d")


def test_a_single_absent_reading_is_not_an_unplug(am):
	"""Choosing File transfer detaches the phone for a moment; that is not a removal."""
	readings = iter([False, True])
	am.usb_serial_attached = lambda serial: next(readings)
	am.MTP_POLL_INTERVAL = 0.01
	assert not am.phone_left_the_bus("1a2b3c4d")


def test_two_absent_readings_mean_it_is_gone(am):
	am.usb_serial_attached = lambda serial: False
	am.MTP_POLL_INTERVAL = 0.01
	assert am.phone_left_the_bus("1a2b3c4d")


def test_waiting_gives_up_as_soon_as_the_phone_is_unplugged(am):
	"""The standing hint must not outlive the device it is about."""
	import time as clock
	am.find_mtp_address = lambda serial: ""
	am.phone_left_the_bus = lambda serial: True
	am.MTP_POLL_INTERVAL = 0.01
	started = clock.monotonic()
	assert am.wait_for_mtp_contents("1a2b3c4d", 30.0) == ""
	assert clock.monotonic() - started < 1.0, "gave up on the timeout instead of the unplug"


def test_the_hint_is_taken_back_when_the_phone_is_unplugged(am):
	sent = []
	am.notify = lambda title, body, urgency="normal", replaces="": sent.append((title, urgency, replaces))
	am.usb_serial_attached = lambda serial: False
	am.withdraw_hint("42", "1a2b3c4d", "Test Phone")
	assert sent == [("Test Phone disconnected", "low", "42")]


def test_the_hint_is_taken_back_when_the_phone_never_shares(am):
	sent = []
	am.notify = lambda title, body, urgency="normal", replaces="": sent.append((title, urgency, replaces))
	am.usb_serial_attached = lambda serial: True
	am.withdraw_hint("42", "1a2b3c4d", "Test Phone")
	assert sent == [("Test Phone was not mounted", "low", "42")]
