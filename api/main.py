from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import protection

app = FastAPI(title="Adversarial Video Protection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(protection.router, prefix="/api/v1/protection")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
