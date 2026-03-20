# main.py
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

import hashlib

from agent import run_agent
from file_handler import process_files
from observability import traceable
from tripletex_api import TripletexClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Accounting Agent")

API_KEY = os.getenv("API_KEY")
REQUEST_LOG_BUCKET = os.getenv("REQUEST_LOG_BUCKET", "")


def _save_request_to_gcs(body: dict, result: dict | None = None):
    """Save the full request payload + result to GCS for replay. Non-blocking."""
    if not REQUEST_LOG_BUCKET:
        return
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(REQUEST_LOG_BUCKET)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        prompt_preview = (body.get("prompt") or body.get("task_prompt") or "unknown")[:50]
        prompt_preview = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt_preview).strip().replace(" ", "_")[:40]
        filename = f"requests/{ts}_{prompt_preview}.json"

        # Save full payload including files, credentials, and result
        payload = {
            "request": body,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        blob = bucket.blob(filename)
        blob.upload_from_string(json.dumps(payload, ensure_ascii=False, default=str), content_type="application/json")
        logger.info(f"Request saved to gs://{REQUEST_LOG_BUCKET}/{filename}")
    except Exception as e:
        logger.warning(f"Failed to save request to GCS: {e}")


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


@traceable(name="handle_accounting_task")
def _handle_task(prompt: str, files: list, base_url: str, session_token: str,
                 metadata: dict | None = None) -> dict | None:
    """Core task handler — wrapped with LangSmith tracing.

    Args:
        metadata: Competition metadata (prompt_hash, prompt_preview, file_count).
                  Captured by @traceable as a trace input for LangSmith filtering.
    """
    file_contents = process_files(files)
    _preconfigure_bank_account(base_url, session_token)
    return run_agent(prompt, file_contents, base_url, session_token)


@app.post("/")
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
    creds = body.get("tripletex_credentials") or {}
    base_url = creds.get("base_url") or body.get("tripletex_base_url", "")
    session_token = creds.get("session_token") or body.get("session_token", "")

    logger.info(f"Task received. Prompt: {prompt}")
    logger.info(f"Files: {len(files)}, Base URL: {base_url}")

    result = None
    try:
        metadata = {
            "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
            "prompt_preview": prompt[:80],
            "file_count": len(files),
        }
        result = _handle_task(prompt, files, base_url, session_token, metadata=metadata)
        logger.info(f"Agent: {result}")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Save full request+result to GCS (synchronous — Cloud Run freezes CPU after response)
    _save_request_to_gcs(body, result)

    return JSONResponse({"status": "completed"})
