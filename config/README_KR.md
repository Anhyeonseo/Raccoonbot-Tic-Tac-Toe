# 설정 파일

이 디렉터리에는 저장소에 공유할 템플릿만 둡니다. 실제 카메라와 로봇에서 얻은 값은 장비 배치마다 달라집니다.

## 로봇 자세

1. `robot_poses.template.json`을 `robot_poses.json`으로 복사합니다.
2. 25개 자세의 `null`을 실제 `[J1, J2, J3, J4]` 각도로 교체합니다.
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
