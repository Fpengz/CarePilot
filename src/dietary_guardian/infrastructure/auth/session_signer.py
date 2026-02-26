from itsdangerous import BadSignature, URLSafeSerializer


class SessionSigner:
    def __init__(self, secret: str) -> None:
        self._serializer = URLSafeSerializer(secret, salt="dietary-guardian-session")

    def sign(self, session_id: str) -> str:
        return self._serializer.dumps({"sid": session_id})

    def unsign(self, token: str) -> str | None:
        try:
            data = self._serializer.loads(token)
        except BadSignature:
            return None
        return str(data.get("sid")) if isinstance(data, dict) else None

