# 설정 파일

이 디렉터리에는 저장소에 공유할 템플릿만 둡니다. 실제 카메라와 로봇에서 얻은 값은 장비 배치마다 달라집니다.

## 로봇 자세

`home`은 제조사 기본 홈 자세가 아니라, 매 동작 전후에 머무르면서 카메라의
3×3 보드 시야를 가리지 않는 **관찰 대기 자세**로 teaching합니다. `transit`은
관찰 자세와 각 hover 자세 사이를 안전하게 연결하고, 집은 말을 다른 말보다
높게 들어 올리는 접힌 중간 이동 자세입니다.

실제 운반 동선은 다음 순서를 사용합니다.

```text
home → transit → source_hover → source_grasp → source_hover
     → transit(말을 든 상태) → target_hover → target_grasp
     → target_hover → transit → home
```

출발 hover에서 목표 hover로 직접 횡이동하지 않습니다. 카메라·보드·로봇의
상대 위치가 바뀌면 기존 teaching 값을 재사용하지 말고 전체 경로를 다시
검증합니다.

1. 현재 자세를 모터 해제 없이 저장하려면 다음처럼 실행합니다.

```bash
raccoonbot-teach-pose home --capture-current
```

2. 손으로 자세를 teaching할 때는 팔을 받친 상태에서 아래 명령을 실행하고, 자세를 맞춘 뒤 라쿤봇의 물리 Teach 버튼을 한 번 누릅니다.

```bash
raccoonbot-teach-pose cell_1_hover --confirm-manual-teaching
```

grasp를 같은 관절 자세 계열에서 안전하게 teaching하려면 먼저 저장된 hover로 자동 이동한 뒤 모터를 해제합니다.

```bash
raccoonbot-teach-pose stock_1_grasp --start-from stock_1_hover \
  --confirm-manual-teaching
```

자동 이동 중에는 로봇에 손을 대지 말고, 모터 해제 안내가 나온 뒤에만 팔을 받칩니다.

각 자세는 `config/robot_poses.json`에 즉시 저장되므로 중간에 종료해도 이전 값이 남습니다. 26개 자세 이름은 `robot_poses.template.json`을 따릅니다.

시험용으로 저장했지만 다시 teaching해야 하는 값은 `_provisional_poses`에 기록합니다. 이 목록이 비어 있지 않으면 자세 검증과 실제 프로파일 로드를 실패시켜 임시값으로 로봇을 운전하지 못하게 합니다. 해당 자세를 다시 저장하면 목록에서 자동 제거됩니다.

3. 다음 명령으로 누락 및 관절 범위를 확인합니다.

```bash
raccoonbot-validate-poses config/robot_poses.json
```

`robot_poses.json`은 `.gitignore`에 포함되어 있습니다. 검증되지 않은 각도를 예제로 공유하지 마세요.

## 카메라 캘리브레이션

Jetson에서 카메라 프레임을 저장한 뒤 다음 명령으로 생성합니다.

```bash
raccoonbot-calibrate frame.png config/vision.json
```

`vision.json`에는 카메라 해상도, 보드 네 모서리, 방향, 빨강/노랑 HSV 범위가 들어갑니다. 이 파일도 설치 위치마다 다시 만들어야 하므로 `.gitignore`에 포함되어 있습니다.
