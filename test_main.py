import pytest
from fastapi.testclient import TestClient
from main import app, SessionLocal, Base, engine

# Setup test client
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create test database and cleanup after test"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_example():
    """Example test"""
    assert True


def test_read_root(test_db):
    """Test root endpoint returns HTML response"""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_get_kelas_empty(test_db):
    """Test getting kelas when empty"""
    response = client.get("/api/kelas")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_kelas(test_db):
    """Test creating a new kelas"""
    response = client.post(
        "/api/kelas",
        data={"nama_kelas": "xi dkv 1", "sekolah": "smkibu"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nama_kelas"] == "xi dkv 1"
    assert data["sekolah"] == "smkibu"


def test_get_siswa_empty(test_db):
    """Test getting siswa when empty"""
    response = client.get("/api/siswa")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_aktivitas_nilai(test_db):
    """Test creating aktivitas nilai"""
    # First create a kelas
    kelas_response = client.post(
        "/api/kelas",
        data={"nama_kelas": "xi dkv 1", "sekolah": "smkibu"}
    )
    kelas_id = kelas_response.json()["id"]
    
    # Then create aktivitas nilai
    response = client.post(
        "/api/aktivitas-nilai",
        data={"nama_aktivitas": "Ulangan Harian", "kelas_id": kelas_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nama_aktivitas"] == "Ulangan Harian"


def test_get_absensi_empty(test_db):
    """Test getting absensi when empty"""
    response = client.get("/api/absensi")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
