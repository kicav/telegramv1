import sys
from .bootstrap import bootstrap


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from .ui.main_window import MainWindow
    app=QApplication(sys.argv);ctx=bootstrap();ctx.runtime.start();win=MainWindow(ctx);win.show()
    app.aboutToQuit.connect(ctx.runtime.stop)
    return app.exec()

if __name__ == '__main__': raise SystemExit(main())
