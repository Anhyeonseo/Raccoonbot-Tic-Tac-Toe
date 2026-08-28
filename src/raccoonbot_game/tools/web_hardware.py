from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from raccoonbot_game.app.web_calibration import WebCalibrationController
from raccoonbot_game.app.web_controller import WebGameController
from raccoonbot_game.calibration import VisionCalibration
from raccoonbot_game.strategy import AiPolicy
from raccoonbot_game.tools.live_board import _open_camera
from raccoonbot_game.tools.play_hardware import run_game
from raccoonbot_game.tools.probe_robot import DEFAULT_PORT


WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}


AI_POLICIES = {
    "easy": AiPolicy(
        block_probability=0.4,
        best_move_probability=0.35,
        second_best_probability=0.25,
    ),
    "normal": AiPolicy(),
}


def request_path(raw_path: str) -> str:
    """Return the routing path while allowing cache-busting query strings."""

    return urlsplit(raw_path).path


def build_handler(
    controller: WebGameController,
    calibration_controller: WebCalibrationController,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = request_path(self.path)
            if path == "/api/state":
                self._send_json(controller.snapshot())
                return
            if path == "/api/calibration/state":
                self._send_json(calibration_controller.snapshot())
                return
            if path == "/api/calibration/frame.jpg":
                self._send_image(calibration_controller.image())
                return
            if path == "/api/calibration/preview.jpg":
                self._send_image(calibration_controller.image(preview=True))
                return
            static = STATIC_FILES.get(path)
            if static is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            filename, content_type = static
            content = (WEB_ROOT / filename).read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:
            try:
                if self.path == "/api/start":
                    accepted = not calibration_controller.busy and controller.start()
                    self._send_accepted(accepted)
                    return
                if self.path == "/api/submit":
                    self._send_accepted(controller.submit())
                    return
                if self.path == "/api/stop":
                    self._send_accepted(controller.request_stop())
                    return
                if self.path == "/api/reset":
                    self._send_accepted(controller.reset())
                    return
                if self.path.startswith("/api/calibration/"):
                    if controller.snapshot()["running"]:
                        self._send_json(
                            {"error": "게임 실행 중에는 캘리브레이션할 수 없습니다"},
                            status=HTTPStatus.CONFLICT,
                        )
                        return
                    if self.path == "/api/calibration/capture":
                        self._send_json(calibration_controller.capture())
                        return
                    if self.path == "/api/calibration/preview":
                        self._send_json(calibration_controller.preview(self._read_json()))
                        return
                    if self.path == "/api/calibration/save":
                        self._send_json(calibration_controller.save())
                        return
                self.send_error(HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            except RuntimeError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.CONFLICT)

        def _send_accepted(self, accepted: bool) -> None:
            status = HTTPStatus.ACCEPTED if accepted else HTTPStatus.CONFLICT
            self._send_json({"accepted": accepted}, status=status)

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ValueError("올바른 JSON 요청이 필요합니다") from exc
            if not isinstance(payload, dict):
                raise ValueError("JSON 객체가 필요합니다")
            return payload

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _send_image(self, content: bytes | None) -> None:
            if content is None:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="노트북 브라우저용 RaccoonBot 실물 게임 UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--web-port", type=int, default=8080)
    parser.add_argument("--profile", type=Path, default=Path("config/robot_poses.json"))
    parser.add_argument("--calibration", type=Path, default=Path("config/vision.json"))
    parser.add_argument("--robot-port", default=DEFAULT_PORT)
    parser.add_argument("--device", type=int)
    parser.add_argument("--joint-step", type=float, default=6.0)
    parser.add_argument(
        "--motion-mode",
        choices=("interpolated", "direct"),
        default="direct",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="생략하면 게임마다 시스템 난수 사용; 재현 시험에만 고정값 지정",
    )
    parser.add_argument("--difficulty", choices=tuple(AI_POLICIES), default="easy")
    parser.add_argument("--capture-dir", type=Path, default=Path("work/game-captures"))
    parser.add_argument("--resume-placement", action="store_true")
    parser.add_argument("--confirm-hardware", action="store_true")
    args = parser.parse_args()
    if not args.confirm_hardware:
        parser.error("refusing hardware game server without --confirm-hardware")
    if not 1 <= args.joint_step <= 6:
        parser.error("--joint-step must be within 1..6 degrees")
    if not 1 <= args.web_port <= 65535:
        parser.error("--web-port must be within 1..65535")

    controller = WebGameController(
        run_game,
        {
            "profile_path": args.profile,
            "calibration_path": args.calibration,
            "port": args.robot_port,
            "device": args.device,
            "joint_step_degrees": args.joint_step,
            "motion_mode": args.motion_mode,
            "seed": args.seed,
            "ai_policy": AI_POLICIES[args.difficulty],
            "capture_dir": args.capture_dir,
            "resume_placement": args.resume_placement,
        },
        threaded=False,
        difficulty=args.difficulty,
    )
    calibration_controller = WebCalibrationController(
        args.calibration,
        lambda: _capture_calibration_frame(args.calibration, args.device),
    )
    server = ThreadingHTTPServer(
        (args.host, args.web_port),
        build_handler(controller, calibration_controller),
    )
    server_thread = threading.Thread(target=server.serve_forever, name="game-ui-http")
    server_thread.start()
    print(f"게임 UI 서버: http://{args.host}:{args.web_port}", flush=True)
    print("브라우저의 '새 게임' 버튼을 눌러 장비 게임을 시작하세요.", flush=True)
    try:
        while controller.run_pending():
            pass
    except KeyboardInterrupt:
        print("게임 서버 종료 요청. 로봇 정지와 연결 해제를 기다립니다.", flush=True)
    finally:
        controller.cancel()
        controller.join()
        server.shutdown()
        server.server_close()
        server_thread.join()


def _capture_calibration_frame(path: Path, device: int | None) -> Any:
    calibration = VisionCalibration.load(path)
    camera_device = calibration.camera.device if device is None else device
    capture = _open_camera(calibration, camera_device)
    try:
        frame = None
        for _ in range(30):
            ok, candidate = capture.read()
            if ok and candidate is not None:
                frame = candidate
        if frame is None:
            raise RuntimeError("카메라 프레임을 촬영하지 못했습니다")
        expected = (calibration.camera.height, calibration.camera.width)
        if frame.shape[:2] != expected:
            raise RuntimeError(
                f"카메라 해상도가 설정과 다릅니다: "
                f"{frame.shape[1]}x{frame.shape[0]} != {expected[1]}x{expected[0]}"
            )
        return frame
    finally:
        capture.release()


if __name__ == "__main__":
    main()
