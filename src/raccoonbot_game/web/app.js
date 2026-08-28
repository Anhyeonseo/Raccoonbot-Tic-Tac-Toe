const board = document.querySelector("#board");
const message = document.querySelector("#message");
const stage = document.querySelector("#stage");
const difficulty = document.querySelector("#difficulty");
const submit = document.querySelector("#submit");
const start = document.querySelector("#start");
const stop = document.querySelector("#stop");
const reset = document.querySelector("#reset");
const showGame = document.querySelector("#show-game");
const showCalibration = document.querySelector("#show-calibration");
const gameView = document.querySelector("#game-view");
const calibrationView = document.querySelector("#calibration-view");

const calibrationCapture = document.querySelector("#calibration-capture");
const calibrationClear = document.querySelector("#calibration-clear");
const calibrationPreviewButton = document.querySelector("#calibration-preview-button");
const calibrationSave = document.querySelector("#calibration-save");
const calibrationNext = document.querySelector("#calibration-next");
const calibrationMessage = document.querySelector("#calibration-message");
const calibrationCanvas = document.querySelector("#calibration-canvas");
const calibrationPlaceholder = document.querySelector("#calibration-placeholder");
const calibrationPreviewImage = document.querySelector("#calibration-preview-image");
const calibrationResult = document.querySelector("#calibration-result");
const calibrationContext = calibrationCanvas.getContext("2d");

const stageNames = {
  idle: "시작 대기",
  starting: "장비 준비",
  observing: "보드 확인",
  waiting_human: "내 차례",
  observing_human: "수 확인",
  robot_moving: "라쿤봇 차례",
  robot_verifying: "결과 확인",
  human_error: "다시 두기",
  stopping: "중단 중",
  finished: "게임 종료",
  stopped: "운영 중단",
  error: "확인 필요",
};

const calibrationLabels = ["좌상단(TL)", "우상단(TR)", "우하단(BR)", "좌하단(BL)", "빨간 말 중앙", "노란 말 중앙"];
let currentView = "game";
let lastGameState = null;
let calibrationImage = null;
let calibrationPoints = [];

function drawBoard(cells = []) {
  board.replaceChildren();
  for (let index = 0; index < 9; index += 1) {
    const cell = document.createElement("div");
    const row = Math.floor(index / 3);
    const column = index % 3;
    cell.className = `cell ${(row + column) % 2 ? "dark" : ""}`;
    const occupant = cells[index];
    if (occupant) {
      const piece = document.createElement("div");
      piece.className = `piece ${occupant}`;
      piece.setAttribute("aria-label", occupant === "human" ? "빨간 말" : "노란 말");
      cell.append(piece);
    } else {
      cell.textContent = String(index + 1);
    }
    board.append(cell);
  }
}

async function request(path, { method = "GET", body } = {}) {
  const options = { method, cache: "no-store", headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.error || `요청 실패 (${response.status})`);
  }
  return payload;
}

async function refresh() {
  try {
    const state = await request("/api/state");
    lastGameState = state;
    drawBoard(state.board);
    message.textContent = state.message;
    stage.textContent = stageNames[state.stage] ?? state.stage;
    difficulty.textContent = state.difficulty === "normal" ? "AI 보통" : "AI 쉬움";
    submit.textContent = state.submit_label;
    submit.disabled = !state.can_submit;
    start.disabled = !state.can_start;
    stop.disabled = !state.can_stop;
    reset.disabled = !state.can_reset;
    calibrationCapture.disabled = Boolean(state.running);
  } catch (_error) {
    stage.textContent = "연결 끊김";
    message.textContent = "Jetson 게임 서버와 연결을 확인해 주세요.";
    for (const button of [submit, start, stop, reset, calibrationCapture]) {
      button.disabled = true;
    }
  }
}

function setView(view) {
  currentView = view;
  const gameSelected = view === "game";
  gameView.classList.toggle("hidden", !gameSelected);
  calibrationView.classList.toggle("hidden", gameSelected);
  showGame.classList.toggle("active", gameSelected);
  showCalibration.classList.toggle("active", !gameSelected);
}

submit.addEventListener("click", async () => {
  submit.disabled = true;
  try {
    await request("/api/submit", { method: "POST" });
  } finally {
    await refresh();
  }
});

start.addEventListener("click", async () => {
  start.disabled = true;
  try {
    await request("/api/start", { method: "POST" });
  } finally {
    await refresh();
  }
});

stop.addEventListener("click", async () => {
  if (!window.confirm("게임을 중단할까요? 현재 관절 이동이 끝난 뒤 다음 명령 전에 멈춥니다.")) return;
  stop.disabled = true;
  try {
    await request("/api/stop", { method: "POST" });
  } finally {
    await refresh();
  }
});

reset.addEventListener("click", async () => {
  reset.disabled = true;
  try {
    await request("/api/reset", { method: "POST" });
  } finally {
    await refresh();
  }
});

showGame.addEventListener("click", () => setView("game"));
showCalibration.addEventListener("click", () => setView("calibration"));

document.addEventListener("keydown", (event) => {
  if (currentView === "game" && event.key === "Enter" && !event.repeat && !submit.disabled) {
    event.preventDefault();
    submit.click();
  }
});

function setCalibrationMessage(text, kind = "") {
  calibrationMessage.textContent = text;
  calibrationMessage.className = `calibration-message ${kind}`.trim();
}

function updateCalibrationControls() {
  const hasImage = Boolean(calibrationImage);
  const complete = calibrationPoints.length === calibrationLabels.length;
  calibrationClear.disabled = !hasImage || calibrationPoints.length === 0;
  calibrationPreviewButton.disabled = !complete;
  if (!hasImage) {
    calibrationNext.textContent = "사진을 먼저 촬영하세요.";
  } else if (!complete) {
    calibrationNext.textContent = `${calibrationPoints.length + 1}/6 · ${calibrationLabels[calibrationPoints.length]}`;
  } else {
    calibrationNext.textContent = "6/6 완료 · 미리보기를 생성하세요.";
  }
}

function drawCalibrationCanvas() {
  if (!calibrationImage) return;
  calibrationContext.clearRect(0, 0, calibrationCanvas.width, calibrationCanvas.height);
  calibrationContext.drawImage(calibrationImage, 0, 0);
  calibrationContext.lineWidth = Math.max(3, calibrationCanvas.width / 480);
  calibrationContext.font = `bold ${Math.max(20, calibrationCanvas.width / 55)}px sans-serif`;

  if (calibrationPoints.length >= 2) {
    calibrationContext.strokeStyle = "#45ff7a";
    calibrationContext.beginPath();
    calibrationContext.moveTo(calibrationPoints[0][0], calibrationPoints[0][1]);
    for (let index = 1; index < Math.min(4, calibrationPoints.length); index += 1) {
      calibrationContext.lineTo(calibrationPoints[index][0], calibrationPoints[index][1]);
    }
    if (calibrationPoints.length >= 4) calibrationContext.closePath();
    calibrationContext.stroke();
  }

  calibrationPoints.forEach(([x, y], index) => {
    calibrationContext.fillStyle = index === 4 ? "#ed2d38" : index === 5 ? "#f1d225" : "#45ff7a";
    calibrationContext.beginPath();
    calibrationContext.arc(x, y, Math.max(8, calibrationCanvas.width / 130), 0, Math.PI * 2);
    calibrationContext.fill();
    calibrationContext.fillStyle = "#ffffff";
    calibrationContext.fillText(calibrationLabels[index], x + 14, y - 14);
  });
}

calibrationCapture.addEventListener("click", async () => {
  calibrationCapture.disabled = true;
  calibrationSave.disabled = true;
  calibrationPreviewImage.classList.remove("ready");
  setCalibrationMessage("카메라 사진을 촬영하고 있습니다…");
  try {
    const result = await request("/api/calibration/capture", { method: "POST" });
    const image = new Image();
    image.onload = () => {
      calibrationImage = image;
      calibrationPoints = [];
      calibrationCanvas.width = result.width;
      calibrationCanvas.height = result.height;
      calibrationPlaceholder.classList.add("hidden");
      drawCalibrationCanvas();
      updateCalibrationControls();
      setCalibrationMessage("사진 촬영 완료. 안내 순서대로 여섯 점을 클릭하세요.", "success");
    };
    image.onerror = () => setCalibrationMessage("촬영 이미지를 불러오지 못했습니다.", "error");
    image.src = `/api/calibration/frame.jpg?t=${Date.now()}`;
  } catch (error) {
    setCalibrationMessage(error.message, "error");
  } finally {
    calibrationCapture.disabled = Boolean(lastGameState?.running);
  }
});

calibrationCanvas.addEventListener("click", (event) => {
  if (!calibrationImage || calibrationPoints.length >= calibrationLabels.length) return;
  const bounds = calibrationCanvas.getBoundingClientRect();
  const x = (event.clientX - bounds.left) * calibrationCanvas.width / bounds.width;
  const y = (event.clientY - bounds.top) * calibrationCanvas.height / bounds.height;
  calibrationPoints.push([Math.round(x), Math.round(y)]);
  calibrationSave.disabled = true;
  calibrationPreviewImage.classList.remove("ready");
  drawCalibrationCanvas();
  updateCalibrationControls();
});

calibrationClear.addEventListener("click", () => {
  calibrationPoints = [];
  calibrationSave.disabled = true;
  calibrationPreviewImage.classList.remove("ready");
  calibrationResult.textContent = "여섯 점을 선택한 뒤 미리보기를 생성하세요.";
  drawCalibrationCanvas();
  updateCalibrationControls();
  setCalibrationMessage("점 선택을 초기화했습니다.");
});

calibrationPreviewButton.addEventListener("click", async () => {
  calibrationPreviewButton.disabled = true;
  calibrationSave.disabled = true;
  setCalibrationMessage("워프와 색상 판정을 계산하고 있습니다…");
  try {
    const result = await request("/api/calibration/preview", {
      method: "POST",
      body: { points: calibrationPoints },
    });
    calibrationPreviewImage.src = `/api/calibration/preview.jpg?t=${Date.now()}`;
    calibrationPreviewImage.classList.add("ready");
    const summary = result.cells.map((cell) => `${cell.cell}:${cell.label}`).join(" · ");
    calibrationResult.textContent = summary;
    calibrationSave.disabled = false;
    setCalibrationMessage("미리보기 완료. 격자와 9칸 판정이 맞을 때만 저장하세요.", "success");
  } catch (error) {
    setCalibrationMessage(error.message, "error");
  } finally {
    calibrationPreviewButton.disabled = calibrationPoints.length !== calibrationLabels.length;
  }
});

calibrationSave.addEventListener("click", async () => {
  if (!window.confirm("현재 미리보기 값으로 vision.json을 교체할까요? 기존 파일은 자동 백업됩니다.")) return;
  calibrationSave.disabled = true;
  try {
    const result = await request("/api/calibration/save", { method: "POST" });
    setCalibrationMessage(`저장 완료 · 백업: ${result.backup || "없음"}`, "success");
  } catch (error) {
    calibrationSave.disabled = false;
    setCalibrationMessage(error.message, "error");
  }
});

drawBoard();
setView("game");
updateCalibrationControls();
refresh();
setInterval(refresh, 350);
