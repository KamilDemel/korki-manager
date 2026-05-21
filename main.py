import jwt
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, create_engine, Session, select
from contextlib import asynccontextmanager
from sqlmodel import Relationship
from datetime import datetime, timedelta
from fastapi import Query
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
sqlite_url = "sqlite:///baza.db"
engine = create_engine(sqlite_url)
SECRET_KEY = "cfa21af05f0843c2fcf0d5a753db321a6ce43d4c5b2f74cc357431f27cd1f6e4"
ALGORITHM = "HS256"
straznik_tokenow = OAuth2PasswordBearer(tokenUrl="login")
class UCZEN(SQLModel, table = True):
    id: int | None = Field(default=None, primary_key=True)
    imie: str
    nazwisko: str
    stawka_za_godzine: int
    lekcje: list["LEKCJA"] = Relationship(back_populates="uczen")
class LEKCJA(SQLModel, table = True):
    id_lekcji: int | None = Field(default=None, primary_key=True)
    data: datetime
    czas_trwania_minuty: int = 60
    czy_oplacona: bool = False
    uczen_id: int = Field(foreign_key="uczen.id")
    uczen: UCZEN | None = Relationship(back_populates="lekcje")
@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
app = FastAPI(lifespan=lifespan)
@app.post("/login")
def logowanie(username: str, password: str, token: str = Depends(straznik_tokenow)):
    if username == "kamil" and password == "jebactuska":
        return {"access_token": "super_tajny_token", "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="zly login lub haslo")
@app.get("/")
def funkcja():
    return {"wiadomosc":"Korki manager działa!"}
@app.post("/dodaj_ucznia")
def dodaj_nowego(nowy_uczen: UCZEN, token: str = Depends(straznik_tokenow)):
    with Session(engine) as session:
        session.add(nowy_uczen)
        session.commit()
        session.refresh(nowy_uczen)
        return nowy_uczen
@app.get("/uczniowie")
def pobierz_wszystkich(
    skip: int = 0,
    limit: int = Query(default=10, le=100),
    nazwisko: str | None = None
):
    with Session(engine) as session:
        zapytanie = select(UCZEN)
        if nazwisko:
            zapytanie = zapytanie.where(UCZEN.nazwisko == nazwisko)
        zapytanie = zapytanie.offset(skip).limit(limit)
        wynik = session.exec(zapytanie).all()
        return wynik
@app.get("/uczen/{uczen_id}")
def pobierz_jednego(uczen_id: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Nie ma takiego ucznia")
        return uczen
@app.patch("/uczen/{uczen_id}/stawka")
def ustaw_nowa_stawke(uczen_id: int, nowa_stawka: int, token: str = Depends(straznik_tokenow)):
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
def usun_ucznia(uczen_id: int, token: str = Depends(straznik_tokenow)):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Ten uczen nie istnieje lub zostal juz usuniety")
        session.delete(uczen)
        session.commit()
        return {"wiadomosc": f"Uczen o ID {uczen_id} zostal trwale usuniety"}
@app.post("/uczen/{uczen_id}/lekcja")
def dodaj_lekcje_dla_ucznia(uczen_id: int, nowa_lekcja: LEKCJA, token: str = Depends(straznik_tokenow)):
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
def aktualizuj_lekcje(lekcja_id: int, czas_trwania: int | None = None, czy_zaplacono: bool | None = None, token: str = Depends(straznik_tokenow)):
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
def usun_lekcje(lekcja_id: int, token: str = Depends(straznik_tokenow)):
    with Session(engine) as session:
        lekcja = session.get(LEKCJA, lekcja_id)
        if not lekcja:
            raise HTTPException(status_code=404, detail= "Ta lekcja nie istnieje, nie mozemy jej usunac")
        session.delete(lekcja)
        session.commit()
        return {"wiadomosc" : f"Lekcja o id {lekcja_id} zostala usunieta"}
@app.get("/uczen/{uczen_id}/balans")
def pobierz_balans_ucznia(uczen_id: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail= "Podany uczen nie istnieje")
        zapytanie = select(LEKCJA).where(LEKCJA.uczen_id == uczen_id).where(LEKCJA.czy_oplacona == False)
        nieoplacone_lekcje = session.exec(zapytanie).all()
        suma_minut = sum(lekcja.czas_trwania_minuty for lekcja in nieoplacone_lekcje)
        naleznosc = (suma_minut / 60) * uczen.stawka_za_godzine
        return {
            "uczen": f"{uczen.imie} {uczen.nazwisko}",
            "liczba_nieoplaconych_lekcji": len(nieoplacone_lekcje),
            "laczny_czas_zalegly_minuty": suma_minut,
            "laczna_naleznosc": naleznosc
        }
