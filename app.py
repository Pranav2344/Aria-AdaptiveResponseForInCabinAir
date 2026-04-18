from __future__ import annotations

import argparse

from gui import launch_desktop_gui
from web_app import run_web_server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ARIA: Adaptive Response for In-Cabin Air"
    )
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Launch the desktop Tkinter dashboard instead of the web dashboard.",
    )
    parser.add_argument("--host", type=str, default=None, help="Host for the web server.")
    parser.add_argument("--port", type=int, default=None, help="Port for the web server.")
    parser.add_argument("--debug", action="store_true", help="Run Flask in debug mode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.desktop:
        launch_desktop_gui()
        return

    run_web_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
