import os

# Defaults so tests run without a `.env` (e.g. in CI). Unit tests never connect to it.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://base:base@localhost:5432/base_test")
os.environ.setdefault("APP_ENV", "test")
