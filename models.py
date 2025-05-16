from datetime import timezone, datetime
from sqlalchemy import create_engine,Column, String, Integer, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
from dotenv import load_dotenv
import os

load_dotenv()

Base = declarative_base()


# -------------------------- DATABASE SCHEMA --------------------------

class BatteryPackModel(Base):
    __tablename__ = "batteryPack"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)

    # relationships
    steps = relationship("StepModel", back_populates="battery_pack", cascade="all, delete-orphan")
    disassemblies = relationship("DisassemblyModel", back_populates="battery_pack")

class StepModel(Base):
    __tablename__ = "steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    number = Column(Integer, nullable=False)
    time = Column(Float, nullable=True)
    risks = Column(String, nullable=True)
    batteryPack_id = Column(UUID(as_uuid=True), ForeignKey("batteryPack.id"), nullable=False)

    # relationships
    battery_pack = relationship("BatteryPackModel", back_populates="steps")
    timers = relationship("TimerModel", back_populates="step", cascade="all, delete-orphan")
    sub_steps = relationship("SubStepModel", back_populates="step", cascade="all, delete-orphan")
    pictures = relationship("PictureModel", back_populates="step", cascade="all, delete-orphan")
    tools = relationship("ToolModel", back_populates="step", cascade="all, delete-orphan")

class SubStepModel(Base):
    __tablename__ = "sub_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    number = Column(Integer, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=False)

    # relationships
    step = relationship("StepModel", back_populates="sub_steps")

class PictureModel(Base):
    __tablename__ = "pictures"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link = Column(String, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=False)

    # relationships
    step = relationship("StepModel", back_populates="pictures")

class ToolModel(Base):
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=False)

    # relationships
    step = relationship("StepModel", back_populates="tools")
  
class DisassemblyModel(Base):
    __tablename__ = "disassemblies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_time = Column(Integer, nullable=False)
    batteryPack_id = Column(UUID(as_uuid=True), ForeignKey("batteryPack.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc)) 

    # relationships
    battery_pack = relationship("BatteryPackModel", back_populates="disassemblies")
    timers = relationship("TimerModel", back_populates="disassembly", cascade="all, delete-orphan")
      
class TimerModel(Base):
    __tablename__ = "timers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    length = Column(Integer, nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("steps.id"), nullable=False)
    disassembly_id = Column(UUID(as_uuid=True), ForeignKey("disassemblies.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc)) 

    # relationships
    step = relationship("StepModel", back_populates="timers")
    disassembly = relationship("DisassemblyModel", back_populates="timers")




# -------------------------- CREATE DB --------------------------
    
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)