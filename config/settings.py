import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://handbook_library:{os.environ.get('HANDBOOK_LIBRARY_DB_PASSWORD', '')}@127.0.0.1:5442/handbook_library"
)

# Pluggable LLM provider for chat
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("LLM_MODEL", "auto")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "free")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "")

EMBEDDING_MODEL = "all-mpnet-base-v2"
EMBEDDING_DIMENSIONS = 768

CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
