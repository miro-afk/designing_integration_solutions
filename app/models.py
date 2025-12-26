from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Author(Base):
    __tablename__ = "authors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    birth_date = Column(DateTime, nullable=True)
    nationality = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    books = relationship("Book", back_populates="author", cascade="all, delete-orphan")

class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    isbn = Column(String(13), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    year_published = Column(Integer, nullable=True)
    publisher = Column(String(100), nullable=True)
    pages = Column(Integer, nullable=True)
    language = Column(String(2), default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Foreign keys
    author_id = Column(Integer, ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)
    
    # New field for v2
    is_available = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    author = relationship("Author", back_populates="books")