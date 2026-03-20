# main.py
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from agent import run_agent
from file_handler import process_files
from tripletex_api import TripletexClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Accounting Agent")

API_KEY = os.getenv("API_KEY")


@app.get("/health")
def health():
    return {"status": "ok"}


def _preconfigure_bank_account(base_url: str, session_token: str) -> None:
    """Ensure ledger account 1920 has a bank account configured."""
    client = TripletexClient(base_url, session_token)
    try:
        result = client.get("/ledger/account", params={"number": "1920", "fields": "id,number,bankAccountNumber"})
        if not result["success"]:
            return

        accounts = result["body"].get("values", [])
        if not accounts:
            return

        account = accounts[0]
        if not account.get("bankAccountNumber"):
            client.put(f"/ledger/account/{account['id']}", body={
                "id": account["id"],
                "number": 1920,
                "bankAccountNumber": "86010517941",
            })
            logger.info("Pre-configured bank account on ledger 1920")
    except Exception as e:
        logger.warning(f"Bank pre-config failed (non-fatal): {e}")


@app.post("/solve")
async def solve(request: Request):
    if API_KEY:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()

    # Handle both payload formats (official + competitor-observed)
    prompt = body.get("prompt") or body.get("task_prompt", "")
    files = body.get("files") or body.get("attached_files", [])
    creds = body.get("tripletex_credentials", {})
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")

    logger.info(f"Task received. Prompt: {len(prompt)} chars, Files: {len(files)}")

    try:
        file_contents = process_files(files)
        _preconfigure_bank_account(base_url, session_token)
        result = run_agent(prompt, file_contents, base_url, session_token)
        logger.info(f"Agent: {result}")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    return JSONResponse({"status": "completed"})
