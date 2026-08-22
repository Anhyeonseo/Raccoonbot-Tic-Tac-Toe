from __future__ import annotations

import argparse

from raccoonbot_game.app.demo_model import DemoGame
from raccoonbot_game.game import Player


def main() -> None:
    parser = argparse.ArgumentParser(description="RaccoonBot 3말 잇기 부스 UI 데모")
    parser.add_argument("--windowed", action="store_true", help="전체 화면 대신 창 모드")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    try:
        import tkinter as tk
    except ImportError as exc:
        raise SystemExit("Tkinter가 필요합니다: sudo apt install python3-tk") from exc

    model = DemoGame(seed=args.seed)
    root = tk.Tk()
    root.title("RaccoonBot 3말 잇기")
    root.configure(bg="#15191f")
    if not args.windowed:
        root.attributes("-fullscreen", True)
    root.bind("<Escape>", lambda _event: root.attributes("-fullscreen", False))

    title = tk.Label(
        root,
        text="라쿤봇 3말 잇기",
        font=("sans", 30, "bold"),
        fg="white",
        bg="#15191f",
    )
    title.pack(pady=(24, 8))
    status = tk.Label(
        root,
        text=model.message,
        font=("sans", 17),
        fg="#dce5ef",
        bg="#15191f",
        wraplength=760,
    )
    status.pack(pady=(0, 16))

    board_frame = tk.Frame(root, bg="#68717c", padx=4, pady=4)
    board_frame.pack(expand=True)
    buttons: list[tk.Button] = []

    def redraw() -> None:
        status.configure(text=model.message)
        for index, button in enumerate(buttons):
            occupant = model.game.board[index]
            row, column = divmod(index, 3)
            base = "#f0f0e8" if (row + column) % 2 == 0 else "#242424"
            if occupant is Player.HUMAN:
                text, foreground = "●", "#e32222"
            elif occupant is Player.ROBOT:
                text, foreground = "●", "#f1d225"
            else:
                text = str(index + 1)
                foreground = "#555" if base == "#f0f0e8" else "#bbb"
            relief = tk.SUNKEN if model.selected_source == index else tk.RAISED
            button.configure(text=text, fg=foreground, bg=base, activebackground=base, relief=relief)

    def click(index: int) -> None:
        model.click(index)
        redraw()

    for index in range(9):
        row, column = divmod(index, 3)
        button = tk.Button(
            board_frame,
            command=lambda value=index: click(value),
            font=("sans", 46, "bold"),
            width=4,
            height=2,
            borderwidth=2,
        )
        button.grid(row=row, column=column, padx=2, pady=2, sticky="nsew")
        buttons.append(button)

    controls = tk.Frame(root, bg="#15191f")
    controls.pack(pady=20)

    def reset() -> None:
        model.reset()
        redraw()

    tk.Button(controls, text="새 게임", command=reset, font=("sans", 16, "bold"), padx=24, pady=8).pack(side=tk.LEFT, padx=8)
    tk.Button(controls, text="종료", command=root.destroy, font=("sans", 16), padx=24, pady=8).pack(side=tk.LEFT, padx=8)
    redraw()
    root.mainloop()


if __name__ == "__main__":
    main()
