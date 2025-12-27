import os
import threading


class AnalizatorPlikow:
    def __init__(self):
        self.wyniki = []
        self.czy_anulowano = False  # Flaga sterująca

    def zatrzymaj(self):
        """Metoda wywoływana przez przycisk Przerwij"""
        self.czy_anulowano = True

    def konwertuj_rozmiar(self, bajty):
        for jednostka in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bajty < 1024.0:
                return f"{bajty:.2f} {jednostka}"
            bajty /= 1024.0
        return f"{bajty:.2f} PB"

    def skanuj_folder(self, sciezka_startowa, callback_koniec):
        self.czy_anulowano = False  # Reset flagi przed startem
        watek = threading.Thread(target=self._logika_skanowania, args=(sciezka_startowa, callback_koniec))
        watek.start()

    def _logika_skanowania(self, sciezka_startowa, callback_koniec):
        pliki_lista = []
        foldery_mapa = {}

        try:
            for root, dirs, files in os.walk(sciezka_startowa):
                # --- SPRAWDZANIE CZY PRZERWAĆ ---
                if self.czy_anulowano:
                    print("Skanowanie przerwane przez użytkownika.")
                    callback_koniec(None)  # None oznacza przerwanie
                    return
                # --------------------------------

                rozmiar_folderu_lokalny = 0

                for plik in files:
                    sciezka_pelna = os.path.join(root, plik)
                    try:
                        rozmiar = os.path.getsize(sciezka_pelna)
                        pliki_lista.append({'path': sciezka_pelna, 'size': rozmiar, 'type': 'PLIK'})
                        rozmiar_folderu_lokalny += rozmiar
                    except OSError:
                        pass

                temp_path = root
                while temp_path and temp_path != os.path.dirname(sciezka_startowa):
                    foldery_mapa[temp_path] = foldery_mapa.get(temp_path, 0) + rozmiar_folderu_lokalny
                    if temp_path == os.path.dirname(temp_path):
                        break
                    temp_path = os.path.dirname(temp_path)

        except Exception as e:
            print(f"Błąd: {e}")
            callback_koniec([])
            return

        # Jeśli przerwano w trakcie obliczeń końcowych
        if self.czy_anulowano:
            callback_koniec(None)
            return

        # Logika sortowania i filtrowania (bez zmian)
        pliki_lista.sort(key=lambda x: x['size'], reverse=True)
        top_pliki = pliki_lista[:20]

        finalne_elementy = []
        for p in top_pliki:
            finalne_elementy.append(p)

        for folder_path, folder_size in foldery_mapa.items():
            czysty_rozmiar = folder_size
            for gigant in top_pliki:
                if gigant['path'].startswith(folder_path):
                    czysty_rozmiar -= gigant['size']

            if czysty_rozmiar > 0:
                finalne_elementy.append({
                    'path': folder_path,
                    'size': czysty_rozmiar,
                    'type': 'FOLDER (z drobnicą)'
                })

        finalne_elementy.sort(key=lambda x: x['size'], reverse=True)
        top_10 = finalne_elementy[:10]

        wyniki_tekstowe = []
        for pozycja in top_10:
            nazwa = os.path.basename(pozycja['path'])
            if not nazwa: nazwa = pozycja['path']
            rozmiar_str = self.konwertuj_rozmiar(pozycja['size'])
            ikona = "📄" if pozycja['type'] == 'PLIK' else "📂"
            wyniki_tekstowe.append(f"{ikona} {rozmiar_str} | {nazwa}")

        callback_koniec(wyniki_tekstowe)