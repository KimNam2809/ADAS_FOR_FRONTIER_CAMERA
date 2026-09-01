from roadwatch.auth import TokenManager, hash_password, verify_password


def test_password_hash_roundtrip() -> None:
    encoded = hash_password("driver123")
    assert encoded != "driver123"
    assert verify_password("driver123", encoded)
    assert not verify_password("wrong-password", encoded)


def test_signed_token_roundtrip() -> None:
    manager = TokenManager(ttl_minutes=5)
    token = manager.issue("engineer", "engineer")
    payload = manager.verify(token)
    assert payload["sub"] == "engineer"
    assert payload["role"] == "engineer"


def test_tampered_token_is_rejected() -> None:
    manager = TokenManager(ttl_minutes=5)
    token = manager.issue("driver", "driver")
    body, signature = token.split(".")
    try:
        manager.verify(f"{body}.{signature[:-1]}x")
    except ValueError:
        pass
    else:
        raise AssertionError("Token bị sửa phải bị từ chối")

