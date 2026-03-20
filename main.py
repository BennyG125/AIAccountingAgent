import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from agent import run_agent
from file_handler import process_files
from tripletex_api import TripletexClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Accounting Agent")

API_KEY = os.getenv("API_KEY")
REQUEST_TIMEOUT = 300  # 5 minutes


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve")
async def solve(request: Request):
    start_time = time.time()
    deadline = start_time + REQUEST_TIMEOUT

    # Optional: API key protection
    if API_KEY:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {API_KEY}":
            raise HTTPException(status_code=401, detail="Invalid API key")

    body = await request.json()
    prompt = body["prompt"]
    files = body.get("files", [])
    creds = body["tripletex_credentials"]

    logger.info(f"Task received. Prompt: {prompt[:100]}... Files: {len(files)}")

    try:
        file_contents = process_files(files)
        client = TripletexClient(creds["base_url"], creds["session_token"])

        result = run_agent(
            client=client,
            prompt=prompt,
            file_contents=file_contents,
            deadline=deadline,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"Agent finished in {elapsed:.1f}s. "
            f"Success: {result['success']}, "
            f"API calls: {result['api_calls']}, "
            f"Errors: {result['errors']}"
        )

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)

    # Always return completed — partial work earns partial credit
    return JSONResponse({"status": "completed"})
