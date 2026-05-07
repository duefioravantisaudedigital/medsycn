import os
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, TIMESTAMP, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

# Usando postgres padrão local (você pode sobrescrever criando um arquivo .env)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Medico(Base):
    __tablename__ = "medicos"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(255), nullable=False)
    crm = Column(String(20), unique=True, nullable=True)
    uf_crm = Column(String(2), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    memed_token = Column(String, nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)

class Paciente(Base):
    __tablename__ = "pacientes"
    id = Column(Integer, primary_key=True, index=True)
    cpf = Column(String(11), unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20), nullable=True)
    data_nascimento = Column(Date, nullable=True)
    email = Column(String(255), nullable=True)
    cep = Column(String(20), nullable=True)

class Consulta(Base):
    __tablename__ = "consultas"
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"), nullable=False)
    medico_id = Column(Integer, ForeignKey("medicos.id"), nullable=False)
    data_consulta = Column(TIMESTAMP, server_default=func.now(), nullable=False)

class SyncLog(Base):
    __tablename__ = "sync_logs"
    id = Column(Integer, primary_key=True, index=True)
    consulta_id = Column(Integer, ForeignKey("consultas.id"), nullable=False)
    status = Column(String(50), nullable=False)
    data_hora = Column(TIMESTAMP, server_default=func.now(), nullable=False)

# Função para criar as tabelas se não existirem
def init_db():
    Base.metadata.create_all(bind=engine)
