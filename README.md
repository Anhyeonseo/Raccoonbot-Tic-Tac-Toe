# RaccoonBot Vision Three-in-a-Row

[![tests](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml/badge.svg)](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml)

RGB 카메라와 Jetson Orin Nano, RaccoonBot을 이용한 3개 말 이동형 3목 대전 프로젝트입니다.

참가자와 로봇은 말 3개씩을 사용합니다. 배치가 끝난 뒤에는 자기 말 하나를 원하는 빈칸으로 옮길 수 있습니다. 카메라가 보드 변화를 인식하고, 게임 엔진이 로봇의 다음 수를 정하며, RaccoonBot이 실제 말을 집어서 옮깁니다.

## 현재 상태

**1차 MVP 구현과 실제 장비 시연을 완료했습니다.** 게임 규칙, 불완전 AI,
보드 인식, 물리 행동 검증, 공식 `robomation.RaccoonBot` 어댑터, 실제 장비
게임 러너와 부스 UI 데모가 구현되어 있습니다. 자동 테스트 87개를 데스크톱과
Jetson에서 통과했습니다.

Jetson Orin Nano NVMe의 JetPack 7.2.1, Trust QHD Webcam의 1080p MJPEG,
Mini Dongle+ BLE 통신을 실제 장비에서 확인했습니다. 관찰 `home`, 높은 운반
`transit`, 9개 보드 칸과 노란 말 대기 위치 3곳의 hover/grasp를 포함한 26개
자세를 모두 teaching했고, 각 위치의 실제 집기·놓기와 셀 간 자유 이동을
검증했습니다.

최종 실기에서는 고정 노출·화이트밸런스와 수동 보드 모서리 보정으로 빨강·노랑
6개를 안정적으로 인식했습니다. 빈 판에서 시작한 실제 게임 2판을 끝까지
진행했고, 사람 수 인식, AI 판단, 로봇 배치, 동작 후 카메라 검증과 승리 판정이
연속 동작했습니다. 운반 중에는 집은 말을 `transit`까지 들어 올린 뒤 목표 칸으로
이동해 다른 말을 건드리지 않도록 했습니다.

현재 실제 게임은 CLI의 `Enter` 입력으로 운영합니다. 전체 화면 부스 UI와 실제
장비의 직접 연결, USB HID 굿즈 버튼, 장시간 반복 운전과 비상정지 리허설은
후속 안정화 범위입니다. 자세한 실기 결과는
[`docs/PROJECT_STATUS_KR.md`](docs/PROJECT_STATUS_KR.md)에 정리되어 있습니다.

## 시연 영상

[![RaccoonBot 3목 게임 시연 영상](assets/demo-thumbnail.jpg)](https://drive.google.com/file/d/1d0tjxeQ3BWgaXYCpIjII7FlVT4bhdUxd/view?usp=drive_link)

이미지를 클릭하면 Google Drive에서 시연 영상을 볼 수 있습니다.

## 확정 규칙

1. 참가자가 선공한다.
2. 두 플레이어는 빈칸에 말 3개를 번갈아 배치한다.
3. 배치 도중 3목을 만들면 즉시 승리한다.
4. 말 6개가 모두 배치되면 이동 단계로 전환한다.
5. 이동 단계에서는 자기 말 하나를 원하는 빈칸으로 옮긴다.
6. 이동 직후 3목을 만들면 승리한다.
7. 같은 보드와 차례가 3회 등장하거나 이동 단계가 10턴을 넘으면 무승부로 종료한다.

현장 UI에서는 무승부를 `라쿤봇 방어 성공`으로 표현할 수 있습니다.

## 시스템 구성

```text
RGB Camera
    -> Board Detector
    -> Game State Validator
    -> Imperfect AI
    -> Robot Motion Controller
    -> Camera Verification
```

각 모듈은 다음처럼 분리합니다.

- `game.py`: 규칙, 턴, 승패 및 반복 상태 판정
- `strategy.py`: 일부러 완벽하지 않은 AI 정책과 선택 이유
- `vision/`: 원근 보정, 3×3 빨강/노랑 판독, 안정화, 물리 행동 추론
- `robot/`: 안전한 hover/grasp 순서, 가상 로봇, 공식 `robomation` API 어댑터
- `app/session.py`: 사람 수부터 로봇 동작 결과 재확인까지의 상태 머신

## 보드 좌표

```text
1 | 2 | 3
--+---+--
4 | 5 | 6
--+---+--
7 | 8 | 9
```

사람에게 보여주는 보드와 자세 이름은 1~9를 사용합니다. Python 내부 배열 인덱스만 0~8입니다.

## 개발 순서

- [x] 게임 규칙 및 상태 모델
- [x] 불완전 AI 정책과 자동 경기 시뮬레이터
- [x] 원근 보정과 9칸 분할
- [x] 빨강/노랑 말 인식 및 프레임 안정화
- [x] 참가자 행동 유효성 검사
- [x] 가상 RaccoonBot 픽앤플레이스
- [x] 공식 `robomation.RaccoonBot` 드라이버 어댑터
- [x] 카메라 기반 로봇 동작 결과 검증 상태기
- [x] 합성 이미지, 캘리브레이션, 자세 검증 CLI
- [x] A4 임시 보드와 말
- [x] Jetson Orin Nano NVMe·JetPack 7.2.1·SSH 브링업
- [x] 실제 카메라 기준 임시 캘리브레이션과 정지 이미지 인식
- [x] 실제 카메라 실시간 연속 인식
- [x] 실제 9칸 hover/grasp teaching 및 제자리 픽앤플레이스 검증
- [x] 실제 3개 대기 위치 hover/grasp teaching 및 제자리 픽앤플레이스 검증
- [x] Jetson ARM64 + Mini Dongle+ 통신 확인
- [x] J1 저속 왕복 및 DC 그리퍼 단독 안전 시험
- [x] 물리 Teach 버튼 기반 자세 저장 도구와 `home` 저장
- [x] 1~9번 전체 실제 말 제자리 픽앤플레이스
- [x] 높은 `transit`을 경유하는 실제 말 운반
- [x] 실제 카메라·로봇 게임 러너와 `Enter` 턴 입력
- [x] 빈 판에서 실제 게임 2판 완주 및 시연 촬영
- [x] 하드웨어 없는 부스용 전체 화면 UI 데모
- [ ] 실제 카메라·로봇 게임 러너와 전체 화면 부스 UI 통합
- [ ] USB HID 굿즈 버튼 연결
- [ ] 반복 운전 및 안전 테스트

## 실행

Python 3.10 이상을 기준으로 합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-desktop.txt
python -m pytest -q
```

설치 후 클릭 가능한 부스 화면 데모를 실행합니다.

```bash
raccoonbot-booth --windowed
```

`--windowed`를 빼면 전체 화면으로 실행되고, `Esc`를 누르면 창 모드로 돌아옵니다.

대화형 게임과 1,000회 자동 경기:

```bash
raccoonbot-sim
raccoonbot-sim --games 1000 --seed 2026
```

Jetson의 실제 카메라에서 안정화된 보드 상태를 읽습니다. 5프레임 중 4프레임이 일치해야 출력되며, `--frames 0`은 `Ctrl+C`까지 계속 실행합니다.

```bash
bash scripts/configure_camera.sh /dev/video0
raccoonbot-live config/vision.json --frames 120 --save-warped work/live-warped.jpg
```

실제 판정 전에는 기본 30프레임을 워밍업으로 버립니다. 카메라를 다시 연결하거나 Jetson을 재부팅하면 고정 카메라 설정 스크립트를 다시 실행합니다. 현장 조명이 달라지면 수동값을 그대로 사용하지 말고 캘리브레이션과 함께 다시 측정합니다.

현재 자세를 바로 저장하거나, 모터를 해제한 뒤 물리 Teach 버튼으로 한 자세를 저장합니다.

```bash
raccoonbot-teach-pose home --capture-current
raccoonbot-teach-pose cell_1_hover --confirm-manual-teaching
raccoonbot-teach-pose stock_1_grasp --start-from stock_1_hover \
  --confirm-manual-teaching
```

수동 teaching 중에는 팔이 중력으로 내려올 수 있으므로 반드시 손으로 받치고 천천히 움직입니다.

1번 칸의 hover/grasp 자세를 저장한 뒤, 로봇을 `transit`에 놓고 실제 말의 제자리 집기·놓기를 시험합니다.

```bash
raccoonbot-smoke-pick config/robot_poses.json --cell 1 --speed 10 --confirm-motion
raccoonbot-smoke-pick config/robot_poses.json --stock 1 --speed 10 --confirm-motion
```

대기 말을 보드에 배치하거나 보드의 말을 원하는 빈칸으로 옮기는 종단 간 시험:

```bash
raccoonbot-smoke-transfer config/robot_poses.json --stock 1 --cell 5 \
  --speed 10 --confirm-motion
raccoonbot-smoke-transfer config/robot_poses.json --from-cell 5 --cell 9 \
  --speed 10 --confirm-motion
```

실제 게임 운반은 말을 집은 뒤 항상 높은 `transit` 자세까지 상승한 다음
목표 칸으로 이동합니다. 부스용 검증 속도는 `45`, 관절 보간 간격은 `6°`를
기준으로 사용합니다.

실제 카메라와 로봇으로 한 게임을 진행합니다. 사람은 말을 놓고 작업 영역에서 손을 뺀 뒤 `Enter`를 눌러 턴 완료를 알립니다.

```bash
bash scripts/configure_camera.sh /dev/video0
raccoonbot-play-hardware --joint-step 6 --seed 0 --confirm-hardware
```

새 게임은 반드시 빈 판에서 시작합니다. 프로그램이 `사람 차례입니다`를 출력한
뒤에만 빨간 말을 놓고 `Enter`를 누릅니다. 중단된 배치 단계를 물리 보드 상태에서
이어갈 때만 `--resume-placement`를 추가합니다.

안전 중심의 현재 설정은 로봇 한 수에 약 1분 30초~2분이 걸릴 수 있습니다.
속도를 더 높이려면 행사 전에 전체 셀 조합과 반복 운전을 다시 검증해야 합니다.

현장 최종형에서는 별도 굿즈 버튼을 USB HID 키보드의 `Enter` 입력으로 연결합니다. 따라서 게임 상태기와 카메라 검증 로직을 바꾸지 않고 입력 장치만 교체할 수 있습니다. 완료 버튼은 턴 제출용이며 비상정지와는 별도로 운용합니다.

그리퍼를 작동하지 않고 잠긴 셀의 hover/grasp 경로만 검증할 때는 다음처럼 실행합니다.

```bash
raccoonbot-smoke-pick config/robot_poses.json --cell 7 --speed 10 \
  --dry-run --allow-provisional-cell --confirm-motion
```

## 저장소 구조

```text
assets/                  A4 임시 보드와 색상 말
config/                  로봇 자세 입력 템플릿
docs/                    개발 계획, 데스크톱 준비, Jetson 브링업
scripts/                 Jetson 장치 진단 스크립트
src/raccoonbot_game/
  app/                   게임 세션과 부스 UI 모델
  robot/                 가상/실제 로봇 드라이버와 동작 계획
  tools/                 실행·캘리브레이션 CLI
  vision/                보드 보정, 색상 인식, 상태 전이 검증
tests/                   단위·통합·시뮬레이션 테스트
```

실제 장비마다 달라지는 `config/vision.json`과 `config/robot_poses.json`은 저장소에 포함하지 않습니다. 템플릿만 복사해서 사용합니다.

## 문서

- [현재 완료 범위와 다음 작업](docs/PROJECT_STATUS_KR.md)
- [SSD 도착 전 데스크톱 준비 및 도구 사용법](docs/DESKTOP_PREPARATION_KR.md)
- [전체 개발 계획](docs/DEVELOPMENT_PLAN_KR.md)
- [Jetson 브링업](docs/JETSON_BRINGUP_KR.md)
- [로컬 캘리브레이션과 자세 설정](config/README_KR.md)

Git 원격 작업과 push는 프로젝트 소유자가 직접 수행합니다.
