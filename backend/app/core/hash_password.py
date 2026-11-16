"""Print a bcrypt hash for HR_ADMIN_PASSWORD_HASH: `python -m app.core.hash_password`.

The password is read without echoing it and is never stored or logged.
"""

import getpass
import secrets

from app.core.security import hash_password


def main() -> None:
    password = getpass.getpass("HR password: ")
    if password != getpass.getpass("Repeat it: "):
        raise SystemExit("The passwords don't match.")
    print(f"HR_ADMIN_PASSWORD_HASH={hash_password(password)}")
    print(f"SESSION_SECRET={secrets.token_urlsafe(48)}  # a fresh random secret, if you need one")


if __name__ == "__main__":
    main()
