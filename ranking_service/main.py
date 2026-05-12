from fastapi import FastAPI
app = FastAPI(title="Module M8")
@app.get("/health")
def health(): return {"status": "ok", "module": "M8"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
