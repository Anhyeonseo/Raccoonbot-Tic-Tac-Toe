# 설치 및 장비 준비

이 문서는 새 데스크톱 또는 Jetson에서 저장소를 실행 가능한 상태로 만드는 절차를
정리합니다. 실제 게임 운영은 [OPERATIONS_KR.md](OPERATIONS_KR.md)를 따릅니다.

## 1. 검증 환경

| 항목 | 실제 검증 구성 |
|---|---|
| 컴퓨팅 | Jetson Orin Nano Developer Kit, 512GB NVMe |
| OS | Ubuntu 24.04.3 LTS, aarch64 |
| JetPack / L4T | JetPack 7.2.1 / L4T R39.2.1 |
| CUDA / OpenCV | CUDA 13.2 / OpenCV 4.8.0 |
| 카메라 | Trust QHD Webcam, MJPEG 1920×1080 30fps |
| 로봇 | RaccoonBot, Mini Dongle+ USB 직렬·BLE 연결 |

위 표는 검증 이력이며 다른 버전의 호환성을 보장하지 않습니다. Jetson 설치와
RaccoonBot 패키지 설치는 각각 NVIDIA와 RobomationLAB의 최신 공식 안내를
우선합니다.

- [Jetson Orin Nano 시작 안내](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html)
- [RaccoonBot 사용자 가이드](https://github.com/RobomationLAB/RaccoonBot_Guide_KR)
- [RaccoonBot Python API](https://github.com/roboid-python/RaccoonBot_API_KR)

## 2. 데스크톱 개발 환경

Python 3.10 이상에서 카메라와 로봇 없이 규칙·AI·합성 비전·UI를 개발할 수
있습니다.

```bash
git clone https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row.git
cd Raccoonbot-Vision-Three-in-a-row
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-desktop.txt
python -m pytest -q
```

```bash
# 대화형 규칙 시험과 반복 시뮬레이션
raccoonbot-sim
raccoonbot-sim --games 1000 --seed 2026

# 하드웨어 없는 운영 UI 데모
raccoonbot-booth --windowed
```

## 3. Jetson 기본 점검

JetPack 설치와 첫 사용자 설정을 마친 뒤 저장소를 Jetson에 준비합니다. 프로젝트의
읽기 전용 진단 스크립트로 OS, CUDA, OpenCV, 저장장치, 카메라와 직렬 장치를
한 번에 확인할 수 있습니다.

```bash
cd ~/raccoonbot-vision-three-in-a-row
bash scripts/jetson_probe.sh
```

주요 개별 확인 명령은 다음과 같습니다.

```bash
cat /etc/nv_tegra_release
dpkg-query -W nvidia-jetpack
nvcc --version
python3 -c 'import cv2; print(cv2.__version__)'
df -h /
v4l2-ctl --list-devices
ls -l /dev/video* /dev/serial/by-id/*
```

카메라는 MJPEG 1920×1080 30fps를 사용합니다. 장치 번호가 달라질 수 있으므로
`v4l2-ctl --list-devices`로 실제 영상 노드를 확인합니다.

## 4. Jetson Python 환경

JetPack이 제공한 OpenCV와 NumPy를 유지하도록 시스템 패키지를 볼 수 있는
가상환경을 권장합니다.

```bash
cd ~/raccoonbot-vision-three-in-a-row
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --no-deps -e .
python -c 'import cv2; from robomation import RaccoonBot; print(cv2.__version__)'
python -m pytest -q
```

`robomation`과 Mini Dongle+는 공식 RaccoonBot 안내에 따라 준비합니다. 이 저장소는
공식 하드웨어 패키지를 재배포하지 않습니다.

## 5. 장비별 설정

다음 파일은 설치마다 달라지며 `.gitignore`에 포함됩니다.

- `config/robot_poses.json`: 27개 관절 자세와 최고 속도
- `config/vision.json`: 카메라, 보드 모서리와 빨강·노랑 HSV 설정

로봇 자세 파일은 템플릿에서 시작하고 실제 장비에서 teaching합니다.

```bash
cp config/robot_poses.template.json config/robot_poses.json
raccoonbot-teach-pose home --capture-current
raccoonbot-validate-poses config/robot_poses.json
```

자세 이름, teaching 순서와 운반 검증은
[config/README_KR.md](../config/README_KR.md)를 따릅니다. 카메라 설정은 먼저
CLI로 만들거나 기존 장비 설정을 복사한 뒤, 운영 UI의 현장 캘리브레이션으로 보드
네 모서리만 다시 지정할 수 있습니다.

```bash
raccoonbot-calibrate frame.png config/vision.json
bash scripts/configure_camera.sh /dev/video0
raccoonbot-live config/vision.json --frames 120
```

## 6. 노트북 연결과 UI 실행

행사장에서는 공유 Wi-Fi 대신 Jetson USB-C 장치망을 기본으로 사용합니다. 먼저
SSH 접속을 확인합니다.

```bash
ssh hyper@192.168.55.1
```

운영 노트북의 저장소에서 UI 실행 스크립트를 시작합니다.

```bash
RACCOONBOT_SSH_IDENTITY=/path/to/private-key \
bash scripts/run_booth_ui.sh
```

스크립트는 카메라 설정, Jetson 서버 실행과 `127.0.0.1:8080` SSH 터널을 함께
관리합니다. 브라우저에서 <http://127.0.0.1:8080>을 엽니다.

| 환경변수 | 기본값 | 용도 |
|---|---|---|
| `RACCOONBOT_JETSON_TARGET` | `hyper@192.168.55.1` | SSH 사용자와 주소 |
| `RACCOONBOT_REMOTE_PROJECT` | `/home/hyper/raccoonbot-vision-three-in-a-row` | Jetson 프로젝트 경로 |
| `RACCOONBOT_SSH_IDENTITY` | 비어 있음 | SSH 개인키 경로 |
| `RACCOONBOT_CAMERA_DEVICE` | `/dev/video0` | 카메라 영상 노드 |
| `RACCOONBOT_ROBOT_PORT` | 검증한 Mini Dongle+ by-id 경로 | 로봇 직렬 포트 |
| `RACCOONBOT_DIFFICULTY` | `easy` | `easy` 또는 `normal` |
| `RACCOONBOT_MOTION_MODE` | `direct` | 운영은 `direct`, 진단은 `interpolated` |
| `RACCOONBOT_WEB_PORT` | `8080` | 로컬·원격 UI 포트 |

개발실 Wi-Fi 주소를 사용할 때는 대상만 바꿉니다.

```bash
RACCOONBOT_JETSON_TARGET=hyper@192.168.35.236 \
RACCOONBOT_SSH_IDENTITY=/path/to/private-key \
bash scripts/run_booth_ui.sh
```

## 7. 설치 완료 기준

- `jetson_probe.sh`에서 NVMe, CUDA, OpenCV와 장치가 정상으로 표시됩니다.
- `raccoonbot-validate-poses`가 오류 없이 끝납니다.
- `raccoonbot-live`가 빈 판과 빨강·노랑 말을 올바르게 구분합니다.
- 노트북에서 UI가 열리고 `새 게임` 전 상태가 표시됩니다.
- 실제 이동 시험은 작업 영역을 비우고 전원을 즉시 차단할 운영자가 있을 때만
  진행합니다.
