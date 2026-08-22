# RaccoonBot Vision Three-in-a-Row

[![tests](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml/badge.svg)](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml)

RGB 카메라와 Jetson Orin Nano, RaccoonBot을 이용한 3개 말 이동형 3목 대전 프로젝트입니다.

참가자와 로봇은 말 3개씩을 사용합니다. 배치가 끝난 뒤에는 자기 말 하나를 원하는 빈칸으로 옮길 수 있습니다. 카메라가 보드 변화를 인식하고, 게임 엔진이 로봇의 다음 수를 정하며, RaccoonBot이 실제 말을 집어서 옮깁니다.

## 현재 상태

게임 규칙, 불완전 AI, 합성 영상 기반 보드 인식, 물리 행동 검증, 가상 로봇, 공식 `robomation.RaccoonBot` 어댑터, 부스 UI 데모까지 구현되어 있습니다. 데스크톱 자동 테스트 43개를 통과했습니다.

실제 Jetson·카메라·Mini Dongle+ 연결, 현장 색상 캘리브레이션, 25개 로봇 자세 teaching은 하드웨어 준비 후 진행합니다.

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
- [ ] 실제 카메라 기준 캘리브레이션 값 저장
- [ ] 실제 9칸/3개 대기 위치 자세 teaching
- [ ] Jetson ARM64 + Mini Dongle+ 통신 확인
- [x] 하드웨어 없는 부스용 전체 화면 UI 데모
- [ ] 실제 카메라/로봇과 부스 UI 연결
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
