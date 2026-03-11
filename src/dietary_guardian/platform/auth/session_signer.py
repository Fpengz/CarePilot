"""Infrastructure support for session signer."""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer


class SessionSigner:
    def __init__(self, secret: str) -> None:
        self._serializer = URLSafeTimedSerializer(secret, salt="dietary-guardian-session")

    def sign(self, session_id: str) -> str:
        return self._serializer.dumps({"sid": session_id})

    def unsign(self, token: str, *, max_age_seconds: int) -> str | None:
        try:
            data = self._serializer.loads(token, max_age=max_age_seconds)
        except (BadSignature, SignatureExpired):
            return None
        return str(data.get("sid")) if isinstance(data, dict) else None
