# 이미지와 출력물

## README 시연 미디어

메인 `README.md`는 다음 두 경로를 사용합니다.

| 용도 | 넣을 파일 |
|---|---|
| Google Drive 영상 클릭용 썸네일 | `assets/demo-thumbnail.jpg` |
| 운영 웹 UI 사진 | `assets/web-ui.png` |

영상 썸네일은 JPG, 웹 UI 사진은 PNG로 저장하고 파일명을 정확히 맞춥니다.
GitHub에 push한 뒤 README에서 두 이미지가 표시되는지 확인합니다.

영상 자체는 저장소에 올리지 않습니다. Google Drive에 영상을 올린 뒤 메인
`README.md`의 시연 섹션에서 아래 부분의 주소만 교체합니다.

```html
<a href="GOOGLE_DRIVE_VIDEO_URL">
```

공개 README에서 열 수 있도록 시크릿 브라우저나 로그아웃 상태에서도 영상 링크가
열리는지 확인합니다.

## A4 임시 출력물

- `temporary_board_a4.svg`: 3×3 흑백 보드와 로봇 말 대기 위치
- `temporary_tokens_a4.svg`: 빨강 3개, 노랑 3개의 임시 색 인식용 말

두 파일 모두 A4 용지에 **실제 크기/100%**로 인쇄합니다. 인쇄 후 50mm 확인선을
자로 재서 축소되지 않았는지 확인합니다.

종이 말은 비전과 게임 흐름 확인용입니다. 로봇 집기 시험에는 실제 말과 비슷한
높이·지름의 단단한 물체가 필요합니다. 최종 grasp 높이는 행사에 사용할 실제 말로
다시 teaching합니다.
