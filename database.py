from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class InputStock(Base):
    __tablename__ = 'input_stock'
    id = Column(Integer, primary_key=True)
    product = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=func.datetime('now', '-3 hours'))

class OutputStock(Base):
    __tablename__ = 'output_stock'
    id = Column(Integer, primary_key=True)
    product = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=func.datetime('now', '-3 hours'))

class BalancedStock(Base):
    __tablename__ = 'balanced_stock'
    id = Column(Integer, primary_key=True)
    product = Column(String, nullable=False, unique=True)
    current_stock = Column(Integer, nullable=False)
    updated_at = Column(DateTime, default=func.datetime('now', '-3 hours'))

# Database setup
engine = create_engine('sqlite:///stock.db')
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)
