import csv
from pathlib import Path

FIELDS=['telegram_user_id','username','first_name','last_name','phone','bot','deleted','activity_status','last_seen']

def export_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader()
        for row in rows: w.writerow({k:row.get(k) for k in FIELDS})
