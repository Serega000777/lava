import pytest
from pydantic import ValidationError

from app.auth.permissions import has_permission
from app.auth.schemas import PasswordRegisterRequest
from app.auth.security import hash_password, hash_token, verify_password


def test_password_hash_is_not_plaintext() -> None:
    encoded = hash_password("Reliable123")
    assert encoded != "Reliable123"
    assert verify_password(encoded, "Reliable123")
    assert not verify_password(encoded, "Wrong123")


def test_session_hash_is_deterministic_and_not_plaintext() -> None:
    assert hash_token("secret") == hash_token("secret")
    assert hash_token("secret") != "secret"


def test_role_permissions_default_to_denied() -> None:
    assert has_permission("user", "profile:update")
    assert not has_permission("user", "moderation:decide")
    assert has_permission("admin", "anything")
    assert not has_permission("unknown", "profile:read")


def test_registration_rejects_weak_password() -> None:
    with pytest.raises(ValidationError):
        PasswordRegisterRequest(phone="+79990000000", display_name="Иван", password="onlyletters")

