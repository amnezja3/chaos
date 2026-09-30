# 146.4.2 — katalog Deep Scannerów

Status: implementacja lokalna gotowa do wdrożenia; odbiór wyglądu i odsłuchu
w grze oczekuje. 146.4.1 ma końcowy PASS autora z 30 IX 2026.

## Zawartość pakietu

| Wzór | Prezentacja | SFX |
|---|---|---|
| regular | Dotychczasowy przesuwający się pas; akcent autora | sweep, ping |
| pulse | Rozchodzące się i wygasające pierścienie od wskazanego punktu | sonar, heartbeat |
| wave | Pionowo przemieszczająca się fala światła | tide, ripple |
| viewfinder | Narożniki, kalibracja i linia przeszukiwania | focus, tracking |
| direct | Wąska wiązka omiatająca obszar od wskazanego punktu | beam, radar |

Efekty nie zawężają ani nie zwiększają wykrywania. Nadal działa jedno Skanuj.
Menu otrzymuje charakterystyczną oprawę wzoru, wybraną ramkę i kolory oraz
oznaczenie pracy. Reduced motion wyłącza ruch, zachowując statyczny efekt.
Nakładka nie przechwytuje kliknięć. Zamknięcie aplikacji usuwa wpływ na mapę.

Każdy wzór ma dwa zgodne assety. Zmiana animacji ogranicza listę SFX i wybiera
pierwszy zgodny dźwięk, jeżeli poprzedni nie pasuje. Klient i serwer odrzucają
niedozwoloną parę. Stare regular/sweep i regular/ping pozostają zgodne:
nie zmieniono wersji kontraktu, identyfikatorów ani historycznych plików WAV.
Osiem nowych, własnych PCM generuje `node tools/build_deepscanner_sfx.js`;
czas 2,4 s, łagodne wejście/wyjście, wyrównany poziom RMS i ograniczenie szczytów.

Audio korzysta z GameSfx i ustawień gracza. Pętla trwa przez cały skan,
z 250 ms przerwy po frazie. Kolejne retry API nie tworzą nowych pętli;
równoległe mapy współdzielą dźwięk. Koniec ostatniego skanu, zamknięcie,
utrata aktywacji i crash anulują powtórzenia.

## GhostLab — podgląd

Podgląd efektu i SFX trwa 6 s; wykorzystuje ten sam CSS i pętlę audio co mapa.
Można wybrać demonstrację sukcesu, zera trafień, błędu API lub odmowy.
Tekst wyraźnie oznacza przykładowy wynik. Nie powstają markery, opłaty ani
zapytania skanu. Osobny odsłuch odtwarza jedną frazę, Zatrzymaj kończy pokaz.
Zmiana pól lub zamknięcie edytora sprząta timery/audio. Katalog logów rozszerzono
o kalibrację, przeszukiwanie sektora i alternatywne teksty wyników/błędów.
300/403 pozostają narracją; brak opcji 500 i maskowania prawdziwego wyniku.

## Wdrożenie

Po zatwierdzeniu i opublikowaniu pakietu:

```bash
git pull
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 logs chaos --lines 80 --nostream
```

Bez nowej migracji danych i bez nowych flag. Pozostaje flaga scanner runtime
z 146.4.1. Odśwież pulpit i ponownie otwórz mapę (nowe wersje JS/CSS/manifestu).
Istniejący regular działa od razu; zmiana produktu na inny efekt wymaga
Save Draft → Compile → Publish → jawnej bezpłatnej aktualizacji instalacji.

## Odbiór na jednym koncie

1. Najpierw otwórz dotychczasowego regular bez zmiany buildu: sprawdź brak regresji.
2. W edytorze przejdź kolejno przez pięć wzorów. Dla każdego sprawdź dwa SFX,
   podgląd 6 s (kilka fraz dźwięku), cztery wyniki demonstracji i Zatrzymaj.
3. Dla każdego nowego wzoru opublikuj/aktualizuj ten sam produkt, uruchom
   aplikację i skan na mapie. Sprawdź oprawę menu, animację, ciągłość audio,
   wynik systemowy i kolejny identyczny komunikat w następnym skanie.
4. Zamknij aplikację podczas skanu i podczas pauzy audio: powrót do Skanuj,
   brak wznowienia SFX i pozostałych nakładek. Zamknij mapę podczas skanu.
5. Sprawdź mute, zmianę głośności, reduced motion i mobile. Obszar mapy ma
   pozostać czytelny, a kontrolki edytora mieścić się bez poziomego scrolla.
6. Sprawdź, że drugi aktywny produkt jest blokowany. Wycofanie sprzedaży
   nie odbiera wcześniej kupionej instalacji.

Nie wymuszaj awarii publicznego OSM dla testu. Błędy, budżety retry i zgodność
polityki są objęte testami lokalnymi. Nie potrzeba dostępu PvP ani obchodzenia
jego limitów, aby odebrać katalog prezentacji.

## Weryfikacja lokalna

43 testy backendu: scanner, publikacja i alignment — PASS.
Zestawy JS: GameSfx, scanner lifecycle, pięć podglądów, launcher runtime,
maintenance i firmware — PASS. Sprawdzono wszystkie 50 par animacja/SFX,
rzeczywiste 10 plików WAV oraz compile/publish/update/activate pięciu wzorów.
Browser w tej sesji nie udostępnił przeglądarki; nie deklarujemy wizualnego
odbioru desktop/mobile ani odsłuchu. Cały 146.4 zostanie zamknięty po ich PASS.
