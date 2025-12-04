from typing import Generator, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from pydantic import ConfigDict
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import City


router = APIRouter()


# Dependency to get a DB session per request
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CityOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/cities", response_model=List[CityOut])
def list_cities(db: Session = Depends(get_db)) -> List[CityOut]:
    cities = db.query(City).order_by(City.name).all()
    return cities
