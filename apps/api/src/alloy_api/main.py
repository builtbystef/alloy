from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alloy_api.config import SettingsDep, get_settings
from alloy_api.routers import health

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)


@app.get("/")
async def read_root(settings: SettingsDep) -> dict[str, str]:
    return {"app": settings.app_name}
