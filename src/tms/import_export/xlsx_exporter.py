from pathlib import Path
from openpyxl import Workbook
from .csv_exporter import FIELDS


def export_xlsx(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    wb=Workbook(write_only=True); ws=wb.create_sheet('Members'); ws.append(FIELDS)
    for row in rows: ws.append([row.get(k) for k in FIELDS])
    wb.save(path)
