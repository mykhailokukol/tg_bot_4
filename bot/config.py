from os import getenv

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())


class Settings:
    TG_TOKEN: str = getenv("TG_TOKEN")
    MONGODB_CLIENT_URL: str = getenv("MONGODB_CLIENT_URL")
    # MODERATOR_ID: int = getenv("MODERATOR_ID_MISHA")
    MODERATOR_ID: int = getenv("MODERATOR_ID")
    STATEMENT: str = "pre-release"


settings = Settings()
