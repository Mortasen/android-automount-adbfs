#!/usr/bin/env bash
#
# Installs the Android automount service into the current user's account.
#
# Everything lands under $HOME and runs as a systemd user service. The only step
# needing root is installing build and runtime packages from the archive, and it
# is the only place this script calls sudo.
#
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local}"
UNIT_DIR="$HOME/.config/systemd/user"
ADBFS_REPO="https://github.com/spion/adbfs-rootless.git"

BUILD_PACKAGES=(build-essential git libfuse-dev pkg-config)
RUNTIME_PACKAGES=(adb zenity wmctrl libnotify-bin gvfs-backends gvfs-fuse fuse3)


main() {
	require_linux
	require_user_systemd
	install_packages
	build_adbfs
	install_files
	enable_service
	report
}


require_linux() {
	if [ "$(uname -s)" != "Linux" ]; then
		die "This service only works on Linux."
	fi
	if ! command -v apt-get >/dev/null; then
		die "This installer expects a Debian or Ubuntu based system such as Linux Mint."
	fi
}


require_user_systemd() {
	if ! systemctl --user show-environment >/dev/null 2>&1; then
		die "No systemd user session found. Log in to a desktop session and try again."
	fi
}


install_packages() {
	local missing
	missing=$(missing_packages "${BUILD_PACKAGES[@]}" "${RUNTIME_PACKAGES[@]}")
	if [ -z "$missing" ]; then
		echo "==> All required packages are already installed"
		return
	fi
	echo "==> These packages are needed and will be installed with sudo:"
	echo "    $missing"
	# shellcheck disable=SC2086
	sudo apt-get install -y $missing
}


missing_packages() {
	local package missing=""
	for package in "$@"; do
		if ! dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q "^install ok installed$"; then
			missing="$missing $package"
		fi
	done
	echo "$missing" | sed 's/^ //'
}


build_adbfs() {
	if [ -x "$PREFIX/bin/adbfs" ]; then
		echo "==> adbfs is already built at $PREFIX/bin/adbfs"
		return
	fi
	local work
	work="$(mktemp -d)"
	trap 'rm -rf "$work"' RETURN
	echo "==> Building adbfs-rootless from source"
	git clone --depth 1 "$ADBFS_REPO" "$work/adbfs-rootless" >/dev/null 2>&1
	make -C "$work/adbfs-rootless" >/dev/null
	install -Dm755 "$work/adbfs-rootless/adbfs" "$PREFIX/bin/adbfs"
}


install_files() {
	echo "==> Installing into $PREFIX/bin and $UNIT_DIR"
	install -Dm755 "$REPO/bin/android-automount" "$PREFIX/bin/android-automount"
	install -Dm644 "$REPO/systemd/android-automount.service" "$UNIT_DIR/android-automount.service"
}


enable_service() {
	echo "==> Enabling the service"
	systemctl --user daemon-reload
	systemctl --user enable --now android-automount.service
}


report() {
	echo
	if systemctl --user is-active --quiet android-automount.service; then
		echo "Installed. Plug in an Android device to try it."
		echo "  Mounts appear in : ~/mnt/android/<device name>"
		echo "  Follow the log   : journalctl --user -u android-automount -f"
	else
		echo "Installed, but the service is not running. Check:"
		echo "  systemctl --user status android-automount"
	fi
}


die() {
	echo "error: $*" >&2
	exit 1
}


main "$@"
