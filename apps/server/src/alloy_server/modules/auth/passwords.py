from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool

_hasher = PasswordHash.recommended()

# Verified against when the email is unknown, so both failures take about as long.
_DUMMY_HASH = _hasher.hash("not a real password")


async def hash_password(password: str) -> str:
    return await run_in_threadpool(_hasher.hash, password)


async def verify_password(password: str, password_hash: str | None) -> bool:
    return await run_in_threadpool(_hasher.verify, password, password_hash or _DUMMY_HASH)
