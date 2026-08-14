CANONICAL = {
    'user_id':'telegram_user_id','telegram_user_id':'telegram_user_id','id':'telegram_user_id',
    'username':'username','first_name':'first_name','last_name':'last_name','phone':'phone',
    'bot':'bot','deleted':'deleted','status':'activity_status','activity_status':'activity_status','last_seen':'last_seen',
}

def map_headers(headers: list[str]) -> dict[int,str]:
    out={}
    for i,h in enumerate(headers):
        key=str(h or '').strip().lower()
        if key in CANONICAL: out[i]=CANONICAL[key]
    return out
