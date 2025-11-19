from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    # country = Column(String(50), default="Pakistan")
    # each city consists of nodes (locations)
    nodes = relationship("Node", back_populates="city")

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    name = Column(String(100))
    type = Column(String(50))  # intersection / hospital / station
    city_id = Column(Integer, ForeignKey("cities.id"))

    
    city = relationship("City", back_populates="nodes")
    # edge -> node -> edge type relation ok takai agay peechay ka pata ho
    edges_from = relationship("Edge", back_populates="from_node_rel", foreign_keys='Edge.from_node')
    edges_to = relationship("Edge", back_populates="to_node_rel", foreign_keys='Edge.to_node')


class Edge(Base):
    __tablename__ = "edges"
    id = Column(Integer, primary_key=True, index=True)
    from_node = Column(Integer, ForeignKey("nodes.id"))
    to_node = Column(Integer, ForeignKey("nodes.id"))
    weight = Column(Float, nullable=False)  # travel time in minutes
    adjusted_weight = Column(Float, nullable=True) # travel time adjusted with respect to traffic
    distance = Column(Float, nullable=True)  # distance in meters
    is_active = Column(Boolean, default=True)  # true if road is open

    # node -> edge -> node type relation
    from_node_rel = relationship("Node", foreign_keys=[from_node], back_populates="edges_from")
    to_node_rel = relationship("Node", foreign_keys=[to_node], back_populates="edges_to")


class Ambulance(Base):
    __tablename__ = "ambulances"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    status = Column(String(20), default="available")  # available / busy
    current_node = Column(Integer, ForeignKey("nodes.id"))
    speed = Column(Float, default=60.0)  # km/h

    # current location, which node is ambulance at 
    node = relationship("Node")



class EmergencyRequest(Base):
    __tablename__ = "emergency_requests"
    id = Column(Integer, primary_key=True, index=True)
    source_node = Column(Integer, ForeignKey("nodes.id")) # patient location
    destination_node = Column(Integer, ForeignKey("nodes.id")) # hospital location
    status = Column(String(20), default="pending")  # pending / in-progress / completed
    created_at = Column(DateTime, default=datetime.utcnow)

    
    source = relationship("Node", foreign_keys=[source_node])
    destination = relationship("Node", foreign_keys=[destination_node])



class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True, index=True)
    ambulance_id = Column(Integer, ForeignKey("ambulances.id"))
    emergency_request_id = Column(Integer, ForeignKey("emergency_requests.id"))
    eta = Column(Float)  # estimated minutes to reach destination
    status = Column(String(20), default="assigned")  # assigned / in-transit / completed

    # Relationships
    ambulance = relationship("Ambulance")
    emergency_request = relationship("EmergencyRequest")



class TrafficUpdate(Base):
    __tablename__ = "traffic_updates"
    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(Integer, ForeignKey("edges.id"))
    new_weight = Column(Float)  # new travel time
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    edge = relationship("Edge")


class Roadblock(Base):
    __tablename__ = "roadblocks"
    id = Column(Integer, primary_key=True, index=True)
    edge_id = Column(Integer, ForeignKey("edges.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    reason = Column(String(100))

    # Relationships
    edge = relationship("Edge")
