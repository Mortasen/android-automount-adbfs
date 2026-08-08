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
		"  activation_root=mtp://Xiaomi_REDMI_Note_15_Pro+_5G_aba6a48f/\n"
		"  activation_root=google-drive://someone@example.com/\n"
	)
	assert am.find_mtp_address("aba6a48f") == "mtp://Xiaomi_REDMI_Note_15_Pro+_5G_aba6a48f/"
	assert am.find_mtp_address("nomatch") == ""


def test_an_empty_serial_does_not_match_every_volume(am):
	am.run_text = lambda command: "  activation_root=mtp://Some_Phone_1234/\n"
	assert am.find_mtp_address("") == ""


def test_non_mtp_volumes_are_never_returned(am):
	am.run_text = lambda command: "  activation_root=google-drive://aba6a48f@example.com/\n"
	assert am.find_mtp_address("aba6a48f") == ""


def test_waiting_gives_up_rather_than_blocking_forever(am):
	am.find_mtp_address = lambda serial: ""
	am.MTP_POLL_INTERVAL = 0.01
	assert am.wait_for_mtp_contents("aba6a48f", 0.05) == ""


def test_waiting_returns_the_address_once_storage_appears(am):
	looks = []

	def storage_appears_late(address):
		looks.append(1)
		return len(looks) > 1

	am.find_mtp_address = lambda serial: "mtp://phone/"
	am.mtp_storage_visible = storage_appears_late
	am.MTP_POLL_INTERVAL = 0.01
	assert am.wait_for_mtp_contents("aba6a48f", 1.0) == "mtp://phone/"
