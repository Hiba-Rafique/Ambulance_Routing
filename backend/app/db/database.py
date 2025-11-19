from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# mnm and zz pls replace with your own details then run create_tables.py
# IMPORTANT - pehlai create an empty db named ambulance_routing in your user in mysql
# then replace the below url with "mysql+mysqlconnector://USER:PASSWORD@localhost/ambulance_routing"
SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root1:oop_app3@localhost/ambulance_routing"

print("Connecting to the database...")  

try:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
    connection = engine.connect()
    print("Database connected successfully!") 
    connection.close()
except OperationalError as e:
    print("Error connecting to the database:", e)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
