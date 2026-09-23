# Consequences Show — SFX MP3

Katalog na dźwięki autora do dziewięciu show konsekwencji, sprint **143.5a**.
Gotowe MP3 zapisuj bezpośrednio tutaj: `static/audio/sfx/consequences/`.
HTTP: `/static/audio/sfx/consequences/<nazwa_pliku>.mp3`.

Każdy stopień ma osobny dźwięk. Nazwa bazowa odpowiada PNG z
[katalogu grafik](../../../images/consequences/show/README.md).
Numery oznaczają stopień konsekwencji, nie poziom incydentu L1–L5.

## Nazwy, charakter i długość

Długości poniżej są wcześniejszymi wskazówkami produkcyjnymi, a nie limitami.
Zgodnie z ustaleniem 23 IX 2026 **czas całego show jest równy rzeczywistej
długości dostarczonego SFX**. Nie zmieniać ani nie przycinać plików do tych
widełek. Aktualne długości zawiera [audyt assetów](../../../../doc/runbooks/sprint_143_5a_asset_audit.md).

| Stopień | Plik MP3                               | Scena / charakter dźwięku                                                                                                                                                                                                               | Długość |
| ------- | -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------: |
| 1       | `consequence_01_fine.mp3`              | Zwykła kontrola: krótki **beep terminala**, elektroniczny wydruk/stempel mandatu, pojedynczy niski impuls „charge accepted”; spokojnie, prawie administracyjnie.                                                                        |   2–3 s |
| 2       | `consequence_02_fine.mp3`              | Recydywa + przeszukanie plecaka: **dwa krótkie impulsy mandatu**, szelest/zamek plecaka, szybki skan elektroniki, ostrzegawczy podwójny beep. Wyraźnie bardziej nerwowo niż lvl 1.                                                      |   3–4 s |
| 3       | `consequence_03_confiscation.mp3`      | Kasowanie plików z laptopa: podłączenie urządzenia, cyfrowy handshake, szybkie **data wipe / delete sweep**, zanikające glitchujące dane i twarde `DEVICE DISABLED`.                                                                    |   4–5 s |
| 4       | `consequence_04_confiscation.mp3`      | Większa konfiskata: kilka urządzeń kolejno odłączanych, dwa ciężkie kliknięcia blokad, skan, wyciszanie elektroniki jedno urządzenie po drugim, zamknięcie skrzyni dowodowej.                                                           |   4–5 s |
| 5       | `consequence_05_confiscation_fine.mp3` | Pełna kontrola sprzętu + kara: chaotyczniejszy sweep danych, kilka `disconnect`, ciężkie zatrzaśnięcie case'a, a na samym końcu znajomy z lvl 1–2 **finansowy impuls mandatu**.                                                         |   5–6 s |
| 6       | `consequence_06_detention.mp3`         | **Zwykłe aresztowanie przy motocyklu:** krótkie syreny w oddali, radio CHPD, krok funkcjonariusza, metaliczny **klik kajdanek**, laptop rozpoczyna skan i na końcu spokojny niski lock.                                                 |   4–5 s |
| 7       | `consequence_07_detention.mp3`         | **Ciemna uliczka, dwóch tajniaków, motocyklista na ziemi:** gwałtowne hamowanie auta, drzwi, szybkie kroki, uderzenie o mokry asfalt, dwa mocne kliknięcia kajdanek, krótki zaszumiony komunikat radiowy.                               |   5–6 s |
| 8       | `consequence_08_detention.mp3`         | **Skrzyżowanie, pełna blokada, negocjator:** narastające syreny z wielu stron, helikopter, wirnik, komunikacja radiowa, niski puls napięcia; wszystko nagle uspokaja się przy geście negocjatora → pojedynczy ciężki confirmation tone. |   6–8 s |
| 9       | `consequence_09_detention.mp3`         | **Total lockdown:** ciężki wirnik/VTOL nad głową, kilka warstw radiowych, drony, dalekie syreny, metaliczne ruchy oddziału, potężny sub-bassowy lockdown pulse, potem **odcięcie całego pasma**, krótki cyfrowy trzask i cisza.         |  8–10 s |


```text
README.md
consequence_01_fine.mp3
consequence_02_fine.mp3
consequence_03_confiscation.mp3
consequence_04_confiscation.mp3
consequence_05_confiscation_fine.mp3
consequence_06_detention.mp3
consequence_07_detention.mp3
consequence_08_detention.mp3
consequence_09_detention.mp3
```

## Eksport

- Prawdziwy MP3, nie WAV ze zmienionym rozszerzeniem. Zalecane 44,1 lub 48 kHz,
  192–320 kb/s, spójnie dla całej paczki; mono lub stereo zgodnie z materiałem.
- Krótki efekt bez zapętlenia, bez długiej ciszy na początku, z łagodnym
  zakończeniem bez kliknięć i przesterowania. Zachowaj podobną odczuwalną
  głośność wszystkich plików; eskalację buduj charakterem, nie samym poziomem.
- Styl CHAOS, dopasowany do istniejących paczek
  [Secret Path](../secret_path/README.md) i [GhostNetwork](../ghostnetwork/README.md).
- Nie dogrywaj radia ani całego podkładu muzycznego. Wyłącznie SFX danego show.
- Nie nagrywaj zmiennych kwot HC, nazw graczy/narzędzi ani czasu aresztu.
  Faktyczne wartości poda warstwa tekstowa na podstawie backendu.
- Nazwy plików dokładnie jak w tabeli, małe litery, bez spacji. Nie dodawaj
  pustych MP3 jako placeholderów. Materiały źródłowe WAV trzymaj osobno.

## Podłączenie w 143.5a

Klucze wspólnego GameSfx: `consequence.stage_1` do `consequence.stage_9`,
przypisane kolejno do plików z tabeli w `../manifest.v1.json`.
Wyzwalaczem jest prywatna delta wykonania kary, z atomowym claim receipt.

Wykorzystać istniejący `GameSfx`, ustawienia SFX, głośność, wyciszenie,
odblokowanie audio w przeglądarce i mechanizm przyciszania radia. Bez osobnego
`new Audio()` omijającego mikser. Start dźwięku razem z właściwym show po
potwierdzonym wykonaniu kary; trwały identyfikator receipt/sankcji do dedupe.
Retry, reconnect i odtworzenie historii nie uruchamiają dźwięku ponownie.

Audio i obraz mają jeden start oraz wspólny koniec. Długość zdekodowanego
audio (np. `AudioBuffer.duration` wspólnego GameSfx) wyznacza cały czas show,
łącznie z wejściem i wyjściem. Bez stałego timera dla wszystkich stopni,
minimalnego hold, dodatkowej końcówki po SFX i zapętlenia.
Wyciszenie/autoplay nie zmienia czasu obrazu: użyć metadanych dźwięku lub
zapisanej długości właściwego pliku jako fallbacku przy błędzie ładowania.
Nie czekać bez końca na `ended`, gdy dźwięk nie został odtworzony.

Przy kilku karach skoordynować kolejkę obrazu i dźwięku, aby nie mieszać
różnych stopni. Nie odtwarzać dodatkowo tego samego SFX z obsługi komunikatu
systemowego. Brak/uszkodzenie MP3 lub blokada autoplay nie mogą blokować
PNG, wykonania kary ani działania gry. Po odblokowaniu audio nie odtwarzać
zaległych, już zakończonych show.
## Integracja 143.5a

Pliki są podłączone do `consequence.stage_1`–`consequence.stage_9` we wspólnym
`manifest.v1.json`, bus `system`. `GameSfx` respektuje mute i głośność;
start i koniec audio sterują show. Przy braku startu w 1,5 s audio jest anulowane,
a grafika używa zmierzonej długości MP3 z `static/js/consequence_show.js`.
Nie skracać show do stałego czasu ani dodawać hold po końcu dźwięku.
