#!/usr/bin/env bash

# Read-only Jetson bring-up report. This script does not install packages,
# change services, or modify system settings.

set -u

section() {
    printf '\n===== %s =====\n' "$1"
}

run_if_available() {
    local command_name="$1"
    shift
    if command -v "$command_name" >/dev/null 2>&1; then
        "$command_name" "$@" 2>&1 || true
    else
        printf '%s: not installed\n' "$command_name"
    fi
}

section "IDENTITY"
printf 'date: '
date --iso-8601=seconds 2>/dev/null || date
printf 'hostname: '
hostname
printf 'user: '
id

section "OPERATING SYSTEM"
uname -a
printf 'architecture: '
uname -m
if test -r /etc/os-release; then
    sed -n '1,12p' /etc/os-release
fi

section "JETSON"
if test -r /etc/nv_tegra_release; then
    sed -n '1,5p' /etc/nv_tegra_release
else
    printf '/etc/nv_tegra_release: not found\n'
fi

if command -v dpkg-query >/dev/null 2>&1; then
    dpkg-query -W -f='${Package}\t${Version}\n' \
        nvidia-jetpack nvidia-l4t-core nvidia-l4t-kernel 2>/dev/null || true
fi

run_if_available nvpmodel -q
run_if_available nvcc --version

section "PYTHON AND COMPUTER VISION"
run_if_available python3 --version
if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' 2>&1 || true
import platform

print("platform:", platform.platform())
try:
    import cv2
except Exception as exc:
    print("opencv: unavailable", repr(exc))
else:
    print("opencv:", cv2.__version__)
    try:
        print("cuda devices visible to OpenCV:", cv2.cuda.getCudaEnabledDeviceCount())
    except Exception as exc:
        print("opencv cuda query failed:", repr(exc))
PY
fi

section "MEMORY AND STORAGE"
run_if_available free -h
run_if_available df -hT /
run_if_available lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL

section "NETWORK"
run_if_available ip -br address
run_if_available ip route
printf 'hostname addresses: '
hostname -I 2>/dev/null || true

section "SSH"
if command -v systemctl >/dev/null 2>&1; then
    printf 'active: '
    systemctl is-active ssh 2>&1 || true
    printf 'enabled: '
    systemctl is-enabled ssh 2>&1 || true
else
    printf 'systemctl: not installed\n'
fi

section "VIDEO DEVICES"
find /dev -maxdepth 1 -type c -name 'video*' -print 2>/dev/null | sort
if test -d /sys/class/video4linux; then
    for device_path in /sys/class/video4linux/video*; do
        test -e "$device_path" || continue
        device_name="$(basename "$device_path")"
        printf '%s: ' "$device_name"
        if test -r "$device_path/name"; then
            cat "$device_path/name"
        else
            printf 'unknown\n'
        fi
    done
fi
run_if_available v4l2-ctl --list-devices

section "USB DEVICES"
run_if_available lsusb

section "SERIAL DEVICES"
find /dev -maxdepth 1 -type c \( \
    -name 'ttyACM*' -o \
    -name 'ttyUSB*' -o \
    -name 'ttyTHS*' \
\) -print 2>/dev/null | sort

section "DEVICE ACCESS GROUPS"
groups

section "REPORT COMPLETE"
printf 'This report was read-only. No system settings were changed.\n'

