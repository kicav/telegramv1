$ErrorActionPreference = "Stop"
python -m pip install -e ".[dev]"
python -m pytest -q
python -m nuitka --standalone --enable-plugin=pyside6 --windows-console-mode=disable --output-dir=dist --output-filename=TelegramMigrationStudio.exe src/tms/main.py
