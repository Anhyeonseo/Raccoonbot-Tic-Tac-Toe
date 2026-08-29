# RaccoonBot Vision Tic-Tac-Toe

[![tests](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml/badge.svg)](https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row/actions/workflows/tests.yml)

Jetson Orin Nano, RGB 카메라와 4축 RaccoonBot으로 만든 **3개 말 이동형
3목 체험 시스템**입니다. 참가자의 수를 카메라로 읽고, 완벽하지 않게 설계한 AI가
다음 수를 고르면 로봇팔이 말을 직접 집어 옮깁니다.

게임·비전·로봇 제어는 모두 Jetson에서 실행되며, 운영자는 노트북 브라우저에서
SSH 터널로 연결된 UI만 사용합니다. 인터넷이 없는 행사장에서도 USB-C 직결
네트워크로 운영할 수 있습니다.

## 시연

<p align="center">
  <a href="https://drive.google.com/file/d/1d0tjxeQ3BWgaXYCpIjII7FlVT4bhdUxd/view?usp=drive_link">
    <img src="assets/demo-thumbnail.jpg" width="420" alt="RaccoonBot 3말 잇기 시연 영상 썸네일">
  </a>
</p>

<p align="center"><strong>이미지를 클릭하면 Google Drive 시연 영상이 열립니다.</strong></p>

<p align="center">
  <img src="assets/web-ui.png" width="720" alt="RaccoonBot 3말 잇기 운영 웹 UI">
</p>

미디어 파일 위치와 영상 링크 교체 방법은
[assets/README_KR.md](assets/README_KR.md)를 참고하세요.

## 주요 기능

- 흑백 3×3 보드 원근 보정과 빨강·노랑 말 인식
- 사람의 배치·이동 검증과 로봇 동작 결과 재확인
- 배치 후 원하는 빈칸으로 말을 옮기는 3말 잇기 규칙
- 어린이 체험용 쉬움 AI와 보통 AI
- 9개 셀·3개 대기 위치의 pick-and-place와 높은 안전 경로
- 브라우저 게임 운영, 오류 복구와 현장 재캘리브레이션

실물 보드 게임과 `1→2→…→9` 연속 운반 시험을 완료했으며, 자세 도달 실패 시
같은 명령을 최대 2회 재전송합니다. 검증 환경은 Jetson Orin Nano Developer Kit,
JetPack 7.2.1, Trust QHD Webcam과 Mini Dongle+입니다.

## 게임 규칙

사람은 빨강 말 3개로 선공하고 라쿤봇은 노랑 말 3개를 사용합니다. 양쪽 말이 모두
배치된 뒤에는 자기 말 하나를 원하는 빈칸으로 옮깁니다. 먼저 가로·세로·대각선
3목을 만들면 승리하며, 반복 상태나 이동 수 제한에 도달하면 무승부입니다.

```text
1 | 2 | 3
--+---+--
4 | 5 | 6
--+---+--
7 | 8 | 9
```

## 빠른 시작

데스크톱에서 시뮬레이션과 자동 테스트를 실행합니다.

```bash
git clone https://github.com/Anhyeonseo/Raccoonbot-Vision-Three-in-a-row.git
cd Raccoonbot-Vision-Three-in-a-row
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-desktop.txt
python -m pytest -q
raccoonbot-booth --windowed
```

Jetson과 장비별 설정을 준비한 뒤 운영 노트북에서 UI를 실행합니다.

```bash
RACCOONBOT_SSH_IDENTITY=/path/to/private-key \
bash scripts/run_booth_ui.sh
```

브라우저에서 <http://127.0.0.1:8080>을 엽니다. 기본 접속 대상은 USB-C 장치망의
`hyper@192.168.55.1`이며 주소·사용자·프로젝트 경로는 환경변수로 바꿀 수 있습니다.

## 문서

| 문서 | 내용 |
|---|---|
| [설치 및 장비 준비](docs/INSTALLATION_KR.md) | 데스크톱·Jetson 설치, SSH, 카메라와 로봇 연결 |
| [부스 운영 안내](docs/OPERATIONS_KR.md) | 게임 진행, 복구, 현장 캘리브레이션과 안전 |
| [기술 설계](docs/TECHNICAL_KR.md) | 규칙, 구조, 비전·로봇 설계와 검증 상태 |
| [장비별 설정](config/README_KR.md) | 로봇 자세 teaching과 비전 설정 파일 |
| [3D 모델](models/scaledown_inst.md) | 보드·말·카메라 거치대 모델 안내 |

RaccoonBot 사용법과 주의사항은
[공식 사용자 가이드](https://github.com/RobomationLAB/RaccoonBot_Guide_KR)와
[Python API 매뉴얼](https://github.com/roboid-python/RaccoonBot_API_KR)을 함께
확인하세요.

## 안전

로봇이 움직일 때 작업 영역에 손을 넣지 마세요. UI의 `게임 중단`은 현재 관절
이동이 끝난 뒤 멈추는 기능이며 물리 비상정지가 아닙니다. 충돌이나 사람 접근에는
현장 전원 차단 절차를 사용해야 합니다.

## 라이선스

이 프로젝트는 [MIT License](LICENSE)로 배포합니다. RaccoonBot 하드웨어,
공식 가이드와 `robomation` 패키지는 각 권리자의 별도 조건을 따릅니다.
