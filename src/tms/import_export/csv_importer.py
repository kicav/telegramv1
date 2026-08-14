import csv
from pathlib import Path
from ..members.models import Member
from .column_mapper import map_headers


def import_csv(path: Path) -> list[Member]:
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f); headers=next(reader); mapping=map_headers(headers); out=[]
        for row in reader:
            data={field:(row[i] if i < len(row) else '') for i,field in mapping.items()}
            raw_id=data.get('telegram_user_id') or None
            try: uid=int(raw_id) if raw_id else None
            except ValueError: uid=None
            out.append(Member(uid,data.get('username') or None,data.get('first_name') or None,data.get('last_name') or None,data.get('phone') or None,
                              str(data.get('bot','')).lower() in {'1','true','yes'},str(data.get('deleted','')).lower() in {'1','true','yes'},data.get('activity_status') or None,data.get('last_seen') or None))
        return out
