import os
from datetime import datetime
from typing import List, Optional
import io

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
import pandas as pd

# ====================
# Database Configuration
# ====================
DATABASE_URL = "sqlite:///./absensiku.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ====================
# Database Models (SQLAlchemy)
# ====================
class Kelas(Base):
    __tablename__ = "kelas"
    id = Column(Integer, primary_key=True, index=True)
    nama_kelas = Column(String, default="xi dkv 2")
    sekolah = Column(String, default="smkibu")
    
    siswa = relationship("Siswa", back_populates="kelas", cascade="all, delete-orphan")
    aktivitas_nilai = relationship("Aktivitas_Nilai", back_populates="kelas", cascade="all, delete-orphan")
    absensi = relationship("Absensi", back_populates="kelas", cascade="all, delete-orphan")


class Siswa(Base):
    __tablename__ = "siswa"
    nis = Column(String, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    jenis_kelamin = Column(String)  # L or P
    kelas_id = Column(Integer, ForeignKey("kelas.id"), nullable=False)
    
    kelas = relationship("Kelas", back_populates="siswa")
    detail_nilai = relationship("Detail_Nilai", back_populates="siswa", cascade="all, delete-orphan")
    detail_absensi = relationship("Detail_Absensi", back_populates="siswa", cascade="all, delete-orphan")


class Aktivitas_Nilai(Base):
    __tablename__ = "aktivitas_nilai"
    id = Column(Integer, primary_key=True, index=True)
    nama_aktivitas = Column(String, nullable=False)  # e.g., "Ulangan Harian"
    tanggal = Column(DateTime, default=datetime.utcnow)
    kelas_id = Column(Integer, ForeignKey("kelas.id"), nullable=False)
    
    kelas = relationship("Kelas", back_populates="aktivitas_nilai")
    detail_nilai = relationship("Detail_Nilai", back_populates="aktivitas", cascade="all, delete-orphan")


class Detail_Nilai(Base):
    __tablename__ = "detail_nilai"
    id = Column(Integer, primary_key=True, index=True)
    aktivitas_id = Column(Integer, ForeignKey("aktivitas_nilai.id"), nullable=False)
    siswa_nis = Column(String, ForeignKey("siswa.nis"), nullable=False)
    nilai = Column(Float, nullable=False)
    catatan = Column(String, nullable=True)
    
    aktivitas = relationship("Aktivitas_Nilai", back_populates="detail_nilai")
    siswa = relationship("Siswa", back_populates="detail_nilai")


class Absensi(Base):
    __tablename__ = "absensi"
    id = Column(Integer, primary_key=True, index=True)
    tanggal = Column(DateTime, default=datetime.utcnow)
    kelas_id = Column(Integer, ForeignKey("kelas.id"), nullable=False)
    
    kelas = relationship("Kelas", back_populates="absensi")
    detail_absensi = relationship("Detail_Absensi", back_populates="absensi", cascade="all, delete-orphan")


class Detail_Absensi(Base):
    __tablename__ = "detail_absensi"
    id = Column(Integer, primary_key=True, index=True)
    absensi_id = Column(Integer, ForeignKey("absensi.id"), nullable=False)
    siswa_nis = Column(String, ForeignKey("siswa.nis"), nullable=False)
    status = Column(String)  # Hadir, Alfa, Izin, Sakit
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    absensi = relationship("Absensi", back_populates="detail_absensi")
    siswa = relationship("Siswa", back_populates="detail_absensi")


# ====================
# Pydantic Schemas
# ====================
class SiswaSchema(BaseModel):
    nis: str
    nama: str
    jenis_kelamin: str
    kelas_id: int

    class Config:
        from_attributes = True


class KelasSchema(BaseModel):
    id: int
    nama_kelas: str
    sekolah: str

    class Config:
        from_attributes = True


class Detail_NilaiSchema(BaseModel):
    id: int
    aktivitas_id: int
    siswa_nis: str
    nilai: float
    catatan: Optional[str]

    class Config:
        from_attributes = True


class Aktivitas_NilaiSchema(BaseModel):
    id: int
    nama_aktivitas: str
    tanggal: datetime
    kelas_id: int
    detail_nilai: List[Detail_NilaiSchema] = []

    class Config:
        from_attributes = True


class Detail_AbsensiSchema(BaseModel):
    id: int
    absensi_id: int
    siswa_nis: str
    status: str
    updated_at: datetime

    class Config:
        from_attributes = True


class AbsensiSchema(BaseModel):
    id: int
    tanggal: datetime
    kelas_id: int
    detail_absensi: List[Detail_AbsensiSchema] = []

    class Config:
        from_attributes = True


# ====================
# Create Tables
# ====================
Base.metadata.create_all(bind=engine)


# ====================
# Initialize Default Data
# ====================
def init_default_data():
    db = SessionLocal()
    
    # Check if default kelas exists
    kelas = db.query(Kelas).filter(Kelas.nama_kelas == "xi dkv 2").first()
    if not kelas:
        kelas = Kelas(nama_kelas="xi dkv 2", sekolah="smkibu")
        db.add(kelas)
        db.commit()
        db.refresh(kelas)
    
    # Check if default siswa exists
    siswa = db.query(Siswa).filter(Siswa.nama == "Andi").first()
    if not siswa:
        siswa = Siswa(nis="001", nama="Andi", jenis_kelamin="L", kelas_id=kelas.id)
        db.add(siswa)
        db.commit()
    
    db.close()


init_default_data()


# ====================
# FastAPI App
# ====================
app = FastAPI(title="Absensiku - Manajemen Absensi & Nilai Sekolah")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====================
# API Endpoints - Kelas
# ====================
@app.get("/api/kelas", response_model=List[KelasSchema])
def get_kelas(db: Session = Depends(get_db)):
    """Get all kelas"""
    kelas_list = db.query(Kelas).all()
    return kelas_list


@app.get("/api/kelas/{kelas_id}", response_model=KelasSchema)
def get_kelas_by_id(kelas_id: int, db: Session = Depends(get_db)):
    """Get kelas by ID"""
    kelas = db.query(Kelas).filter(Kelas.id == kelas_id).first()
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    return kelas


@app.post("/api/kelas")
def create_kelas(nama_kelas: str = Form(...), sekolah: str = Form(...), db: Session = Depends(get_db)):
    """Create new kelas"""
    kelas = Kelas(nama_kelas=nama_kelas, sekolah=sekolah)
    db.add(kelas)
    db.commit()
    db.refresh(kelas)
    return {"id": kelas.id, "nama_kelas": kelas.nama_kelas, "sekolah": kelas.sekolah}


# ====================
# API Endpoints - Siswa
# ====================
@app.get("/api/siswa", response_model=List[SiswaSchema])
def get_siswa(kelas_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all siswa, optionally filtered by kelas"""
    query = db.query(Siswa)
    if kelas_id:
        query = query.filter(Siswa.kelas_id == kelas_id)
    return query.all()


@app.post("/api/siswa")
def create_siswa(
    nis: str = Form(...),
    nama: str = Form(...),
    jenis_kelamin: str = Form(...),
    kelas_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Create new siswa"""
    siswa = Siswa(nis=nis, nama=nama, jenis_kelamin=jenis_kelamin, kelas_id=kelas_id)
    db.add(siswa)
    db.commit()
    db.refresh(siswa)
    return {"nis": siswa.nis, "nama": siswa.nama, "jenis_kelamin": siswa.jenis_kelamin, "kelas_id": siswa.kelas_id}


@app.post("/api/siswa/import")
async def import_siswa(file: UploadFile = File(...), kelas_id: int = Form(...), db: Session = Depends(get_db)):
    """Import siswa from CSV file (NIS, Nama, Jenis_Kelamin)"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                nis = str(row['NIS']).strip()
                nama = str(row['Nama']).strip()
                jenis_kelamin = str(row['Jenis_Kelamin']).strip()
                
                # Check if siswa already exists
                existing = db.query(Siswa).filter(Siswa.nis == nis).first()
                if existing:
                    errors.append(f"Row {index + 1}: NIS {nis} sudah ada")
                    continue
                
                siswa = Siswa(nis=nis, nama=nama, jenis_kelamin=jenis_kelamin, kelas_id=kelas_id)
                db.add(siswa)
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        db.commit()
        
        return {
            "status": "success",
            "imported": imported_count,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


# ====================
# API Endpoints - Aktivitas Nilai
# ====================
@app.get("/api/aktivitas-nilai", response_model=List[Aktivitas_NilaiSchema])
def get_aktivitas_nilai(kelas_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all aktivitas nilai"""
    query = db.query(Aktivitas_Nilai)
    if kelas_id:
        query = query.filter(Aktivitas_Nilai.kelas_id == kelas_id)
    return query.all()


@app.post("/api/aktivitas-nilai")
def create_aktivitas_nilai(
    nama_aktivitas: str = Form(...),
    kelas_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Create new aktivitas nilai"""
    aktivitas = Aktivitas_Nilai(nama_aktivitas=nama_aktivitas, kelas_id=kelas_id, tanggal=datetime.utcnow())
    db.add(aktivitas)
    db.commit()
    db.refresh(aktivitas)
    return {"id": aktivitas.id, "nama_aktivitas": aktivitas.nama_aktivitas, "kelas_id": aktivitas.kelas_id}


# ====================
# API Endpoints - Detail Nilai
# ====================
@app.post("/api/detail-nilai")
def create_detail_nilai(
    aktivitas_id: int = Form(...),
    siswa_nis: str = Form(...),
    nilai: float = Form(...),
    catatan: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Create/Update detail nilai"""
    existing = db.query(Detail_Nilai).filter(
        Detail_Nilai.aktivitas_id == aktivitas_id,
        Detail_Nilai.siswa_nis == siswa_nis
    ).first()
    
    if existing:
        existing.nilai = nilai
        existing.catatan = catatan
    else:
        detail = Detail_Nilai(
            aktivitas_id=aktivitas_id,
            siswa_nis=siswa_nis,
            nilai=nilai,
            catatan=catatan
        )
        db.add(detail)
    
    db.commit()
    return {"status": "success"}


@app.get("/api/detail-nilai/{aktivitas_id}")
def get_detail_nilai(aktivitas_id: int, db: Session = Depends(get_db)):
    """Get detail nilai by aktivitas"""
    return db.query(Detail_Nilai).filter(Detail_Nilai.aktivitas_id == aktivitas_id).all()


# ====================
# API Endpoints - Absensi
# ====================
@app.get("/api/absensi", response_model=List[AbsensiSchema])
def get_absensi(kelas_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get all absensi"""
    query = db.query(Absensi)
    if kelas_id:
        query = query.filter(Absensi.kelas_id == kelas_id)
    return query.all()


@app.post("/api/absensi")
def create_absensi(kelas_id: int = Form(...), db: Session = Depends(get_db)):
    """Create new absensi record"""
    absensi = Absensi(kelas_id=kelas_id, tanggal=datetime.utcnow())
    db.add(absensi)
    db.commit()
    db.refresh(absensi)
    
    # Auto-create detail_absensi for all siswa in kelas
    siswa_list = db.query(Siswa).filter(Siswa.kelas_id == kelas_id).all()
    for siswa in siswa_list:
        detail = Detail_Absensi(
            absensi_id=absensi.id,
            siswa_nis=siswa.nis,
            status="Hadir",
            updated_at=datetime.utcnow()
        )
        db.add(detail)
    
    db.commit()
    return {"id": absensi.id, "kelas_id": absensi.kelas_id}


# ====================
# API Endpoints - Detail Absensi
# ====================
@app.get("/api/detail-absensi/{absensi_id}")
def get_detail_absensi(absensi_id: int, db: Session = Depends(get_db)):
    """Get detail absensi by absensi ID"""
    return db.query(Detail_Absensi).filter(Detail_Absensi.absensi_id == absensi_id).all()


@app.put("/api/detail-absensi/{detail_id}")
def update_detail_absensi(
    detail_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update detail absensi status"""
    detail = db.query(Detail_Absensi).filter(Detail_Absensi.id == detail_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="Detail absensi tidak ditemukan")
    
    detail.status = status
    detail.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}


# ====================
# Frontend Route
# ====================
@app.get("/", response_class=HTMLResponse)
def get_index():
    """Serve index.html"""
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
