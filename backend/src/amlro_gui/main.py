import threading
import webbrowser

from amlro_gui.app import create_app

app = create_app()


def run_app() -> None:
    """Run Flask app."""
    app.run(host="127.0.0.1", port=5000, debug=False)


def launch() -> None:
    """Open browser + start Flask."""
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    run_app()


def main() -> None:
    """Entry point for the `amlro-gui` console script."""
    launch()


if __name__ == "__main__":
    main()
