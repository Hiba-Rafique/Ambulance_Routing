from db.database import engine
from db import models

# Create all tables
models.Base.metadata.create_all(bind=engine)
print("Tables created successfully")
