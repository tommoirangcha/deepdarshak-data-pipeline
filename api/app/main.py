from fastapi import FastAPI
from .core.config import get_settings
from .routers.vessels import router as vessels_router
from .routers.visualizations import router as visualizations_router


def create_app() -> FastAPI:
	settings = get_settings()
	app = FastAPI(title="DeepDarshak API", version="0.1.0")

	# Routers
	app.include_router(vessels_router, prefix="/vessels", tags=["vessels"])
	app.include_router(visualizations_router, prefix="/visualizations", tags=["visualizations"])

	@app.get("/health")
	def health():
		return {"status": "ok"}

	return app


app = create_app()
