"""
Clara AI Pipeline – Configuration & Constants
"""
import os, pathlib, logging
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────
ROOT_DIR   = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / os.getenv("OUTPUT_DIR", "outputs")
DATASET_DIR = ROOT_DIR / os.getenv("DATASET_DIR", "dataset")
ACCOUNTS_DIR = OUTPUT_DIR / "accounts"

# ── LLM ───────────────────────────────────────────────────────────────
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL     = "llama-3.3-70b-versatile"   # free on Groq
GROQ_FALLBACK  = "llama-3.1-8b-instant"      # lighter fallback

# ── Retell ────────────────────────────────────────────────────────────
RETELL_API_KEY = os.getenv("RETELL_API_KEY", "")

# ── Task tracker ──────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "")

# ── Logging ───────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s │ %(name)-18s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clara")
