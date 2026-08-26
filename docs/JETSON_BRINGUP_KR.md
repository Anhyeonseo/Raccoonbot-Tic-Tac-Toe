# Jetson Orin Nano 브링업 및 원격 개발 가이드

## 목표 구성

```text
개발 PC
  └─ SSH / 유선 Ethernet
       └─ Jetson Orin Nano
            ├─ RGB 카메라
            ├─ Mini Dongle+
            └─ RaccoonBot
```

개발 PC는 코드 편집과 원격 명령에 사용한다. 카메라 입력, 로봇 통신과 실제 애플리케이션 실행은 모두 Jetson에서 수행한다.

## 1. 먼저 확인할 것

기존 설치를 지우거나 다시 플래시하기 전에 다음 상태를 확인한다.

- Jetson이 현재 정상 부팅되는가?
- 로그인할 사용자 이름과 비밀번호를 알고 있는가?
- microSD 또는 NVMe 중 어디에서 부팅하는가?
- 현재 JetPack 및 Jetson Linux 버전은 무엇인가?
- 기존 파일 중 보존할 데이터가 있는가?

기존 OS가 정상 부팅된다면 즉시 재설치하지 않는다. 먼저 이 문서의 진단 스크립트를 실행한 뒤 유지 또는 재설치를 결정한다.

## 2. 확정 JetPack 기준

2026-08-26 실제 장비에서 다음 구성을 확인했다.

- Jetson Orin Nano Developer Kit
- TAMMUZ M740Q 512GB NVMe (`/dev/nvme0n1p1` 루트 파일시스템)
- Jetson ISO r39.2.1
- JetPack 7.2.1 / Jetson Linux R39.2.1
- Ubuntu 24.04.3 LTS, aarch64
- CUDA 13.2, OpenCV 4.8.0

Jetson ISO를 USB 메모리에 원시 이미지로 기록하고, UEFI/QSPI 업데이트 후 NVMe를 설치 대상으로 선택했다. JetPack SDK 구성요소는 첫 부팅 후 `sudo apt install nvidia-jetpack`으로 설치했다.

주의: ISO USB 생성과 NVMe 설치는 선택한 저장장치 내용을 지운다. 장치 이름과 용량을 확인하기 전에는 진행하지 않는다.

공식 자료:

- <https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html>
- <https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/setup_jetpack.html>

## 3. 최초 부팅

가장 빠르고 실수가 적은 방법은 첫 설정 때만 모니터, 키보드와 마우스를 연결하는 것이다.

1. Jetson을 비전도성 표면에 둔다.
2. 부팅 저장장치를 장착한다.
3. 모니터, 키보드와 마우스를 연결한다.
4. 번들 전원 어댑터를 연결한다.
5. EULA, 언어, 시간대, 사용자 계정과 호스트 이름을 설정한다.
6. 로그인 후 터미널을 연다.

권장 호스트 이름 예시:

```text
raccoon-jetson
```

USB-C 포트는 데이터 및 복구 용도이므로 Jetson 전원은 정식 전원 어댑터를 사용한다.

## 4. 현재 시스템 진단

저장소가 Jetson에 준비된 후 다음을 실행한다.

```bash
bash scripts/jetson_probe.sh
```

저장소가 아직 없다면 스크립트 파일만 Jetson에 복사해서 실행해도 된다. 이 스크립트는 시스템을 변경하지 않고 다음 정보를 출력한다.

- CPU 아키텍처 및 운영체제
- Jetson Linux 및 JetPack 버전
- Python, CUDA와 OpenCV 상태
- 카메라 장치
- USB 및 직렬 장치
- 네트워크 주소
- SSH 서비스 상태
- 사용자 장치 접근 그룹
- 저장공간과 메모리

출력 결과를 개발 기록에 보관한다.

## 5. SSH 준비

Jetson에서 SSH 상태를 확인한다.

```bash
systemctl is-active ssh
```

`active`가 아니고 OpenSSH 서버가 설치되어 있다면:

```bash
sudo systemctl enable --now ssh
```

설치되어 있지 않을 때만 다음을 실행한다.

```bash
sudo apt update
sudo apt install openssh-server
sudo systemctl enable --now ssh
```

## 6. 권장 네트워크: 같은 공유기 또는 스위치

가장 단순한 방식이다.

1. 개발 PC와 Jetson을 같은 공유기 또는 스위치에 연결한다.
2. Jetson에서 IP 주소를 확인한다.

```bash
hostname -I
ip -br address
```

3. 개발 PC에서 접속한다.

```bash
ssh <사용자명>@<JETSON_IP>
```

호스트 이름 검색이 지원되면 다음도 가능하다.

```bash
ssh <사용자명>@raccoon-jetson.local
```

행사장에서는 공유기의 DHCP 예약 기능으로 Jetson IP를 고정하는 것을 권장한다.

## 7. 대안: PC와 Jetson 직접 Ethernet 연결

공유기가 없으면 Ethernet 케이블로 직접 연결할 수 있다.

Ubuntu 개발 PC의 네트워크 설정에서 유선 연결의 IPv4 방식을 `다른 컴퓨터와 공유`로 설정한다. 다시 연결하면 개발 PC가 Jetson에 DHCP 주소를 제공한다.

개발 PC에서 Jetson 주소 후보를 확인한다.

```bash
ip -br address
ip neighbor
```

보통 공유 연결은 `10.42.0.0/24` 대역을 사용하지만 실제 주소를 명령 출력으로 확인한다. 주소를 추측해서 고정하지 않는다.

연결 후:

```bash
ssh <사용자명>@<JETSON_IP>
```

직결 환경이 확정되면 이후 별도의 정적 IP 프로필을 만들 수 있다. 최초 연결 단계에서는 Ubuntu의 공유 연결이 더 간단하다.

## 8. SSH 키 등록

비밀번호 입력 없이 안전하게 개발하려면 개발 PC에서 키를 생성하고 Jetson에 공개키를 등록한다.

기존 SSH 키가 있는지 먼저 확인한다.

```bash
ls ~/.ssh
```

키가 없다면 개발 PC에서 생성한다.

```bash
ssh-keygen -t ed25519
```

Jetson에 등록한다.

```bash
ssh-copy-id <사용자명>@<JETSON_IP>
```

접속을 확인한다.

```bash
ssh <사용자명>@<JETSON_IP> 'hostname && uname -m'
```

예상 아키텍처는 `aarch64`다.

## 9. 개발 PC의 SSH 별칭

개발 PC의 `~/.ssh/config`에 다음과 같은 항목을 둘 수 있다.

```sshconfig
Host raccoon-jetson
    HostName <JETSON_IP>
    User <사용자명>
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

이후 다음처럼 접속한다.

```bash
ssh raccoon-jetson
```

IP와 사용자 이름을 실제 값으로 교체한다.

## 10. 기본 개발 패키지

현재 설치 상태를 진단한 뒤 필요한 패키지만 설치한다.

```bash
sudo apt update
sudo apt install python3.12-venv python3-pip v4l-utils usbutils ffmpeg rsync
```

Git 설치와 저장소 동기화는 사용자가 별도로 관리한다.

Python 가상환경은 시스템 OpenCV와 Jetson 라이브러리를 사용할 수 있도록 다음 방식을 우선 검토한다.

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -c 'import cv2; print(cv2.__version__)'
```

JetPack이 제공한 OpenCV와 NumPy를 유지하기 위해 프로젝트는 의존성을 다시 받지 않고 설치한다.

```bash
python -m pip install --no-deps -e .
python -m pip install 'pytest>=8,<9'
python -m pytest -q
```

## 11. 카메라 브링업

카메라는 Jetson USB 또는 CSI 포트에 연결한다.

USB 카메라 확인:

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

지원 형식 확인:

```bash
v4l2-ctl --device /dev/video0 --list-formats-ext
```

Python 확인:

```bash
python3 -c 'import cv2; c=cv2.VideoCapture(0); ok,f=c.read(); print(c.isOpened(), ok, None if f is None else f.shape); c.release()'
```

카메라가 여러 `/dev/video*` 노드를 만들 수 있으므로 첫 번째 번호가 항상 영상 노드라고 가정하지 않는다.

CSI 카메라는 센서별 드라이버와 GStreamer 파이프라인이 필요할 수 있으므로 정확한 모델 확인 후 별도 설정한다.

## 12. Mini Dongle+ 브링업

카메라 확인이 끝난 뒤 Mini Dongle+를 Jetson에 연결한다.

연결 전후 USB 목록을 비교한다.

```bash
lsusb
```

커널 이벤트를 보면서 동글을 연결한다.

```bash
sudo dmesg --follow
```

새 직렬 장치가 생기는지 확인한다.

```bash
find /dev -maxdepth 1 -name 'ttyACM*' -o -name 'ttyUSB*'
```

직렬 장치가 생기면 현재 사용자가 접근 가능한지 확인한다.

```bash
ls -l /dev/ttyACM0
groups
```

필요한 경우에만 사용자를 `dialout` 그룹에 추가하고 다시 로그인한다.

```bash
sudo usermod -aG dialout "$USER"
```

동글이 Web Serial 전용으로 동작하더라도 USB 장치 식별자와 Chromium 연결 여부를 기록한다.

## 13. 브링업 완료 조건

- Jetson이 안정적으로 부팅된다.
- JetPack 및 Jetson Linux 버전을 기록했다.
- 개발 PC에서 유선 SSH 접속이 된다.
- 재부팅 후에도 Jetson 주소를 찾고 접속할 수 있다.
- Jetson에서 Python과 OpenCV를 불러올 수 있다.
- RGB 카메라에서 실제 프레임 한 장을 읽을 수 있다.
- Mini Dongle+의 USB 식별자와 장치 노드를 확인했다.
- 라쿤봇 홈 및 그리퍼 최소 제어 경로를 정했다.
- 카메라 또는 동글 연결이 끊겼을 때 진단 방법을 알고 있다.

이 조건을 만족한 뒤 게임 보드 인식과 로봇 티칭 개발로 진행한다.
