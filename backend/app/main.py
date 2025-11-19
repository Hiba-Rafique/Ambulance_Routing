from fastapi import FastAPI
from app.routers import routing, traffic, ambulance

app = FastAPI(title="DSA Ambulance Routing")

# Include routers
app.include_router(routing.router, prefix="/route", tags=["Route"])
app.include_router(traffic.router, prefix="/traffic", tags=["Traffic"])
app.include_router(ambulance.router, prefix="/ambulance", tags=["Ambulance"])

@app.get("/")
def root():
    return {"message": "Ambulance Routing System Backend Running!"}
