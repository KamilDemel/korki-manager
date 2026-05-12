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
class LEKCJA(SQLModel, table = True):
    id_lekcji: int | None = Field(default=None, primary_key=True)
    data: str
    czas_trwania_minuty: int = 60
    czy_oplacona: bool = False
    uczen_id: int = Field(foreign_key="uczen.id")
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
@app.patch("/uczen/{uczen_id}/stawka")
def ustaw_nowa_stawke(uczen_id: int, nowa_stawka: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Taki uczen nie istnieje")
        uczen.stawka_za_godzine = nowa_stawka
        session.add(uczen)
        session.commit()
        session.refresh(uczen)
        return uczen
@app.delete("/uczen/{uczen_id}")
def usun_ucznia(uczen_id: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Ten uczen nie istnieje lub zostal juz usuniety")
        session.delete(uczen)
        session.commit()
        return {"wiadomosc": f"Uczen o ID {uczen_id} zostal trwale usuniety"}
@app.post("/uczen/{uczen_id}/lekcja")
def dodaj_lekcje_dla_ucznia(uczen_id: int, nowa_lekcja: LEKCJA):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Nie mozna przypisac lekcji do nieistniejacego ucznia")
        nowa_lekcja.uczen_id = uczen_id
        session.add(nowa_lekcja)
        session.commit()
        session.refresh(nowa_lekcja)
        return nowa_lekcja
@app.patch("/lekcja/{lekcja_id}")
def aktualizuj_lekcje(lekcja_id: int, czas_trwania: int | None = None, czy_zaplacono: bool | None = None):
    with Session(engine) as session:
        lekcja = session.get(LEKCJA, lekcja_id)
        if not lekcja:
            raise HTTPException(status_code=404, detail="Ta lekcja nie istnieje")
        if czas_trwania is not None:
            lekcja.czas_trwania_minuty = czas_trwania
        if czy_zaplacono is not None:
            lekcja.czy_oplacona = czy_zaplacono
        session.add(lekcja)
        session.commit()
        session.refresh(lekcja)
        return lekcja
@app.delete("/lekcja/{lekcja_id}")
def usun_lekcje(lekcja_id: int):
    with Session(engine) as session:
        lekcja = session.get(LEKCJA, lekcja_id)
        if not lekcja:
            raise HTTPException(status_code=404, detail= "Ta lekcja nie istnieje, nie mozemy jej usunac")
        session.delete(lekcja)
        session.commit()
        return {"wiadomosc" : f"Lekcja o id {lekcja_id} zostala usunieta"}