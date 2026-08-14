from .client_manager import ClientManager


class AuthService:
    def __init__(self, clients: ClientManager, session_lookup: callable) -> None:
        self.clients=clients
        self.session_lookup=session_lookup

    async def send_code(self, account_id: int, phone: str) -> str:
        client=await self.clients.get(account_id, self.session_lookup(account_id))
        sent=await client.send_code_request(phone)
        return sent.phone_code_hash

    async def sign_in(self, account_id: int, phone: str, code: str, phone_code_hash: str, password: str | None = None) -> None:
        client=await self.clients.get(account_id, self.session_lookup(account_id))
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        except Exception as exc:
            if "SessionPasswordNeeded" not in type(exc).__name__ or password is None:
                raise
            await client.sign_in(password=password)
