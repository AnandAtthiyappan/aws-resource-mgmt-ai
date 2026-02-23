from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from processor import process_request

app = FastAPI()

# Allow Streamlit to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "FastAPI is running"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    history = data.get("history", [])  # ✅ Grab history from frontend

    response = process_request(user_input, history)

    return {
        "response": response,
        "updated_history": history  # ✅ Return updated history to Streamlit
    }
