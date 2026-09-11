# 140.stylization.1+ — stylizacja całego GhostSignal show

Status: `DRAFT / BACKLOG`, otwarty decyzją autora 2026-09-11.

## Cel i zależność od Sprintu 140

Przejść wspólnie przez całe show 00:00–15:00, scena po scenie, i dopracować
kompozycję, czytelność, ruch, przejścia oraz oprawę dźwiękową. Kolejne iteracje
140.stylization.1, .2 itd. wynikną z przeglądu; nie ustalamy ich liczby z góry.
Ten draft nie rozpoczyna jeszcze implementacji stylizacji.

[Sprint 140](sprint_140_ghostsignal_15_minute_finale.md) przygotowuje działający
szkielet: źródła i projekcje danych, kolejność scen, synchronizację z czasem
serwera, video, muzykę, recovery i integrację z restartem. Jego odbiór techniczny
nie zamraża wyglądu. Podgląd 140.2 został zaakceptowany jako podstawa do dalszej
pracy, a poprawki estetyczne trafiają tutaj.

[Szczegółowy scenariusz](sprint_140_ghostsignal_szczegolowy_scenariusz.md)
pozostaje kierunkiem artystycznym. W stylizacji dostosowujemy go do działającej
implementacji i zatwierdzonego kontraktu 139.

## Zakres wspólnego przeglądu

| Odcinek | Przedmiot stylizacji |
| --- | --- |
| 00–03 | Przejęcie pulpitu, wejście części, historia i czytelność grupowania |
| 03–06 | Cztery grupy maszyn, sieć, ring, rytm narastania napięcia |
| 06–07 | Hero maszyn, ekspozycja assetów i hierarchia opisów |
| 07–08 | Ramka filmu, przejścia do retrospekcji, terminal 2108 i potwierdzenie |
| 08–12 | Mapa i konsekwencje dla świata, nagrody, uczestnicy, czytelność wyników |
| 12–14 | Odtworzenie warstw systemu, aplikacji i pulpitu |
| 14–15 | Ranking, archiwum, wyciszenie, shutdown i przejście do nowego pulpitu |

Każdy odcinek oceniamy w kontekście całego show: spójność kolorów i typografii,
czas na odczytanie danych, proporcje assetów, puste lub przeciążone fragmenty,
przejścia, zgranie z muzyką, desktop/mobile i reduced motion. Lista jest
zakresem przeglądu, nie stwierdzeniem usterek zaakceptowanego podglądu.

## Granice techniczne

- Rozwijamy istniejący kontroler, manifest, projekcje i GhostRadio. Nie budujemy
  równoległego systemu scen, radia, eventów ani magazynu danych.
- Zachowujemy lekką ścieżkę i brak ciężkich profili. Widok korzysta z ograniczonych,
  właściwych dla odbiorcy projekcji; brak danych ma jawny fallback.
- Zegar show pozostaje serwerowy, 900 s. Seek/reconnect odtwarza bieżący stan,
  a animacja, koniec filmu czy MP3 nie sterują skutkami w świecie.
- Emisja, SFX `ghost.signal_sent`, settlement, rollover i restart/ACK z 139
  pozostają obowiązujące. Późniejsza wizualizacja emisji jest retrospekcją.
- Video zachowuje proporcje 3:2 i pole maksymalnie 720×480, bez interakcji,
  kontrolek i fullscreen w odtwarzaczu. Nie powiększamy go kosztem jakości.
- Cztery MP3 mają łącznie 860,055376 s. Autor zatwierdził AAC filmu i 0,5 s
  nakładania: fade-out muzyki 425–425,5 s, pauza do 463,12 s, fade-in do
  463,62 s. Muzyka kończy się w 897,675376 s, ostatnie około 2,325 s to cisza.
  Tło zastępuje radio, ustawienia mute są nadrzędne. Ocenę tempa robimy z audio.
- Zachowujemy ograniczone ładowanie assetów i zwalnianie zasobów po scenie.
  Poprawki estetyczne nie mogą pogorszyć blokady UI, recovery ani dostępności.

## Sposób pracy w iteracjach

1. Obejrzeć ciągłe 15 minut na desktopie i mobile, następnie przejść sceny
   suwakiem istniejącego podglądu. Oddzielić uwagi wizualne od błędów danych,
   czasu lub działania; błędy funkcjonalne wracają do odpowiedniego zakresu 140.
2. Zapisać uwagi z kodem sceny/czasem, urządzeniem i oczekiwanym efektem.
3. Wybrać spójny zakres najbliższej iteracji i nanieść zmiany w istniejących
   rendererach, stylach oraz konfiguracji prezentacji.
4. Porównać sceny przed/po, przejścia z sąsiednimi scenami i zachowanie po seek.
5. Zebrać akceptację autora; po ostatniej iteracji obejrzeć całość bez przewijania.

Szablon wpisu backlogu: scena/czas → obserwacja → zamierzony efekt → zakres
zmiany → desktop/mobile → walidacja → decyzja autora. Konkretne uwagi zostaną
uzupełnione podczas przeglądu, bez wymyślania z góry koniecznych poprawek.

## Kryteria odbioru

Całe show ma spójną oprawę i akceptację autora, dane pozostają czytelne,
film zachowuje jakość, a miks nie nakłada na siebie radia, muzyki show i SFX.
Desktop/mobile, reduced motion, powrót z tła, brak assetu i seek działają
poprawnie. Testy dobieramy do zmian; po stylizacji całości powtarzamy ciągły
przegląd 15 minut i kontrolę wydajności. Nie uruchamiamy prawdziwego finału
wyłącznie po to, by ocenić CSS lub kompozycję.
