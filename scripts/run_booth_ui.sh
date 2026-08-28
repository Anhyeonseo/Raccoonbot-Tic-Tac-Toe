#!/usr/bin/env bash
set -euo pipefail

jetson_target="${RACCOONBOT_JETSON_TARGET:-hyper@192.168.55.1}"
web_port="${RACCOONBOT_WEB_PORT:-8080}"
remote_project="${RACCOONBOT_REMOTE_PROJECT:-/home/hyper/raccoonbot-vision-three-in-a-row}"
identity="${RACCOONBOT_SSH_IDENTITY:-}"
motion_mode="${RACCOONBOT_MOTION_MODE:-direct}"
difficulty="${RACCOONBOT_DIFFICULTY:-easy}"
camera_device="${RACCOONBOT_CAMERA_DEVICE:-/dev/video0}"
robot_port="${RACCOONBOT_ROBOT_PORT:-/dev/serial/by-id/usb-Robomation_Mini_Dongle+_CCC0C21B94C3-if00}"

if [[ ! "$web_port" =~ ^[0-9]+$ ]] || ((web_port < 1 || web_port > 65535)); then
  echo "RACCOONBOT_WEB_PORT must be within 1..65535" >&2
  exit 2
fi
if [[ "$motion_mode" != "interpolated" && "$motion_mode" != "direct" ]]; then
  echo "RACCOONBOT_MOTION_MODE must be interpolated or direct" >&2
  exit 2
fi
if [[ "$difficulty" != "easy" && "$difficulty" != "normal" ]]; then
  echo "RACCOONBOT_DIFFICULTY must be easy or normal" >&2
  exit 2
fi
if [[ ! "$camera_device" =~ ^/dev/video([0-9]+)$ ]]; then
  echo "RACCOONBOT_CAMERA_DEVICE must look like /dev/video0" >&2
  exit 2
fi
camera_index="${BASH_REMATCH[1]}"

ssh_args=(-tt -L "${web_port}:127.0.0.1:${web_port}")
if [[ -n "$identity" ]]; then
  ssh_args+=(-i "$identity")
fi

echo "Jetson target: ${jetson_target}"
echo "Robot motion mode: ${motion_mode}"
echo "AI difficulty: ${difficulty}"
echo "Camera device: ${camera_device}"
echo "Robot port: ${robot_port}"
echo "노트북 브라우저에서 http://127.0.0.1:${web_port} 를 여세요."
echo "종료는 이 터미널에서 Ctrl+C를 누르고 로봇 연결 해제를 기다리세요."

exec ssh "${ssh_args[@]}" "$jetson_target" \
  "cd '$remote_project' && bash scripts/configure_camera.sh '$camera_device' && .venv/bin/raccoonbot-web --web-port '$web_port' --motion-mode '$motion_mode' --difficulty '$difficulty' --robot-port '$robot_port' --device '$camera_index' --joint-step 6 --confirm-hardware"
