from app.config import Settings


def test_neon_postgresql_url_uses_installed_psycopg3_driver() -> None:
    settings = Settings(
        database_url=(
            "postgresql://pet_detective:secret@"
            "ep-example-pooler.ap-northeast-1.aws.neon.tech/neondb"
            "?sslmode=require&channel_binding=require"
        ),
        openai_api_key=None,
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert "sslmode=require" in settings.database_url
    assert "channel_binding=require" in settings.database_url
