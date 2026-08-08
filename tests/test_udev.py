"""Tests for reading the udev event stream and classifying what appeared on the bus."""


def test_properties_are_parsed_and_the_header_line_ignored(am):
	block = [
		"UDEV  [123.4] add   /devices/x (usb)",
		"ACTION=add",
		"DEVTYPE=usb_device",
		"ID_USB_INTERFACES=:060101:",
	]
	assert am.parse_udev_properties(block) == {
		"ACTION": "add",
		"DEVTYPE": "usb_device",
		"ID_USB_INTERFACES": ":060101:",
	}


def test_events_are_split_on_blank_lines(am):
	lines = iter(["ACTION=add\n", "DEVTYPE=usb_device\n", "\n", "ACTION=remove\n", "\n"])
	assert [event["ACTION"] for event in am.read_udev_events(lines)] == ["add", "remove"]


def test_a_trailing_event_without_a_blank_line_is_dropped(am):
	lines = iter(["ACTION=add\n", "\n", "ACTION=remove\n"])
	assert [event["ACTION"] for event in am.read_udev_events(lines)] == ["add"]


def test_media_only_device_is_a_phone_without_debugging(am, phone):
	assert am.is_phone_without_debugging(phone)


def test_a_device_offering_adb_is_left_alone(am, phone):
	phone["ID_USB_INTERFACES"] = ":060101:ff4201:"
	assert not am.is_phone_without_debugging(phone)


def test_non_media_devices_are_ignored(am, phone):
	phone["ID_USB_INTERFACES"] = ":030102:"
	assert not am.is_phone_without_debugging(phone)


def test_only_whole_devices_count_not_their_interfaces(am, phone):
	phone["DEVTYPE"] = "usb_interface"
	assert not am.is_phone_without_debugging(phone)


def test_removals_are_recognised(am, phone):
	assert am.is_usb_removal({"ACTION": "remove", "DEVTYPE": "usb_device"})
	assert not am.is_usb_removal(phone)
	assert not am.is_usb_removal({"ACTION": "remove", "DEVTYPE": "usb_interface"})


def test_devices_are_keyed_by_serial_so_re_enumeration_matches(am, phone):
	assert am.device_key(phone) == "1a2b3c4d"
	assert am.device_key(dict(phone, DEVPATH="/devices/x/usb3/3-9")) == "1a2b3c4d"


def test_devices_without_a_serial_fall_back_to_their_path(am):
	assert am.device_key({"DEVPATH": "/devices/x"}) == "/devices/x"


def test_interface_classes_are_matched_by_prefix(am):
	assert am.has_adb_interface(":060101:ff4201:")
	assert not am.has_adb_interface(":060101:")
	assert am.has_media_interface(":060101:ff4201:")
	assert not am.has_media_interface(":ff4201:")
