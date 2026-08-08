"""Tests for how a device gets its directory name and its human readable name."""


def test_slug_is_lower_case_and_hyphenated(am):
	assert am.sanitize_label("REDMI Note 15 Pro+ 5G") == "redmi-note-15-pro-5g"
	assert am.sanitize_label(" Pixel 7 Pro\n") == "pixel-7-pro"
	assert am.sanitize_label("SM-G991B") == "sm-g991b"
	assert am.sanitize_label("Alex's Phone!!") == "alex-s-phone"


def test_slug_never_produces_a_hidden_or_empty_directory(am):
	assert am.sanitize_label(".hidden name.") == "hidden-name"
	assert am.sanitize_label("   ") == ""
	assert am.sanitize_label("!!!") == ""


def test_label_falls_back_to_the_serial_when_no_device_answers(am):
	am.run_device_command = lambda serial, command: ""
	assert am.read_device_label("ABA6A48F") == "aba6a48f"


def test_bluetooth_name_is_asked_before_the_stale_aosp_setting(am):
	assert am.DEVICE_NAME_COMMANDS[0] == ("settings", "get", "secure", "bluetooth_name")
	assert am.DEVICE_NAME_COMMANDS[1] == ("settings", "get", "global", "device_name")


def test_unset_settings_are_treated_as_no_answer(am):
	am.run_text = lambda command: "null\n"
	assert am.run_device_command("serial", ("settings", "get", "secure", "bluetooth_name")) == ""


def test_remembered_name_survives_a_round_trip(am):
	am.remember_device_name("aba6a48f", "REDMI Note 15 Pro+")
	assert am.remembered_device_name("aba6a48f") == "REDMI Note 15 Pro+"
	assert am.NAME_CACHE.exists()


def test_remembering_one_device_does_not_clobber_another(am):
	am.remember_device_name("aba6a48f", "REDMI Note 15 Pro+")
	am.remember_device_name("other", "Pixel 9")
	assert set(am.read_remembered_names()) == {"aba6a48f", "other"}


def test_blank_names_are_not_stored(am):
	am.remember_device_name("", "Ignored")
	am.remember_device_name("serial", "")
	assert am.read_remembered_names() == {}


def test_a_damaged_cache_reads_as_empty(am):
	am.NAME_CACHE.parent.mkdir(parents=True, exist_ok=True)
	am.NAME_CACHE.write_text("{ this is not json")
	assert am.read_remembered_names() == {}


def test_an_unwritable_cache_does_not_raise(am):
	am.NAME_CACHE = am.Path("/proc/cannot/write/here.json")
	am.remember_device_name("aba6a48f", "Whatever")


def test_display_name_prefers_the_owners_name_over_the_usb_descriptor(am, phone):
	assert am.device_display_name(phone) == "Xiaomi REDMI Note 15 Pro+ 5G"
	am.remember_device_name("aba6a48f", "REDMI Note 15 Pro+")
	assert am.device_display_name(phone) == "REDMI Note 15 Pro+"


def test_usb_descriptor_beats_the_hardware_database(am, phone):
	phone["ID_MODEL_FROM_DATABASE"] = "Mi/Redmi series (MTP)"
	phone["ID_VENDOR_FROM_DATABASE"] = "Xiaomi Inc."
	assert am.describe_usb_device(phone) == "Xiaomi REDMI Note 15 Pro+ 5G"


def test_unknown_devices_still_get_a_name(am):
	assert am.describe_usb_device({}) == "Android device"
