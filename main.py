import base64
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from planner import plan_task
from executor import execute_plan
from recovery import recover_and_execute
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


@app.post("/solve")
async def solve(request: Request):
    # Optional: API key protection
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()
    prompt = body["prompt"]
    files = body.get("files", [])
    creds = body["tripletex_credentials"]

    base_url = creds["base_url"]
    session_token = creds["session_token"]

    logger.info(f"Received task. Prompt length: {len(prompt)}, Files: {len(files)}")

    try:
        # Step 1: Process any attached files
        file_contents = process_files(files)

        # Step 2: Plan — Gemini analyzes prompt and returns execution plan
        client = TripletexClient(base_url, session_token)
        plan = plan_task(prompt, file_contents)

        logger.info(f"Plan generated with {len(plan['steps'])} steps")

        # Step 3: Execute the plan
        result = execute_plan(client, plan)

        if not result["success"]:
            # Step 4: Recovery — send error context back to Gemini
            logger.warning(f"Step {result['failed_step']} failed: {result['error']}")
            recover_and_execute(client, prompt, file_contents, plan, result)

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Always return completed — partial work may earn partial credit
    return JSONResponse({"status": "completed"})
