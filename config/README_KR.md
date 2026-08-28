# 설정 파일

이 디렉터리에는 저장소에 공유할 템플릿만 둡니다. 실제 카메라와 로봇에서 얻은 값은 장비 배치마다 달라집니다.

## 로봇 자세

`home`은 제조사 기본 홈 자세가 아니라, 매 동작 전후에 머무르면서 카메라의
3×3 보드 시야를 가리지 않는 **관찰 대기 자세**로 teaching합니다. `home_high`는
높은 `transit`에서 관찰 `home`으로 안전하게 내려가기 전에 거치는 카메라 쪽
높은 자세입니다. `transit`은 관찰 쪽과 각 hover 자세 사이를 안전하게 연결하고,
집은 말을 다른 말보다 높게 들어 올리는 접힌 중간 이동 자세입니다.

실제 운반 동선은 다음 순서를 사용합니다.

```text
home → home_high → transit → source_hover → source_grasp → source_hover
     → transit(말을 든 상태) → target_hover → target_grasp → target_hover
     → transit → home_high → home
```

출발 hover에서 목표 hover로 직접 횡이동하지 않습니다. 카메라·보드·로봇의
상대 위치가 바뀌면 기존 teaching 값을 재사용하지 말고 전체 경로를 다시
검증합니다.

현재 확인한 공식 패키지/펌웨어 조합에서는 새 `RaccoonBot` 연결을 열 때 J1이
0도 쪽으로 초기화될 수 있습니다. 따라서 연결 직후에는 보드를 읽지 않고 반드시
`transit → home_high → home` 관찰 진입 경로를 완료한 뒤 카메라를 사용합니다.

일반 게임 이동은 공식 `set_angle_joints(..., wait=True)`에 목표 자세를 전달하는
`direct` 모드를 기본으로 사용합니다. 작은 각도 보간 방식은 문제 진단용
`interpolated` 모드로만 남겨둡니다. 두 모드 모두 이동 뒤 엔코더 도달 오차를
검증합니다. 최대 관절 오차가 3도를 넘으면 같은 목표를 최대 2번 재전송하며,
총 3회 모두 실패한 경우에만 그리퍼 동작 전에 게임을 중단합니다. 실패와 복구
로그에는 목표·실제 관절값과 관절별 오차가 기록됩니다.

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

저장된 hover까지 게임과 같은 빠른 직접 이동을 사용하려면 다음 옵션을 추가합니다.
보드와 이동 경로를 비운 뒤에만 사용합니다.

```bash
raccoonbot-teach-pose cell_1_grasp --start-from cell_1_hover \
  --start-speed 30 --start-motion-mode direct --confirm-manual-teaching
```

자동 이동 중에는 로봇에 손을 대지 말고, 모터 해제 안내가 나온 뒤에만 팔을 받칩니다.

각 자세는 `config/robot_poses.json`에 즉시 저장되므로 중간에 종료해도 이전 값이 남습니다. 27개 자세 이름은 `robot_poses.template.json`을 따릅니다.

시험용으로 저장했지만 다시 teaching해야 하는 값은 `_provisional_poses`에 기록합니다. 이 목록이 비어 있지 않으면 자세 검증과 실제 프로파일 로드를 실패시켜 임시값으로 로봇을 운전하지 못하게 합니다. 해당 자세를 다시 저장하면 목록에서 자동 제거됩니다.

3. 다음 명령으로 누락 및 관절 범위를 확인합니다.

```bash
raccoonbot-validate-poses config/robot_poses.json
```

`robot_poses.json`은 `.gitignore`에 포함되어 있습니다. 검증되지 않은 각도를 예제로 공유하지 마세요.

4. 모든 셀의 hover/grasp와 높은 운반 경로를 말 하나로 확인합니다. 1번에 말 하나를
놓고 나머지 칸을 비운 뒤 실행합니다. 카메라는 사용하지 않습니다.

```bash
raccoonbot-smoke-cell-sweep config/robot_poses.json --confirm-motion
```

말을 `1→2→3→4→5→6→7→8→9` 순서로 옮긴 뒤 `home_high → home`으로
복귀합니다. 전 구간을 운영자가 눈으로 확인합니다.

## 카메라 캘리브레이션

Jetson에서 카메라 프레임을 저장한 뒤 다음 명령으로 생성합니다.

```bash
raccoonbot-calibrate frame.png config/vision.json
```

`vision.json`에는 카메라 해상도, 보드 네 모서리, 방향, 빨강/노랑 HSV 범위가 들어갑니다. 이 파일도 설치 위치마다 다시 만들어야 하므로 `.gitignore`에 포함되어 있습니다.
