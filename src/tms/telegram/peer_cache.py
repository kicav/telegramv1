from dataclasses import dataclass
from ..storage.database import Database


@dataclass(slots=True)
class CachedPeer:
    account_id: int
    peer_id: int
    peer_type: str
    access_hash: int | None
    username: str | None = None
    title: str | None = None


class PeerCache:
    def __init__(self, db: Database) -> None:
        self.db=db
        self._memory: dict[tuple[int,int], CachedPeer] = {}

    def put(self, peer: CachedPeer) -> None:
        self._memory[(peer.account_id,peer.peer_id)] = peer
        with self.db.connect() as conn:
            conn.execute(
                """INSERT INTO peer_cache(account_id,peer_id,peer_type,access_hash,username,title)
                VALUES(?,?,?,?,?,?) ON CONFLICT(account_id,peer_id) DO UPDATE SET
                peer_type=excluded.peer_type, access_hash=excluded.access_hash,
                username=excluded.username, title=excluded.title, cached_at=CURRENT_TIMESTAMP""",
                (peer.account_id,peer.peer_id,peer.peer_type,peer.access_hash,peer.username,peer.title),
            )
            conn.commit()

    def get(self, account_id: int, peer_id: int) -> CachedPeer | None:
        key=(account_id,peer_id)
        if key in self._memory:
            return self._memory[key]
        with self.db.reader() as conn:
            row=conn.execute("SELECT * FROM peer_cache WHERE account_id=? AND peer_id=?", key).fetchone()
        if not row:
            return None
        peer=CachedPeer(account_id,row['peer_id'],row['peer_type'],row['access_hash'],row['username'],row['title'])
        self._memory[key]=peer
        return peer
