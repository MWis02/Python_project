import customtkinter as ctk
from tkinter import filedialog
from backend import AnalizatorPlikow


class Skaner_Folderow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- START: MAŁE OKNO ---
        self.title("Skaner Folderów")
        self.geometry("600x350")  # Nieco wyższe, żeby zmieścił się drugi przycisk
        ctk.set_appearance_mode("Dark")

        self.analizator = None  # Tu będziemy trzymać instancję backendu

        # --- 1. Góra ---
        self.frame_gora = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_gora.pack(fill="x", padx=20, pady=10)

        self.label_tytul = ctk.CTkLabel(self.frame_gora, text="Analizator Rozmiaru", font=("Arial", 20, "bold"))
        self.label_tytul.pack(side="left")

        self.btn_motyw = ctk.CTkButton(
            self.frame_gora, text="☀", width=40, font=("Arial", 20),
            fg_color="transparent", border_width=2, text_color=("orange", "yellow"),
            command=self.zmien_motyw
        )
        self.btn_motyw.pack(side="right")

        # --- 2. Środek ---
        self.frame_sterowanie = ctk.CTkFrame(self)
        self.frame_sterowanie.pack(pady=10, padx=20, fill="x")

        self.label_info = ctk.CTkLabel(self.frame_sterowanie, text="Wybierz folder do analizy:", font=("Arial", 14))
        self.label_info.pack(pady=5)

        self.frame_input = ctk.CTkFrame(self.frame_sterowanie, fg_color="transparent")
        self.frame_input.pack(pady=5)

        self.entry_sciezka = ctk.CTkEntry(self.frame_input, width=350, placeholder_text="Ścieżka...")
        self.entry_sciezka.pack(side="left", padx=5)

        self.btn_wybierz = ctk.CTkButton(self.frame_input, text="📁", width=40, command=self.wybierz_folder_z_dysku)
        self.btn_wybierz.pack(side="left")

        # Przycisk START
        self.btn_skanuj = ctk.CTkButton(
            self.frame_sterowanie, text="URUCHOM SKANOWANIE", font=("Arial", 14, "bold"),
            fg_color="green", hover_color="darkgreen", height=40,
            command=self.rozpocznij_skanowanie
        )
        self.btn_skanuj.pack(pady=(15, 5))  # padding od dołu mniejszy, bo dojdzie przycisk STOP

        # Przycisk STOP (na początku ukryty - nie pakujemy go)
        self.btn_przerwij = ctk.CTkButton(
            self.frame_sterowanie, text="PRZERWIJ SKANOWANIE 🛑", font=("Arial", 12, "bold"),
            fg_color="red", hover_color="darkred", height=30,
            command=self.akcja_przerwij
        )
        # UWAGA: Nie ma .pack() tutaj!

        self.label_status = ctk.CTkLabel(self.frame_sterowanie, text="Gotowy do pracy", text_color="gray")
        self.label_status.pack(pady=(5, 10))

        # --- 3. Dół (Wyniki) ---
        self.lista_wynikow = ctk.CTkScrollableFrame(self, label_text="Największe pliki i foldery")

    # --- FUNKCJE ---

    def wybierz_folder_z_dysku(self):
        sciezka = filedialog.askdirectory()
        if sciezka:
            self.entry_sciezka.delete(0, "end")
            self.entry_sciezka.insert(0, sciezka)

    def zmien_motyw(self):
        if ctk.get_appearance_mode() == "Dark":
            ctk.set_appearance_mode("Light")
            self.btn_motyw.configure(text="☾", text_color="blue")
        else:
            ctk.set_appearance_mode("Dark")
            self.btn_motyw.configure(text="☀", text_color="yellow")

    def rozpocznij_skanowanie(self):
        sciezka = self.entry_sciezka.get()
        if not sciezka:
            self.label_status.configure(text="Błąd: Wybierz folder!", text_color="red")
            return

        # Reset widoku
        self.geometry("600x350")
        self.lista_wynikow.pack_forget()  # Ukryj listę
        for widget in self.lista_wynikow.winfo_children():
            widget.destroy()

        # UI w trybie pracy
        self.btn_skanuj.configure(state="disabled", text="SKANOWANIE...")

        # POKAZUJEMY PRZYCISK STOP
        self.btn_przerwij.pack(pady=5)

        self.label_status.configure(text=f"Analizuję: {sciezka}...", text_color="cyan")

        # Tworzymy instancję i przypisujemy do self, żeby mieć do niej dostęp w innej funkcji
        self.analizator = AnalizatorPlikow()
        self.analizator.skanuj_folder(sciezka, self.zakonczono_skanowanie)

    def akcja_przerwij(self):
        """Funkcja podpięta pod czerwony przycisk"""
        if self.analizator:
            self.analizator.zatrzymaj()
            self.label_status.configure(text="Zatrzymywanie...", text_color="orange")
            # Przycisk stop blokujemy, żeby nie klikać go 10 razy
            self.btn_przerwij.configure(state="disabled")

    def zakonczono_skanowanie(self, wyniki):
        # Przywracanie UI
        self.btn_skanuj.configure(state="normal", text="URUCHOM SKANOWANIE")

        # UKRYWAMY PRZYCISK STOP
        self.btn_przerwij.pack_forget()
        self.btn_przerwij.configure(state="normal")  # Odblokowujemy go na przyszłość

        # Obsługa przerwania (backend zwraca None)
        if wyniki is None:
            self.label_status.configure(text="Skanowanie przerwane!", text_color="red")
            return

        self.label_status.configure(text="Skanowanie zakończone!", text_color="green")

        # Pokaż wyniki
        self.geometry("700x600")
        self.lista_wynikow.pack(fill="both", expand=True, padx=20, pady=20)

        if not wyniki:
            lbl = ctk.CTkLabel(self.lista_wynikow, text="Brak wyników.")
            lbl.pack(pady=10)
            return

        for wynik_tekst in wyniki:
            wiersz = ctk.CTkFrame(self.lista_wynikow)
            wiersz.pack(fill="x", pady=5, padx=5)

            try:
                lewo, prawo = wynik_tekst.split("|", 1)
            except ValueError:
                lewo, prawo = "???", wynik_tekst

            lbl_rozmiar = ctk.CTkLabel(wiersz, text=lewo.strip(), font=("Consolas", 14, "bold"), width=120, anchor="w")
            lbl_rozmiar.pack(side="left", padx=10, pady=5)

            lbl_nazwa = ctk.CTkLabel(wiersz, text=prawo.strip(), font=("Arial", 13), anchor="w")
            lbl_nazwa.pack(side="left", fill="x", expand=True, padx=5)