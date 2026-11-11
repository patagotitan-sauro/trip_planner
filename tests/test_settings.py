from django.conf import settings


def test_language_is_brazilian_portuguese():
    assert settings.LANGUAGE_CODE == "pt-br"


def test_timezone_is_sao_paulo_and_storage_is_utc():
    assert settings.TIME_ZONE == "America/Sao_Paulo"
    assert settings.USE_TZ is True


def test_sqlite_uses_wal_mode():
    assert "journal_mode=WAL" in settings.DATABASES["default"]["OPTIONS"]["init_command"]
