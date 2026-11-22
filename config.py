
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Ollama local configuration
OLLAMA_BASE_URL = os.getenv(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2:1b"
)
