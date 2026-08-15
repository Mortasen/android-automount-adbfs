"""
Covers running adbfs in the foreground: relaying its errors to the journal, and
reacting when it stops.

adbfs used to be left to daemonise, which sent its output to /dev/null and made a
collapsed mount invisible until something touched it and got EIO. These tests pin
the behaviour that replaced it.
"""

import io
import pathlib
import subprocess


class FakeAdbfs:
	"""Stands in for a running adbfs process."""

	def __init__(self, errors="", status=0):
		self.stderr = io.StringIO(errors)
		self.status = status
		self.terminated = False
		self.killed = False

	def wait(self):
		return self.status

	def terminate(self):
		self.terminated = True

	def kill(self):
		self.killed = True

	def communicate(self, timeout=None):
		return "", self.stderr.read()


def test_adbfs_runs_in_the_foreground(am):
	"""Daemonising is what loses both the error output and the exit."""
	recorded = {}
	am.subprocess.Popen = lambda command, **kwargs: recorded.update(command=command, kwargs=kwargs)
	am.start_adbfs("1a2b3c4d", pathlib.Path("/mnt/phone"))
	assert "-f" in recorded["command"]
	assert recorded["kwargs"]["stdout"] is subprocess.DEVNULL, "per-operation tracing must be dropped"
	assert recorded["kwargs"]["stderr"] is subprocess.PIPE, "errors must be captured"
	assert recorded["kwargs"]["env"]["ANDROID_SERIAL"] == "1a2b3c4d"


def test_error_lines_reach_the_log(am, caplog):
	adbfs = FakeAdbfs("adb: device '1a2b3c4d' not found\nfuse: mountpoint is not empty\n")
	am.forward_adbfs_errors(adbfs, "phone")
	assert "adb: device '1a2b3c4d' not found" in caplog.text
	assert "fuse: mountpoint is not empty" in caplog.text


def test_blank_error_lines_are_not_logged(am, caplog):
	am.forward_adbfs_errors(FakeAdbfs("\n   \n"), "phone")
	assert "adbfs[phone]" not in caplog.text


def test_a_deliberate_unmount_is_not_treated_as_a_collapse(am):
	"""Unmounting on disconnect kills adbfs; that must not look like a failure."""
	sent = []
	am.notify = lambda *a, **k: sent.append(a)
	am.unmount_path = lambda path: sent.append(("unmounted", path))
	mounter = am.DeviceMounter()
	mounter.handle_adbfs_exit("1a2b3c4d", pathlib.Path("/mnt/gone"), "phone", 0, 900.0)
	assert sent == [], "a mount already released must be left alone"


def test_a_collapsed_mount_is_cleaned_up(am):
	released = []
	am.unmount_path = released.append
	am.notify = lambda *a, **k: None
	am.read_adb_serials = lambda: set()
	mounter = am.DeviceMounter()
	point = am.MOUNT_ROOT / "phone"
	mounter.mounts["1a2b3c4d"] = point
	mounter.handle_adbfs_exit("1a2b3c4d", point, "phone", 1, 900.0)
	assert released == [point], "the stale mount must not be left returning EIO"
	assert "1a2b3c4d" not in mounter.mounts


def test_a_healthy_mount_that_dies_is_put_back(am):
	remounted = []
	am.unmount_path = lambda path: None
	am.notify = lambda *a, **k: None
	am.read_adb_serials = lambda: {"1a2b3c4d"}
	mounter = am.DeviceMounter()
	mounter.mount = remounted.append
	point = am.MOUNT_ROOT / "phone"
	mounter.mounts["1a2b3c4d"] = point
	mounter.handle_adbfs_exit("1a2b3c4d", point, "phone", 1, 900.0)
	assert remounted == ["1a2b3c4d"]


def test_a_mount_that_collapses_immediately_is_not_retried(am):
	"""Retrying a mount that cannot survive would just loop."""
	remounted = []
	am.unmount_path = lambda path: None
	am.notify = lambda *a, **k: None
	am.read_adb_serials = lambda: {"1a2b3c4d"}
	mounter = am.DeviceMounter()
	mounter.mount = remounted.append
	point = am.MOUNT_ROOT / "phone"
	mounter.mounts["1a2b3c4d"] = point
	mounter.handle_adbfs_exit("1a2b3c4d", point, "phone", 1, 2.0)
	assert remounted == []


def test_an_unplugged_phone_is_not_remounted(am):
	remounted = []
	am.unmount_path = lambda path: None
	am.notify = lambda *a, **k: None
	am.read_adb_serials = lambda: set()
	mounter = am.DeviceMounter()
	mounter.mount = remounted.append
	point = am.MOUNT_ROOT / "phone"
	mounter.mounts["1a2b3c4d"] = point
	mounter.handle_adbfs_exit("1a2b3c4d", point, "phone", 1, 900.0)
	assert remounted == []


def test_a_mount_that_never_came_up_leaves_nothing_running(am, caplog):
	released = []
	am.unmount_path = released.append
	am.notify = lambda *a, **k: None
	adbfs = FakeAdbfs("fuse: bad mount point\n")
	point = am.MOUNT_ROOT / "phone"
	am.abandon_adbfs(adbfs, point, "phone")
	assert adbfs.terminated, "the process must not be left behind"
	assert released == [point]
	assert "fuse: bad mount point" in caplog.text


def test_an_unstoppable_adbfs_is_killed(am):
	class Stubborn(FakeAdbfs):
		def communicate(self, timeout=None):
			raise subprocess.TimeoutExpired("adbfs", timeout)

	am.unmount_path = lambda path: None
	am.notify = lambda *a, **k: None
	adbfs = Stubborn()
	am.abandon_adbfs(adbfs, am.MOUNT_ROOT / "phone", "phone")
	assert adbfs.killed, "a process ignoring SIGTERM must be killed"
