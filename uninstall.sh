#!/usr/bin/env bash
#
# Removes the Android automount service from the current user's account.
#
# Packages installed from the archive are left alone, since other things may be
# using them by now. Pass --purge to also drop the remembered device names.
#
set -euo pipefail

PREFIX="${PREFIX:-$HOME/.local}"
UNIT_DIR="$HOME/.config/systemd/user"
MOUNT_ROOT="$HOME/mnt/android"
NAME_CACHE="$HOME/.cache/android-automount"


main() {
	stop_service
	release_mounts
	remove_files
	if [ "${1:-}" = "--purge" ]; then
		rm -rf "$NAME_CACHE"
		echo "==> Removed remembered device names"
	fi
	echo
	echo "Removed. Packages installed from the archive were left in place."
}


stop_service() {
	echo "==> Stopping the service"
	systemctl --user disable --now android-automount.service 2>/dev/null || true
	rm -f "$UNIT_DIR/android-automount.service"
	systemctl --user daemon-reload 2>/dev/null || true
}


release_mounts() {
	[ -d "$MOUNT_ROOT" ] || return 0
	echo "==> Releasing any mounts still held"
	local mount_point
	for mount_point in "$MOUNT_ROOT"/*; do
		[ -e "$mount_point" ] || continue
		rmdir "$mount_point" 2>/dev/null && continue
		fusermount -u "$mount_point" 2>/dev/null || fusermount -uz "$mount_point" 2>/dev/null || true
		rmdir "$mount_point" 2>/dev/null || true
	done
	rmdir "$MOUNT_ROOT" 2>/dev/null || true
}


remove_files() {
	echo "==> Removing installed files"
	rm -f "$PREFIX/bin/android-automount" "$PREFIX/bin/adbfs"
}


main "$@"
