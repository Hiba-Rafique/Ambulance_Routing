from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import routing, traffic, ambulance, websocket

app = FastAPI(title="DSA Ambulance Routing")

# Allow the Next.js frontend (running on localhost:3000) to call this API.
# This is important in development; otherwise the browser will block
# cross-origin requests and the frontend sees only "Failed to fetch".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routing.router, prefix="/route", tags=["Route"])
app.include_router(traffic.router, prefix="/traffic", tags=["Traffic"])
app.include_router(ambulance.router, prefix="/ambulance", tags=["Ambulance"])
app.include_router(websocket.router, tags=["WebSocket"])

@app.get("/")
def root():
    return {"message": "Ambulance Routing System Backend Running!"}
