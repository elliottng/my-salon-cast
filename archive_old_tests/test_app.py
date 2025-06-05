from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

@app.post("/test")
async def test_endpoint():
    return {"status": "success", "message": "Test endpoint is working!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("test_app:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
