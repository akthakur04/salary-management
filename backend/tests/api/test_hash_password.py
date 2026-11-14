import bcrypt
import pytest

from app.core import hash_password


def test_command_prints_a_hash_of_the_password_and_a_fresh_secret(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "a long passphrase")
    monkeypatch.setattr(
        hash_password,
        "hash_password",
        lambda p: bcrypt.hashpw(p.encode(), bcrypt.gensalt(rounds=4)).decode(),
    )

    hash_password.main()

    hash_line, secret_line = capsys.readouterr().out.strip().splitlines()
    hashed = hash_line.removeprefix("HR_ADMIN_PASSWORD_HASH=")
    assert bcrypt.checkpw(b"a long passphrase", hashed.encode())
    assert secret_line.startswith("SESSION_SECRET=")
    assert "a long passphrase" not in capsys.readouterr().out


def test_command_stops_when_the_passwords_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["first", "second"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(answers))

    with pytest.raises(SystemExit):
        hash_password.main()
