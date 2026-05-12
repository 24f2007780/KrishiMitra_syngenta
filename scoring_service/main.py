from fastapi import FastAPI
app = FastAPI(title="Module M7")
@app.get("/health")
def health(): return {"status": "ok", "module": "M7"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
