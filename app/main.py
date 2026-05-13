from fastapi import FastAPI
from app.routes import calendar

app = FastAPI(
    title="M3 Crop Calendar Service",
    description="REST service that returns the current crop stage information for given state, crop and month.",
    version="1.0.0"
)

# Include routes
app.include_router(calendar.router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the M3 Crop Calendar Service",
        "endpoints": {
            "calendar": "/calendar?state=<state>&crop=<crop>",
            "states": "/calendar/states",
            "crops": "/calendar/crops"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
