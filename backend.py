import os
import threading


class AnalizatorPlikow:
    """Backend: skanuje folder w osobnym wątku i zwraca największe elementy.

    Kontrakt callbacku:
        callback_zakonczenia(wynik)

    gdzie `wynik` to dict:
        {
            "status": "OK" | "ANULOWANO" | "BLAD",
            "elementy": [
                {"sciezka": str, "typ": "PLIK"|"FOLDER", "rozmiar_b": int},
                ...
            ],
            "komunikat": str | None
        }

    UWAGA: callback jest wywoływany z wątku roboczego.
    """

    STATUS_OK = "OK"
    STATUS_ANULOWANO = "ANULOWANO"
    STATUS_BLAD = "BLAD"

    TYP_PLIK = "PLIK"
    TYP_FOLDER = "FOLDER"

    def __init__(self):
        self._czy_anulowano = False

    def zatrzymaj(self):
        """Metoda wywoływana przez przycisk Przerwij."""
        self._czy_anulowano = True

    @staticmethod
    def konwertuj_rozmiar(bajty: int) -> str:
        """Zamienia liczbę bajtów na czytelny zapis (np. 1.23 MB)."""
        rozmiar = float(bajty)
        for jednostka in ["B", "KB", "MB", "GB", "TB"]:
            if rozmiar < 1024.0:
                return f"{rozmiar:.2f} {jednostka}"
            rozmiar /= 1024.0
        return f"{rozmiar:.2f} PB"

    def skanuj_folder(self, sciezka_startowa: str, callback_zakonczenia):
        """Startuje skanowanie w osobnym wątku."""
        self._czy_anulowano = False
        watek = threading.Thread(
            target=self._skanuj_w_tle,
            args=(sciezka_startowa, callback_zakonczenia),
            daemon=True,
        )
        watek.start()

    def _skanuj_w_tle(self, sciezka_startowa: str, callback_zakonczenia):
        pliki: list[dict] = []
        rozmiary_folderow: dict[str, int] = {}
        liczba_pominietych = 0

        try:
            for katalog_biezacy, _podkatalogi, pliki_w_katalogu in os.walk(sciezka_startowa):
                if self._czy_anulowano:
                    callback_zakonczenia({
                        "status": self.STATUS_ANULOWANO,
                        "elementy": [],
                        "komunikat": "Skanowanie przerwane przez użytkownika.",
                    })
                    return

                rozmiar_biezacego_katalogu = 0

                for nazwa_pliku in pliki_w_katalogu:
                    sciezka_pliku = os.path.join(katalog_biezacy, nazwa_pliku)
                    try:
                        rozmiar_pliku = os.path.getsize(sciezka_pliku)
                    except OSError:
                        liczba_pominietych += 1
                        continue

                    pliki.append({
                        "sciezka": sciezka_pliku,
                        "typ": self.TYP_PLIK,
                        "rozmiar_b": int(rozmiar_pliku),
                    })
                    rozmiar_biezacego_katalogu += int(rozmiar_pliku)

                # Dodajemy rozmiar plików do wszystkich katalogów nadrzędnych (aż do katalogu startowego).
                temp_katalog = katalog_biezacy
                katalog_graniczny = os.path.dirname(sciezka_startowa.rstrip(os.sep))
                while temp_katalog and temp_katalog != katalog_graniczny:
                    rozmiary_folderow[temp_katalog] = rozmiary_folderow.get(temp_katalog, 0) + rozmiar_biezacego_katalogu

                    nastepny = os.path.dirname(temp_katalog)
                    if nastepny == temp_katalog:
                        break
                    temp_katalog = nastepny

        except Exception as e:
            callback_zakonczenia({
                "status": self.STATUS_BLAD,
                "elementy": [],
                "komunikat": f"Błąd skanowania: {e}",
            })
            return

        if self._czy_anulowano:
            callback_zakonczenia({
                "status": self.STATUS_ANULOWANO,
                "elementy": [],
                "komunikat": "Skanowanie przerwane przez użytkownika.",
            })
            return

        # Składamy listę elementów: pliki + foldery (rozmiary folderów to suma plików w poddrzewie).
        elementy: list[dict] = []
        elementy.extend(pliki)
        for sciezka_folderu, rozmiar_folderu in rozmiary_folderow.items():
            elementy.append({
                "sciezka": sciezka_folderu,
                "typ": self.TYP_FOLDER,
                "rozmiar_b": int(rozmiar_folderu),
            })

        # Jeżeli startujemy od wyznaczonego folderu, nie pokazujemy jego wagi jako pozycji na liście.
        sciezka_startowa_norm = os.path.normpath(sciezka_startowa)
        elementy = [
            e for e in elementy
            if os.path.normpath(str(e.get("sciezka", ""))) != sciezka_startowa_norm
        ]

        elementy.sort(key=lambda x: x["rozmiar_b"], reverse=True)
        top_75 = elementy[:75]

        komunikat = None
        if liczba_pominietych > 0:
            komunikat = f"Pominięto elementy bez dostępu: {liczba_pominietych}."

        callback_zakonczenia({
            "status": self.STATUS_OK,
            "elementy": top_75,
            "komunikat": komunikat,
        })