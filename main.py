import jwt
import time
from fastapi import FastAPI, HTTPException
from sqlmodel import SQLModel, Field, create_engine, Session, select
from contextlib import asynccontextmanager
from sqlmodel import Relationship
from datetime import datetime, timedelta, timezone
from fastapi import Query
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi import BackgroundTasks
def wyslij_powiadomienie_o_dlugu(imie_ucznia: str, kwota: float):
    time.sleep(5)
    print(f"--- [TŁO] Wysłano przypomnienie do {imie_ucznia} o zaległości {kwota} zł ---")
sqlite_url = "sqlite:///baza.db"
engine = create_engine(sqlite_url)
SECRET_KEY = "cfa21af05f0843c2fcf0d5a753db321a6ce43d4c5b2f74cc357431f27cd1f6e4"
ALGORITHM = "HS256"
czas_wygasniecia_minuty = 60
straznik_tokenow = OAuth2PasswordBearer(tokenUrl="login")
class UczenBase(SQLModel):
    imie: str
    nazwisko: str
    stawka_za_godzine: int
    lekcje: list["LEKCJA"] = Relationship(back_populates="uczen")
class UCZEN(UczenBase, table = True):
    id: int | None = Field(default=None, primary_key=True)
class UczenResponse(UczenBase):
    id: int
class LekcjaBase(SQLModel):
    data: datetime
    czas_trwania_minuty: int = 60
    czy_oplacona: bool = False
    uczen_id: int = Field(foreign_key="uczen.id")
    uczen: UCZEN | None = Relationship(back_populates="lekcje")
class LEKCJA(LekcjaBase, table = True):
    id_lekcji: int | None = Field(default=None, primary_key=True)
class LekcjaResponse(LekcjaBase):
    id_lekcji: int
class BalansResponse(BaseModel):
    uczen: str
    liczba_nieoplaconych_lekcji: int
    laczny_czas_zalegly_minuty: int
    laczna_naleznosc: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
app = FastAPI(lifespan=lifespan)
def weryfikuj_token(token: str = Depends(straznik_tokenow)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Nieprawidlowy token")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token wygasl, zaloguj sie ponownie")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="brak dostepu, sygnatura naruszona")
@app.post("/login")
def logowanie(formularz: OAuth2PasswordRequestForm = Depends()):
    if formularz.username == "kamil" and formularz.password == "jebactuska":
        wygasa = datetime.now(timezone.utc) + timedelta(minutes=czas_wygasniecia_minuty)
        dane_do_tokena = {
            "sub": formularz.username,
            "exp": wygasa
        }
        zakodowany_token = jwt.encode(dane_do_tokena, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": zakodowany_token, "token_type": "bearer"}
    raise HTTPException(status_code=400, detail="zly login lub haslo")
@app.get("/")
def funkcja():
    return {"wiadomosc":"Korki manager działa!"}
@app.post("/dodaj_ucznia", dependencies=[Depends(straznik_tokenow)], response_model=UczenResponse)
def dodaj_nowego(nowy_uczen: UczenBase):
    with Session(engine) as session:
        db_uczen  = UCZEN.model_validate(nowy_uczen)
        session.add(db_uczen)
        session.commit()
        session.refresh(db_uczen)
        return db_uczen
@app.get("/uczniowie", response_model=list[UczenResponse])
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
@app.get("/uczen/{uczen_id}", response_model=UczenResponse)
def pobierz_jednego(uczen_id: int):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Nie ma takiego ucznia")
        return uczen
@app.patch("/uczen/{uczen_id}/stawka", dependencies=[Depends(straznik_tokenow)], response_model=UczenResponse)
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
def usun_ucznia(uczen_id: int, zalogowany_admin: str = Depends(weryfikuj_token)):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail="Ten uczen nie istnieje lub zostal juz usuniety")
        session.delete(uczen)
        session.commit()
        return {"wiadomosc": f"Uczen o ID {uczen_id} usuniety przez {zalogowany_admin}"}
@app.post("/uczen/{uczen_id}/lekcja", dependencies=[Depends(straznik_tokenow)], response_model=LekcjaResponse)
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
@app.patch("/lekcja/{lekcja_id}", dependencies=[Depends(straznik_tokenow)], response_model=LekcjaResponse)
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
@app.delete("/lekcja/{lekcja_id}", dependencies=[Depends(straznik_tokenow)])
def usun_lekcje(lekcja_id: int):
    with Session(engine) as session:
        lekcja = session.get(LEKCJA, lekcja_id)
        if not lekcja:
            raise HTTPException(status_code=404, detail= "Ta lekcja nie istnieje, nie mozemy jej usunac")
        session.delete(lekcja)
        session.commit()
        return {"wiadomosc" : f"Lekcja o id {lekcja_id} zostala usunieta"}
@app.get("/uczen/{uczen_id}/balans", response_model=BalansResponse, dependencies=[Depends(straznik_tokenow)])
def pobierz_balans_ucznia(uczen_id: int, background_tasks: BackgroundTasks):
    with Session(engine) as session:
        uczen = session.get(UCZEN, uczen_id)
        if not uczen:
            raise HTTPException(status_code=404, detail= "Podany uczen nie istnieje")
        zapytanie = select(LEKCJA).where(LEKCJA.uczen_id == uczen_id).where(LEKCJA.czy_oplacona == False)
        nieoplacone_lekcje = session.exec(zapytanie).all()
        suma_minut = sum(lekcja.czas_trwania_minuty for lekcja in nieoplacone_lekcje)
        naleznosc = (suma_minut / 60) * uczen.stawka_za_godzine
        if naleznosc > 0:
            background_tasks.add_task(
                wyslij_powiadomienie_o_dlugu,
                uczen.imie,
                naleznosc
            )
        return {
            "uczen": f"{uczen.imie} {uczen.nazwisko}",
            "liczba_nieoplaconych_lekcji": len(nieoplacone_lekcje),
            "laczny_czas_zalegly_minuty": suma_minut,
            "laczna_naleznosc": naleznosc
        }
