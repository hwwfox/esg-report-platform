from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ESG Mock AI Gateway", version="0.1.0")


class ChatRequest(BaseModel):
    agent_type: str = "dev_ping"
    prompt: str | None = None
    input: dict | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ai-gateway", "model": "mock-model"}


@app.post("/v1/mock/generate")
async def generate(req: ChatRequest):
    return {
        "model": "mock-model",
        "agent_type": req.agent_type,
        "raw_output": "{\"ok\": true}",
        "parsed_output": {"ok": True},
        "input_tokens": 10,
        "output_tokens": 5,
        "total_cost": 0,
    }
