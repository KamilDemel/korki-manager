from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, create_engine, Session, select
from contextlib import asynccontextmanager
sqlite_url = "sqlite:///baza.db"
engine = create_engine(sqlite_url)
class UCZEN(SQLModel, table = True):
    id: int | None = Field(default=None, primary_key=True)
    imie: str
    nazwisko: str
    stawka_za_godzine: int
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
app = FastAPI(lifespan=lifespan)
@app.get("/")
def funkcja():
    return {"wiadomosc":"Korki manager działa!"}
@app.post("/dodaj_ucznia")
def dodaj_nowego(nowy_uczen: UCZEN):
    with Session(engine) as session:
        session.add(nowy_uczen)
        session.commit()
        session.refresh(nowy_uczen)
        return nowy_uczen
@app.get("/uczniowie")
def pobierz_wszystkich():
    with Session(engine) as session:
        wynik = session.exec(select(UCZEN)).all()
        return wynik
@app.get("/uczen/{uczen_id}")
def pobierz_jednego(uczen_id: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Nie ma takiego ucznia")
        return uczen
