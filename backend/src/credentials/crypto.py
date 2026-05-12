import os
import json
from cryptography.fernet import Fernet

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("ENCRYPTION_KEY")
        if not key:
            raise RuntimeError("ENCRYPTION_KEY env var is required")
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_json(data: dict) -> str:
    return _get_fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(ciphertext: str) -> dict:
    return json.loads(_get_fernet().decrypt(ciphertext.encode()).decode())
