import os

class Config:
    SERVICE_NAME = "ingredients-service"
    PORT = int(os.getenv("PORT", 5002))
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")

    # Database configuration
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ingredients_db")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Inter-service communication
    RECIPES_SERVICE_URL = os.getenv("RECIPES_SERVICE_URL", "http://recipes-service:5001")
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 3))
