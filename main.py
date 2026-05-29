from fastapi import FastAPI



app = FastAPI()

@app.get("/")
def home():
    return {" message": "I think there is something I am forgetting"}

