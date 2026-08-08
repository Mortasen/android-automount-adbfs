# Backlog

Known gaps, roughly in order of how likely they are to bite someone.

## The MTP hint can outlive the phone

If you pick **Mount via MTP**, get the "not sharing files yet" notification, then
unplug without granting access, the notification stays until its 3 minute timeout.
The dialog handles this case; this code path does not.

Fixing it needs a presence check that survives the re-enumeration caused by
choosing *File transfer* on the phone, so it cannot simply watch the udev device
path the way the dialog does. Matching on USB serial across `/sys/bus/usb/devices/*`
would work.

## Only the first dialog gets pinned on top

`find_dialog_window` matches the window by title. With two phones prompting at
once, the first match is pinned and the second may not be. Tracking the window id
per dialog would fix it. Two simultaneous dialogs is unlikely enough that this has
not been worth the plumbing.

## A dead mount is only noticed when adb changes state

If an `adbfs` process dies while the phone stays connected, the mount goes stale
and nothing remounts it, because the adb device state never changed. A periodic
liveness sweep over `self.mounts` using `is_readable_mount` would catch it.

## adbfs is built from source

It is not packaged in Debian or Ubuntu, so every install compiles it. Vendoring a
known-good revision, or pinning to a tag rather than the default branch, would make
installs reproducible.

## Untested beyond one phone and one desktop

Developed against a Xiaomi Redmi Note 15 Pro+ on Linux Mint 22.3 Cinnamon. The
media-interface heuristic that detects "Android phone without debugging" matches on
USB class `06:01` with no `ff:42`, which should hold generally but has not been
tried against other vendors.
