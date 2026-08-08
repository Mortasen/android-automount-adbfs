# android-automount-adbfs

Mounts Android phones over `adb` the moment you plug them in, and asks what to do
when it can't.

Linux desktops already mount phones over MTP, which is slow, refuses to expose
anything outside the media folders, and drops the connection if you look at it
wrong. `adbfs` gives you the phone's whole filesystem as an ordinary directory. The
catch is that nothing wires it up for you: you have to notice the phone, find its
serial, pick a mount point, and clean up when you unplug. This does that.

Everything runs as a **systemd user service**. There are no udev rules, no root
daemon, and nothing installed outside your home directory apart from packages from
your distribution's archive.

## What it does

| Situation | What happens |
|---|---|
| Phone plugged in, USB debugging on, authorised | Mounts at `~/mnt/android/<device name>`, notification |
| Phone plugged in, not yet authorised | Notification asking you to tap **Allow** on the phone |
| Phone plugged in, USB debugging off | A dialog offering to mount over MTP instead, or to do nothing |
| You enable USB debugging while the dialog is open | The dialog closes itself and the phone mounts |
| You unplug while the dialog is open | The dialog closes itself |
| Phone unplugged | Unmounts and removes the directory |

The mount is named after the name you gave the phone in its own settings,
lower-cased and hyphenated, so a phone called `Pixel 9 Pro` lands at
`~/mnt/android/pixel-9-pro`.

## Requirements

Built for **Linux Mint Cinnamon**, and should work on any GTK desktop with a
notification daemon. It needs `zenity` for the dialog, `wmctrl` to keep that dialog
on top, and `gvfs` for the MTP fallback. The installer pulls these in.

Python 3.10 or newer. No third-party Python packages.

## Install

```bash
git clone https://github.com/Mortasen/android-automount-adbfs.git
cd android-automount-adbfs
./install.sh
```

The installer asks for `sudo` **once**, to install packages from the archive
(`build-essential`, `libfuse-dev`, `adb`, `zenity`, `wmctrl`, `gvfs-backends` and a
few others). It then builds [`adbfs-rootless`](https://github.com/spion/adbfs-rootless)
from source, because it is not packaged in Debian or Ubuntu, and installs
everything under `~/.local`.

To remove it:

```bash
./uninstall.sh          # add --purge to also forget remembered device names
```

Packages from the archive are left alone.

## Where things go

| Path | What |
|---|---|
| `~/.local/bin/android-automount` | the service |
| `~/.local/bin/adbfs` | the FUSE filesystem, built during install |
| `~/.config/systemd/user/android-automount.service` | the unit |
| `~/mnt/android/` | where phones appear |
| `~/.cache/android-automount/device-names.json` | remembered device names |

Follow what it is doing with:

```bash
journalctl --user -u android-automount -f
```

## Things worth knowing

**Your phone's name is only readable over adb.** USB descriptors carry the
marketing name burnt into the ROM, not the name you set. So when USB debugging is
off, the dialog uses the last name it saw over adb, falling back to the USB
descriptor for a phone it has never mounted.

**Vendor skins disagree about where the device name lives.** The AOSP setting is
`global device_name`, but at least Xiaomi's HyperOS writes renames to
`secure bluetooth_name` and leaves the AOSP one stamped with the marketing name
forever. Both are tried, `bluetooth_name` first. If your phone shows the wrong
name, `adb shell settings list secure | grep name` will tell you where yours keeps it.

**Renames may not appear immediately.** HyperOS commits the new name when the
settings screen closes, not when you type it. Press Home after renaming, then
replug.

**MTP mounts are left for gvfs to clean up, deliberately.** Nothing leaks: gvfs
owns that mount and drops it when the phone leaves the bus. This service never
unmounts one itself because tearing down a *live* MTP session leaves it half-open
on the phone, and nothing short of a replug reopens it. If MTP ever wedges with
`Unable to open MTP device`, unplug and plug back in.

## Development

```bash
pip install --user pytest
python3 -m pytest tests/ -q
```

The tests cover the pure logic: udev event parsing, device naming, the dialog's
exit-code handling and withdrawal conditions, prompt de-duplication, and the adb
wire protocol. Anything touching real hardware is stubbed.

## Credits

The heavy lifting is done by [`adbfs-rootless`](https://github.com/spion/adbfs-rootless)
by spion, itself a fork of Calvin Tee's `adbfs`, licensed BSD. This project only
wires it into the desktop.
