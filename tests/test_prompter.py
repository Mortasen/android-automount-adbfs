"""Tests that one plugged-in phone produces exactly one dialog, and only when it should."""

import time


def test_a_phone_is_prompted_about_once(am, phone):
	runs = []
	prompter = am.DebuggingPrompter()
	am.handle_missing_debugging = lambda properties: runs.append(properties) or time.sleep(0.4)
	am.DEBUGGING_PROMPT_DELAY = 0.01

	prompter.schedule(phone)
	prompter.schedule(phone)
	prompter.schedule(dict(phone, DEVPATH="/devices/x/usb3/3-2"))
	time.sleep(0.2)

	assert len(runs) == 1


def test_an_answered_phone_is_not_asked_about_again(am, phone):
	prompter = am.DebuggingPrompter()
	am.handle_missing_debugging = lambda properties: None

	prompter.prompt(phone)

	assert not prompter.claim(phone)


def test_re_enumeration_does_not_reset_the_answer(am, phone):
	"""Answering the dialog often changes the USB mode, which changes the device path."""
	prompter = am.DebuggingPrompter()
	am.handle_missing_debugging = lambda properties: None

	prompter.prompt(phone)

	assert not prompter.claim(dict(phone, DEVPATH="/devices/x/usb3/3-9"))


def test_unplugging_clears_the_answer(am, phone):
	prompter = am.DebuggingPrompter()
	am.handle_missing_debugging = lambda properties: None
	prompter.prompt(phone)

	prompter.forget(phone["DEVPATH"])

	assert prompter.claim(phone)


def test_forgetting_an_unknown_path_does_not_release_a_live_claim(am, phone):
	prompter = am.DebuggingPrompter()
	prompter.claim(phone)

	prompter.forget("/devices/nonexistent")

	assert not prompter.claim(phone)


def test_the_answer_expires_so_a_missed_removal_cannot_wedge_it(am, phone):
	prompter = am.DebuggingPrompter()
	am.handle_missing_debugging = lambda properties: None
	am.DECISION_COOLDOWN = 0.05
	prompter.prompt(phone)

	assert not prompter.claim(phone)
	time.sleep(0.1)
	assert prompter.claim(phone)
