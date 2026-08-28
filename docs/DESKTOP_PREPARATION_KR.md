# 데스크톱 개발 및 하드웨어 없는 검증

## 하드웨어 없이 가능한 범위

실제 카메라 영상, 실제 보드 치수, 실제 말 높이, Mini Dongle+가 없어도 아래 항목은 데스크톱에서 개발·검증할 수 있습니다.

- 3말 잇기 배치/이동/승리/무승부 규칙
- 일부러 완벽하지 않은 로봇 AI
- 카메라 관측 전후로 사람의 합법 행동 추론
- 흑백 3×3 판 원근 보정과 빨강/노랑 9칸 판독
- 여러 프레임이 일치할 때만 상태를 확정하는 안정화
- 사람 수 → AI → pick-and-place → 결과 재확인 통합 상태기
- 실제 로봇과 같은 명령 순서의 가상 로봇
- 공식 `robomation.RaccoonBot` API 어댑터
- A4 임시 보드/말과 합성 테스트 이미지
- 클릭 가능한 전체 화면 부스 UI 데모

## 데스크톱 실행

저장소 루트에서 가상환경을 만든 뒤 의존성을 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-desktop.txt
python -m pytest -q
```

대화형 게임은 다음과 같이 실행합니다. 빈칸에 표시되는 1~9가 카메라와 로봇 설정에서도 동일한 칸 번호입니다.

```bash
raccoonbot-sim
```

자동 종료/규칙 스트레스 테스트:

```bash
raccoonbot-sim --games 1000 --seed 2026
```

## 부스 화면 데모

카메라와 로봇 대신 마우스로 실제 규칙을 시험합니다.

```bash
raccoonbot-booth --windowed
```

`--windowed`를 빼면 전체 화면입니다. 배치 단계에서는 빈칸을 클릭하고, 이동 단계에서는 빨강 말 하나를 클릭한 뒤 원하는 빈칸을 클릭합니다. `Esc`는 전체 화면을 해제합니다. Tkinter가 없다면 `sudo apt install python3-tk`로 설치합니다.

## 카메라가 없어도 비전 파이프라인 시험하기

```bash
raccoonbot-synthetic work/synthetic --count 20 --seed 7
raccoonbot-inspect \
  work/synthetic/board_000.png \
  work/synthetic/board_000.calibration.json \
  --warped-output work/synthetic/board_000.warped.png
```

출력에서 `R`은 사람 빨강 말, `Y`는 로봇 노랑 말, `.`은 빈칸, `?`는 판정 불가입니다.

## 현장 캘리브레이션 도구 미리 연습하기

실제 설치 후 카메라 프레임 한 장을 저장했다면 다음 도구로 캘리브레이션을 만듭니다.

```bash
raccoonbot-calibrate frame.png config/vision.json
```

화면에서 순서대로 클릭합니다.

1. 보드 좌상단
2. 보드 우상단
3. 보드 우하단
4. 보드 좌하단
5. 빨강 말 중심
6. 노랑 말 중심
7. Enter로 저장

`R`은 클릭 초기화, `Esc` 또는 `Q`는 취소입니다. 방향이 90도씩 틀리면 `--rotation 1`, `2`, `3`을 사용합니다.

## 임시 보드와 말

`assets/temporary_board_a4.svg`와 `assets/temporary_tokens_a4.svg`를 A4 실제 크기 100%로 인쇄합니다. 인쇄 후 표시된 50 mm 선을 자로 확인합니다. 종이 말은 색상과 흐름 시험용이며 실제 로봇 grasp 높이 teaching에는 사용할 수 없습니다.

## 로봇 자세 파일

`config/robot_poses.template.json`에는 필요한 27개 자세 이름이 모두 있습니다.

- home 1개
- home_high 1개
- transit 1개
- 9칸 × hover/grasp = 18개
- 노랑 말 대기 위치 3개 × hover/grasp = 6개

실제 환경에서 4축 각도를 teaching한 뒤 `null`을 `[J1, J2, J3, J4]`로 교체하고 `config/robot_poses.json`으로 저장합니다. 검증 명령:

```bash
raccoonbot-validate-poses config/robot_poses.json
```

템플릿의 `null`은 의도적으로 실행 불가능합니다. 임의의 0도 값을 넣어 로봇을 움직이지 마세요.

## 실제 Jetson과 하드웨어가 필요한 범위

아래 항목은 데스크톱 모의 시험으로 대체할 수 없으며 실제 설치에서 수행합니다.

- JetPack 설치 및 Jetson 첫 부팅
- Jetson에서 `robomation` 패키지와 Mini Dongle+ 호환성 확인
- 실제 `/dev/video*`, `/dev/tty*` 장치 확인과 권한 설정
- 현장 조명 기준 노출/화이트밸런스/HSV 확정
- 실제 보드 네 모서리와 방향 저장
- 9칸/3개 stock의 실제 joint teaching
- 말의 지름·높이·마찰에 맞춘 grasp 높이와 그리퍼 대기시간 조정
- 충돌 없는 속도와 hover 높이 검증
- 사용자 UI 기반 최종 한 게임과 오류 복구 리허설

Jetson 부팅 후에는 `docs/JETSON_BRINGUP_KR.md`의 순서로 이어갑니다.

## 실제 장비 확인 결과

Jetson ARM64에서 Mini Dongle+ 직렬 장치와 공식 `robomation.RaccoonBot` 연결을
확인했습니다. 배터리·BLE·DC 그리퍼 조회, 직접 관절 이동, teaching, 1~9번 연속
운반과 실제 게임을 완료했습니다. 다른 JetPack 또는 공식 패키지 버전에서는 API와
장치 경로가 달라질 수 있으므로 `docs/JETSON_BRINGUP_KR.md`의 진단부터 반복합니다.
