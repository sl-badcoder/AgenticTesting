from src.app.security import FernetSecretBox, hash_password, verify_password


def test_password_hash_does_not_store_plain_text() -> None:
    encoded = hash_password("correct horse battery staple")

    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded) is True
    assert verify_password("wrong password", encoded) is False


def test_fernet_secret_box_encrypts_and_decrypts_value(tmp_path) -> None:
    secret_box = FernetSecretBox(tmp_path / "secret.key")

    encrypted = secret_box.encrypt("sk-test")

    assert encrypted != "sk-test"
    assert secret_box.decrypt(encrypted) == "sk-test"
    assert (tmp_path / "secret.key").exists()
