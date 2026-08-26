#!/usr/bin/env bash

# Apply the fixed Trust QHD Webcam controls validated for the home setup.
# Run this again after reconnecting the camera or rebooting the Jetson.

set -euo pipefail

camera_device="${1:-/dev/video0}"

if ! test -c "$camera_device"; then
    printf 'camera device is not available: %s\n' "$camera_device" >&2
    exit 1
fi
if ! command -v v4l2-ctl >/dev/null 2>&1; then
    printf 'v4l2-ctl is not installed\n' >&2
    exit 1
fi

v4l2-ctl -d "$camera_device" --set-ctrl=power_line_frequency=2
v4l2-ctl -d "$camera_device" --set-ctrl=white_balance_automatic=0
v4l2-ctl -d "$camera_device" --set-ctrl=white_balance_temperature=4600
v4l2-ctl -d "$camera_device" --set-ctrl=auto_exposure=1
v4l2-ctl -d "$camera_device" --set-ctrl=exposure_time_absolute=333
v4l2-ctl -d "$camera_device" --set-ctrl=focus_automatic_continuous=0
v4l2-ctl -d "$camera_device" --set-ctrl=focus_absolute=68
v4l2-ctl -d "$camera_device" --set-ctrl=gain=64

v4l2-ctl -d "$camera_device" --get-ctrl=power_line_frequency,white_balance_automatic,white_balance_temperature,auto_exposure,exposure_time_absolute,focus_automatic_continuous,focus_absolute,gain
