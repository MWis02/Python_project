import os
import subprocess
import tkinter.messagebox as messagebox
import tkinter.font as tkfont

import customtkinter as ctk
from tkinter import filedialog

from backend import AnalizatorPlikow

try:
    # Preferowane: przeniesienie do Kosza (Windows/macOS/Linux)
    from send2trash import send2trash as _funkcja_kosz  # type: ignore
except Exception:
    _funkcja_kosz = None


class Skaner_Folderow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Skaner Folderów")
        self.geometry("600x350")
        ctk.set_appearance_mode("Dark")

        self.analizator: AnalizatorPlikow | None = None
        self.ostatnie_elementy: list[dict] = []

        # Filtr wyników: "Wszystko" | "Pliki" | "Foldery"
        self.filtr_typu = ctk.StringVar(value="Wszystko")
        self.pasek_filtrow = None

        # Paginacja
        self.elementow_na_strone = 15
        self.liczba_stron = 5
        self.biezaca_strona = 1  # 1..liczba_stron

        # Tooltip (okienko pomocnicze)
        self._tooltip_okno = None
        self._tooltip_etykieta = None

        self.ramka_nawigacji = None
        self.przycisk_poprzednia = None
        self.przycisk_nastepna = None
        self.etykieta_strona = None

        # --- GÓRA ---
        self.ramka_gora = ctk.CTkFrame(self, fg_color="transparent")
        self.ramka_gora.pack(fill="x", padx=20, pady=10)

        self.etykieta_tytul = ctk.CTkLabel(self.ramka_gora, text="Analizator rozmiaru", font=("Arial", 20, "bold"))
        self.etykieta_tytul.pack(side="left")

        self.przycisk_motyw = ctk.CTkButton(
            self.ramka_gora,
            text="☀",
            width=40,
            font=("Arial", 20),
            fg_color="transparent",
            border_width=2,
            text_color=("orange", "yellow"),
            command=self.zmien_motyw,
        )
        self.przycisk_motyw.pack(side="right")

        # --- ŚRODEK (STEROWANIE) ---
        self.ramka_sterowanie = ctk.CTkFrame(self)
        self.ramka_sterowanie.pack(pady=10, padx=20, fill="x")

        self.etykieta_info = ctk.CTkLabel(self.ramka_sterowanie, text="Wybierz folder do analizy:", font=("Arial", 14))
        self.etykieta_info.pack(pady=5)

        self.ramka_sciezka = ctk.CTkFrame(self.ramka_sterowanie, fg_color="transparent")
        self.ramka_sciezka.pack(pady=5)

        self.wejscie_sciezka = ctk.CTkEntry(self.ramka_sciezka, width=350, placeholder_text="Ścieżka...")
        self.wejscie_sciezka.pack(side="left", padx=5)

        self.przycisk_wybierz = ctk.CTkButton(self.ramka_sciezka, text="📁", width=40, command=self.wybierz_folder)
        self.przycisk_wybierz.pack(side="left")

        self.przycisk_skanuj = ctk.CTkButton(
            self.ramka_sterowanie,
            text="URUCHOM SKANOWANIE",
            font=("Arial", 14, "bold"),
            fg_color="green",
            hover_color="darkgreen",
            height=40,
            command=self.rozpocznij_skanowanie,
        )
        self.przycisk_skanuj.pack(pady=(15, 5))

        self.przycisk_przerwij = ctk.CTkButton(
            self.ramka_sterowanie,
            text="PRZERWIJ SKANOWANIE 🛑",
            font=("Arial", 12, "bold"),
            fg_color="red",
            hover_color="darkred",
            height=30,
            command=self.przerwij_skanowanie,
        )
        # nie pakujemy na start

        self.etykieta_status = ctk.CTkLabel(self.ramka_sterowanie, text="Gotowy do pracy", text_color="gray")
        self.etykieta_status.pack(pady=(5, 10))

        # --- DÓŁ (WYNIKI) ---
        # Kontener na wyniki i nawigację (żeby nawigacja była zawsze widoczna)
        self.ramka_wynikow_kontener = ctk.CTkFrame(self, fg_color="transparent")
        self.ramka_lista_wynikow = ctk.CTkFrame(self.ramka_wynikow_kontener, fg_color="transparent")
        self.lista_wynikow = ctk.CTkScrollableFrame(self.ramka_lista_wynikow, label_text="Największe pliki i foldery")

    # --- TOOLTIP ---

    def _pokaz_tooltip(self, tekst: str, widget):
        if not tekst:
            return
        try:
            if self._tooltip_okno is None or not self._tooltip_okno.winfo_exists():
                self._tooltip_okno = ctk.CTkToplevel(self)
                self._tooltip_okno.overrideredirect(True)
                self._tooltip_okno.attributes("-topmost", True)
                self._tooltip_okno.configure(fg_color=("#ffffff", "#222222"))

                self._tooltip_etykieta = ctk.CTkLabel(
                    self._tooltip_okno,
                    text="",
                    font=("Arial", 12),
                    justify="left",
                    padx=10,
                    pady=6,
                    wraplength=700,
                )
                self._tooltip_etykieta.pack()

            if self._tooltip_etykieta is not None:
                self._tooltip_etykieta.configure(text=tekst)

            # Pozycjonowanie przy kursorem
            x = self.winfo_pointerx() + 12
            y = self.winfo_pointery() + 16
            self._tooltip_okno.geometry(f"+{x}+{y}")
            self._tooltip_okno.deiconify()
        except Exception:
            pass

    def _ukryj_tooltip(self):
        try:
            if self._tooltip_okno is not None and self._tooltip_okno.winfo_exists():
                self._tooltip_okno.withdraw()
        except Exception:
            pass

    # --- POMOCNICZE (SYSTEM/OS) ---

    @staticmethod
    def _otworz_w_eksploratorze(sciezka: str, typ: str):
        """Windows: dla pliku otwórz folder nadrzędny, dla folderu otwórz ten folder."""
        try:
            if not sciezka:
                return

            sciezka = os.path.abspath(os.path.normpath(sciezka))

            if not os.path.exists(sciezka):
                messagebox.showerror("Błąd", f"Ścieżka nie istnieje:\n{sciezka}")
                return

            if typ == AnalizatorPlikow.TYP_PLIK:
                folder_nadrzedny = os.path.dirname(sciezka)
                subprocess.Popen(["explorer.exe", folder_nadrzedny])

            else:
                # Folder: otwieramy dokładnie ten folder (nie nadrzędny)
                subprocess.Popen(["explorer.exe", sciezka])
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć:\n{sciezka}\n\n{e}")

    @staticmethod
    def _normalizuj_sciezke(sciezka: str) -> str:
        r"""Normalizuje ścieżkę do postaci czytelnej i stabilnej.

        Cel: trzymać w UI i komunikatach postać klasyczną (C:\... lub \\server\share\...).
        """
        if not sciezka:
            return ""

        s = str(sciezka).strip().strip('"')

        # Obsługa Windows extended-length paths
        # \\?\UNC\server\share\...  -> \\server\share\...
        if s.startswith("\\\\?\\UNC\\"):
            s = "\\\\" + s[len("\\\\?\\UNC\\"):]
        # \\?\C:\... -> C:\...
        elif s.startswith("\\\\?\\"):
            s = s[len("\\\\?\\"):]
        # \\.\C:\... -> C:\...
        elif s.startswith("\\\\.\\"):
            s = s[len("\\\\.\\"):]

        return os.path.abspath(os.path.normpath(s))

    @staticmethod
    def _wariant_dluga_sciezka_windows(sciezka: str) -> str:
        r"""Zwraca wersję ścieżki z prefiksem \\?\ (dla bardzo długich ścieżek na Windows)."""
        s = Skaner_Folderow._normalizuj_sciezke(sciezka)
        if not s:
            return ""
        # UNC
        if s.startswith("\\\\"):
            return "\\\\?\\UNC\\" + s.lstrip("\\")
        return "\\\\?\\" + s

    @staticmethod
    def _czy_folder_chroniony(sciezka: str) -> bool:
        """Zabezpiecza przed usuwaniem typowych katalogów użytkownika (Desktop, Dokumenty itd.)."""
        if not sciezka:
            return False
        try:
            home = os.path.abspath(os.path.expanduser("~"))
            # polskie i angielskie nazwy
            nazwy = [
                "Desktop",
                "Pulpit",
                "Documents",
                "Dokumenty",
                "Downloads",
                "Pobrane",
                "Pictures",
                "Obrazy",
                "Music",
                "Muzyka",
                "Videos",
                "Wideo",
            ]
            sc = os.path.abspath(os.path.normpath(sciezka))
            sc_norm = os.path.normcase(sc)
            for n in nazwy:
                kand = os.path.normcase(os.path.join(home, n))
                if sc_norm == kand or sc_norm.startswith(cand_sep := kand + os.sep):
                    return True
            # sam katalog domowy też blokujemy
            if sc_norm == os.path.normcase(home):
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _sprobuj_usunac(sciezka: str, typ: str) -> tuple[bool, str | None]:
        """Usuwanie elementu.

        Preferowane: przeniesienie do Kosza (jeśli dostępne send2trash).
        Fallback: trwałe usunięcie.
        """
        try:
            sciezka_norm = Skaner_Folderow._normalizuj_sciezke(sciezka)
            if not sciezka_norm:
                return False, "Pusta ścieżka."

            # Blokada: katalogi użytkownika (Pulpit/Dokumenty/Pobrane/Obrazy/Muzyka/Wideo) i ich zawartość
            if Skaner_Folderow._czy_folder_chroniony(sciezka_norm):
                return False, "Nie można usuwać plików ani folderów z chronionych katalogów użytkownika (np. Pulpit, Dokumenty, Pobrane)."

            # Dla bardzo długich ścieżek Windows czasem potrzebuje prefiksu \\?\
            sciezka_dluga = Skaner_Folderow._wariant_dluga_sciezka_windows(sciezka_norm)

            # Sprawdzenie istnienia (najpierw normalna ścieżka, potem długa)
            if not os.path.exists(sciezka_norm) and (not sciezka_dluga or not os.path.exists(sciezka_dluga)):
                return False, "Nie można odnaleźć określonej ścieżki."

            if callable(_funkcja_kosz):
                try:
                    _funkcja_kosz(sciezka_norm)
                    return True, None
                except OSError:
                    # Retry: wersja długiej ścieżki (Windows)
                    if sciezka_dluga:
                        _funkcja_kosz(sciezka_dluga)
                        return True, None
                    raise

            # Fallback (bez kosza) – trwałe usunięcie
            if typ == AnalizatorPlikow.TYP_PLIK:
                try:
                    os.remove(sciezka_norm)
                except OSError:
                    if sciezka_dluga:
                        os.remove(sciezka_dluga)
                    else:
                        raise
                return True, None

            # folder + cała zawartość
            import shutil

            try:
                shutil.rmtree(sciezka_norm)
            except OSError:
                if sciezka_dluga:
                    shutil.rmtree(sciezka_dluga)
                else:
                    raise
            return True, None
        except OSError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def _nazwa_z_sciezki(sciezka: str) -> str:
        nazwa = os.path.basename(sciezka)
        return nazwa if nazwa else sciezka

    # --- UI: akcje ---

    def wybierz_folder(self):
        sciezka = filedialog.askdirectory()
        if sciezka:
            self.wejscie_sciezka.delete(0, "end")
            self.wejscie_sciezka.insert(0, sciezka)

    def zmien_motyw(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
            self.przycisk_motyw.configure(text="☾", text_color="blue")
        else:
            ctk.set_appearance_mode("Dark")
            self.przycisk_motyw.configure(text="☀", text_color="yellow")

        # Po zmianie motywu odśwież kolory wierszy wyników
        if self.ostatnie_elementy:
            self._wyrenderuj_biezaca_strone()

    def rozpocznij_skanowanie(self):
        sciezka = self.wejscie_sciezka.get().strip()
        if not sciezka:
            self.etykieta_status.configure(text="Błąd: wybierz folder!", text_color="red")
            return

        self._wyczysc_wyniki_i_zwin_okno()

        self.przycisk_skanuj.configure(state="disabled", text="SKANOWANIE...")
        self.przycisk_przerwij.pack(pady=5)
        self.etykieta_status.configure(text=f"Analizuję: {sciezka}...", text_color="cyan")

        self.analizator = AnalizatorPlikow()
        self.analizator.skanuj_folder(sciezka, self._callback_z_backendu)

    def przerwij_skanowanie(self):
        if self.analizator:
            self.analizator.zatrzymaj()
            self.etykieta_status.configure(text="Zatrzymywanie...", text_color="orange")
            self.przycisk_przerwij.configure(state="disabled")

    # --- UI: renderowanie ---

    def _wyczysc_wyniki_i_zwin_okno(self):
        self.geometry("600x350")
        # Schowaj kontener wyników
        self.ramka_wynikow_kontener.pack_forget()
        for widget in self.lista_wynikow.winfo_children():
            widget.destroy()
        self.ostatnie_elementy = []

        # Schowaj pasek filtrów, jeśli był
        if self.pasek_filtrow is not None:
            try:
                self.pasek_filtrow.destroy()
            except Exception:
                pass
            self.pasek_filtrow = None

        # Reset paginacji
        self.biezaca_strona = 1
        if self.ramka_nawigacji is not None:
            try:
                self.ramka_nawigacji.destroy()
            except Exception:
                pass
            self.ramka_nawigacji = None

    def _callback_z_backendu(self, wynik: dict):
        # Backend woła w wątku roboczym -> przerzucamy na wątek GUI
        self.after(0, lambda: self._obsluz_wynik_skanowania(wynik))

    def _obsluz_wynik_skanowania(self, wynik: dict):
        self.przycisk_skanuj.configure(state="normal", text="URUCHOM SKANOWANIE")
        self.przycisk_przerwij.pack_forget()
        self.przycisk_przerwij.configure(state="normal")

        status = wynik.get("status")
        komunikat = wynik.get("komunikat")
        elementy = wynik.get("elementy") or []

        if status == AnalizatorPlikow.STATUS_ANULOWANO:
            self.etykieta_status.configure(text="Skanowanie przerwane!", text_color="red")
            return

        if status == AnalizatorPlikow.STATUS_BLAD:
            self.etykieta_status.configure(text="Błąd skanowania.", text_color="red")
            if komunikat:
                messagebox.showerror("Błąd", komunikat)
            return

        # OK
        self.etykieta_status.configure(text="Skanowanie zakończone!", text_color="green")
        if komunikat:
            # nie spamujemy oknami, tylko pokazujemy w statusie
            self.etykieta_status.configure(text=f"Skanowanie zakończone. {komunikat}", text_color="green")

        self.ostatnie_elementy = elementy

        # Reset na pierwszą stronę po nowym skanie
        self.biezaca_strona = 1
        self.filtr_typu.set("Wszystko")

        self.geometry("750x620")
        self._zapewnij_pasek_filtrow()
        # Wyniki + nawigacja w stałym kontenerze
        if not self.ramka_wynikow_kontener.winfo_ismapped():
            self.ramka_wynikow_kontener.pack(fill="both", expand=True, padx=20, pady=20)
            self.ramka_lista_wynikow.pack(fill="both", expand=True)
            self.lista_wynikow.pack(fill="both", expand=True)

        if not elementy:
            et = ctk.CTkLabel(self.lista_wynikow, text="Brak wyników.")
            et.pack(pady=10)
            return

        self._wyrenderuj_biezaca_strone()

    def _elementy_po_filtrze(self) -> list[dict]:
        """Zwraca listę elementów po zastosowaniu filtra typu."""
        if not self.ostatnie_elementy:
            return []
        wybor = self.filtr_typu.get()
        if wybor == "Pliki":
            return [e for e in self.ostatnie_elementy if e.get("typ") == AnalizatorPlikow.TYP_PLIK]
        if wybor == "Foldery":
            return [e for e in self.ostatnie_elementy if e.get("typ") == AnalizatorPlikow.TYP_FOLDER]
        return list(self.ostatnie_elementy)

    def _zapewnij_pasek_filtrow(self):
        """Tworzy pasek filtrów nad listą wyników (jeśli jeszcze nie istnieje)."""
        if self.pasek_filtrow is not None:
            return

        self.pasek_filtrow = ctk.CTkFrame(self, fg_color="transparent")
        # Nad listą wyników (po sterowaniu), więc wpinamy przed `lista_wynikow`
        self.pasek_filtrow.pack(fill="x", padx=20, pady=(0, 8))

        et = ctk.CTkLabel(self.pasek_filtrow, text="Filtr:", font=("Arial", 12, "bold"))
        et.pack(side="left", padx=(0, 10))

        def ustaw_filtr(wartosc: str):
            self.filtr_typu.set(wartosc)
            self.biezaca_strona = 1
            self._wyrenderuj_biezaca_strone()
            self._przewin_liste_na_gore()

        # CustomTkinter ma CTkSegmentedButton (jeśli wersja wspiera). Jeśli nie, łatwo podmienić na 3 CTkRadioButton.
        self.segment_filtr = ctk.CTkSegmentedButton(
            self.pasek_filtrow,
            values=["Wszystko", "Pliki", "Foldery"],
            command=ustaw_filtr,
            variable=self.filtr_typu,
        )
        self.segment_filtr.pack(side="left")

    def _maksymalna_strona_dla_danych(self) -> int:
        """Zwraca ile stron realnie można pokazać dla danych (max 5)."""
        elementy = self._elementy_po_filtrze()
        if not elementy:
            return 1
        strony = (len(elementy) + self.elementow_na_strone - 1) // self.elementow_na_strone
        return max(1, min(self.liczba_stron, strony))

    def _przewin_liste_na_gore(self):
        """Przewija CTkScrollableFrame na samą górę."""
        try:
            # CustomTkinter: CTkScrollableFrame trzyma Canvas w polu `_parent_canvas`
            canvas = getattr(self.lista_wynikow, "_parent_canvas", None)
            if canvas is not None:
                canvas.yview_moveto(0)
        except Exception:
            pass

    def _wyrenderuj_biezaca_strone(self):
        """Czyści listę wyników i rysuje tylko elementy z bieżącej strony + nawigację."""
        # Wyczyść tylko elementy wyników (bez zwijania całego layoutu)
        for widget in self.lista_wynikow.winfo_children():
            widget.destroy()

        # Po zmianie strony chcemy zawsze zacząć od góry listy
        self._przewin_liste_na_gore()

        elementy = self._elementy_po_filtrze()
        max_strona = self._maksymalna_strona_dla_danych()
        if self.biezaca_strona < 1:
            self.biezaca_strona = 1
        if self.biezaca_strona > max_strona:
            self.biezaca_strona = max_strona

        start = (self.biezaca_strona - 1) * self.elementow_na_strone
        koniec = start + self.elementow_na_strone
        elementy_strony = elementy[start:koniec]

        if not elementy_strony:
            et = ctk.CTkLabel(self.lista_wynikow, text="Brak elementów na tej stronie.")
            et.pack(pady=10)
        else:
            for idx_lokalny, element in enumerate(elementy_strony):
                # Indeks do kolorowania pasków: liczony w obrębie przefiltrowanej listy
                indeks_w_liscie = start + idx_lokalny
                self._dodaj_wiersz_wyniku(indeks=indeks_w_liscie, element=element)

        self._pokaz_nawigacje(max_strona=max_strona)

    def _pokaz_nawigacje(self, max_strona: int):
        """Dodaje pod listą przyciski: Poprzednia / licznik / Następna."""
        if self.ramka_nawigacji is None:
            # Zawsze na dole kontenera wyników, pod listą przewijalną
            self.ramka_nawigacji = ctk.CTkFrame(self.ramka_wynikow_kontener, fg_color="transparent")
            self.ramka_nawigacji.pack(fill="x", pady=(10, 0))

            self.przycisk_poprzednia = ctk.CTkButton(
                self.ramka_nawigacji,
                text="⟵ Poprzednia",
                width=140,
                command=self._poprzednia_strona,
            )
            self.przycisk_poprzednia.pack(side="left")

            self.etykieta_strona = ctk.CTkLabel(self.ramka_nawigacji, text="", font=("Arial", 12, "bold"))
            self.etykieta_strona.pack(side="left", expand=True)

            self.przycisk_nastepna = ctk.CTkButton(
                self.ramka_nawigacji,
                text="Następna ⟶",
                width=140,
                command=self._nastepna_strona,
            )
            self.przycisk_nastepna.pack(side="right")

        # Aktualizacje stanu
        if self.etykieta_strona is not None:
            self.etykieta_strona.configure(text=f"Strona {self.biezaca_strona} / {max_strona}")

        if self.przycisk_poprzednia is not None:
            self.przycisk_poprzednia.configure(state="normal" if self.biezaca_strona > 1 else "disabled")

        if self.przycisk_nastepna is not None:
            self.przycisk_nastepna.configure(state="normal" if self.biezaca_strona < max_strona else "disabled")

    def _poprzednia_strona(self):
        self.biezaca_strona -= 1
        self._wyrenderuj_biezaca_strone()

    def _nastepna_strona(self):
        self.biezaca_strona += 1
        self._wyrenderuj_biezaca_strone()

    def _kolory_wiersza(self, indeks: int) -> tuple[str, str, str, str]:
        """Zwraca (tlo_normalne, tlo_hover, kolor_separatora, kolor_obramowania)."""
        appearance = ctk.get_appearance_mode()
        if appearance == "Dark":
            tlo_parzyste = "#1f1f1f"
            tlo_nieparzyste = "#2b2b2b"
            tlo_hover = "#333333"
            separator = "#444444"
            obramowanie = "#3a3a3a"
        else:
            tlo_parzyste = "#ffffff"
            tlo_nieparzyste = "#f5f5f5"
            tlo_hover = "#e8e8e8"
            separator = "#d9d9d9"
            obramowanie = "#dddddd"

        tlo = tlo_parzyste if indeks % 2 == 0 else tlo_nieparzyste
        return tlo, tlo_hover, separator, obramowanie

    @staticmethod
    def _skroc_z_wielokropkiem(tekst: str, max_px: int, font_obj: tkfont.Font) -> str:
        """Ucina tekst do szerokości `max_px` dodając wielokropek."""
        if max_px <= 0:
            return ""
        if font_obj.measure(tekst) <= max_px:
            return tekst

        wielokropek = "..."
        if font_obj.measure(wielokropek) > max_px:
            return ""

        # Binary search po długości
        lo, hi = 0, len(tekst)
        while lo < hi:
            mid = (lo + hi) // 2
            kandydat = tekst[:mid] + wielokropek
            if font_obj.measure(kandydat) <= max_px:
                lo = mid + 1
            else:
                hi = mid

        mid = max(0, lo - 1)
        return tekst[:mid] + wielokropek

    def _dodaj_wiersz_wyniku(self, indeks: int, element: dict):
        sciezka = element.get("sciezka", "")
        typ = element.get("typ", "")
        rozmiar_b = int(element.get("rozmiar_b", 0) or 0)

        sciezka_norm = self._normalizuj_sciezke(sciezka)

        pelna_nazwa = self._nazwa_z_sciezki(sciezka)
        rozmiar_tekst = AnalizatorPlikow.konwertuj_rozmiar(rozmiar_b)
        typ_tekst = "Plik" if typ == AnalizatorPlikow.TYP_PLIK else "Folder" if typ == AnalizatorPlikow.TYP_FOLDER else str(typ)

        tlo, tlo_hover, kolor_separatora, kolor_obramowania = self._kolory_wiersza(indeks)

        wiersz = ctk.CTkFrame(
            self.lista_wynikow,
            fg_color=tlo,
            corner_radius=8,
            border_width=1,
            border_color=kolor_obramowania,
        )
        wiersz.pack(fill="x", padx=6, pady=(6, 0))

        # Responsywny układ: grid zamiast pack (nazwa nie zmniejszy przycisków)
        wiersz.grid_columnconfigure(0, weight=1)   # nazwa - zajmuje resztę
        wiersz.grid_columnconfigure(1, weight=0)   # typ
        wiersz.grid_columnconfigure(2, weight=0)   # rozmiar
        wiersz.grid_columnconfigure(3, weight=0)   # usuń

        # Kolumna: nazwa
        font_nazwa = ("Arial", 13)
        etykieta_nazwa = ctk.CTkLabel(wiersz, text=pelna_nazwa, font=font_nazwa, anchor="w")
        etykieta_nazwa.grid(row=0, column=0, sticky="ew", padx=(12, 6), pady=8)

        # Kolumna: typ (przed przyciskiem Usuń)
        etykieta_typ = ctk.CTkLabel(wiersz, text=typ_tekst, font=("Arial", 12), width=80, anchor="center")
        etykieta_typ.grid(row=0, column=1, sticky="e", padx=(6, 6), pady=8)

        # Kolumna: rozmiar
        etykieta_rozmiar = ctk.CTkLabel(wiersz, text=rozmiar_tekst, font=("Consolas", 13, "bold"), width=140, anchor="e")
        etykieta_rozmiar.grid(row=0, column=2, sticky="e", padx=(6, 8), pady=8)

        # Przycisk: Usuń
        def usun():
            if not sciezka_norm:
                return

            czy_kosz = callable(_funkcja_kosz)
            dopisek_kosz = "Element zostanie przeniesiony do Kosza." if czy_kosz else "Element zostanie usunięty trwale (brak Kosza)."

            if typ == AnalizatorPlikow.TYP_PLIK:
                tresc = (
                    "Czy na pewno chcesz usunąć ten plik?\n\n"
                    "Plik zostanie bezpowrotnie usunięty.\n"
                    "Jeśli nie jesteś pewny decyzji, lepiej otwórz lokalizację i sprawdź plik.\n\n"
                    f"{dopisek_kosz}\n\n"
                    f"{sciezka_norm}"
                )
            else:
                tresc = (
                    "Czy na pewno chcesz usunąć ten folder?\n\n"
                    "UWAGA: cała zawartość tego folderu (podfoldery i pliki) zostanie bezpowrotnie usunięta.\n"
                    "Jeśli nie jesteś pewny decyzji, lepiej otwórz folder i sprawdź co w nim jest.\n\n"
                    f"{dopisek_kosz}\n\n"
                    f"{sciezka_norm}"
                )

            czy_tak = messagebox.askyesno("Potwierdzenie usunięcia", tresc)
            if not czy_tak:
                return

            ok, blad = self._sprobuj_usunac(sciezka_norm, typ)
            if not ok:
                messagebox.showerror(
                    "Nie udało się usunąć",
                    f"Nie udało się usunąć:\n{sciezka_norm}\n\n{blad}",
                )
                return

            # Usuń wizualnie wiersz
            try:
                wiersz.destroy()
            except Exception:
                pass

        przycisk_usun = ctk.CTkButton(
            wiersz,
            text="Usuń",
            width=70,
            fg_color="#b00020",
            hover_color="#7f0015",
            command=usun,
        )
        przycisk_usun.grid(row=0, column=3, sticky="e", padx=(0, 12), pady=8)

        # --- Skracanie nazwy z wielokropkiem (responsywnie) ---
        font_pomiar = tkfont.Font(family="Arial", size=13)

        def odswiez_uciecie(_event=None):
            try:
                # Ustal ile miejsca mamy dla kolumny nazwy: szerokość wiersza - (typ + rozmiar + przycisk + marginesy)
                szer_wiersza = max(0, int(wiersz.winfo_width()))
                # Szerokości widgetów po prawej (już mają stałe width, ale realna szerokość zależy od DPI)
                zajete = int(etykieta_typ.winfo_width()) + int(etykieta_rozmiar.winfo_width()) + int(przycisk_usun.winfo_width())
                # Marginesy/paddingi: lewy 12, między 6, 6, 8, 12 oraz wewnętrzne ≈ 40
                margines = 12 + 6 + 6 + 8 + 12 + 24
                max_px = max(0, szer_wiersza - zajete - margines)
                etykieta_nazwa.configure(text=self._skroc_z_wielokropkiem(pelna_nazwa, max_px, font_pomiar))
            except Exception:
                pass

        # Po utworzeniu i przy zmianie rozmiaru
        wiersz.bind("<Configure>", odswiez_uciecie)
        self.after(50, odswiez_uciecie)

        # Klik: otwórz w explorer
        def otworz(_event=None):
            if sciezka_norm:
                self._otworz_w_eksploratorze(sciezka_norm, typ)

        # Hover
        def on_enter(_event=None):
            try:
                wiersz.configure(fg_color=tlo_hover)
            except Exception:
                pass

        def on_leave(_event=None):
            try:
                wiersz.configure(fg_color=tlo)
            except Exception:
                pass

        for widget in (wiersz, etykieta_nazwa, etykieta_rozmiar, etykieta_typ):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            widget.bind("<Button-1>", otworz)

        # Tooltip: pokazuj pełną nazwę po najechaniu (tylko jeśli została ucięta)
        def tooltip_enter(_event=None):
            try:
                wyswietlany = etykieta_nazwa.cget("text")
                if wyswietlany != pelna_nazwa:
                    self._pokaz_tooltip(pelna_nazwa, etykieta_nazwa)
            except Exception:
                pass

        def tooltip_leave(_event=None):
            self._ukryj_tooltip()

        etykieta_nazwa.bind("<Enter>", tooltip_enter, add=True)
        etykieta_nazwa.bind("<Leave>", tooltip_leave, add=True)

        # Separator pod wierszem
        separator = ctk.CTkFrame(self.lista_wynikow, height=1, fg_color=kolor_separatora)
        separator.pack(fill="x", padx=12, pady=(0, 6))