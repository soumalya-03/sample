from backend.app.services.auth_service import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_verifies_without_storing_plaintext():
    stored = hash_password("correct-horse-battery")

    assert stored != "correct-horse-battery"
    assert verify_password("correct-horse-battery", stored)
    assert not verify_password("incorrect-password", stored)


def test_access_token_is_signed_and_contains_user_scope():
    token = create_access_token(42, "alex@example.com", "operations")
    claims = decode_access_token(token)

    assert claims is not None
    assert claims["sub"] == 42
    assert claims["email"] == "alex@example.com"
    assert claims["role"] == "operations"
    assert decode_access_token(f"{token}tampered") is None