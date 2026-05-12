from fastapi import FastAPI
app = FastAPI(title="Crop Calendar (M5)")
@app.get("/health")
def health(): return {"status": "ok", "module": "M5"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
