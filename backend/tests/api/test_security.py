from app.core.security import credentials_match, hash_password


def test_hashed_password_verifies_and_the_plain_text_is_not_kept() -> None:
    hashed = hash_password("a long passphrase")

    assert hashed.startswith("$2")
    assert "a long passphrase" not in hashed
    assert credentials_match("hr@acme.example", "a long passphrase", "hr@acme.example", hashed)
    assert not credentials_match("hr@acme.example", "wrong", "hr@acme.example", hashed)
