# 143.5a — audyt PNG i MP3, 23 IX 2026

Komplet: **9/9 PNG + 9/9 MP3**. Nazwy bazowe odpowiadają stopniom 01–09
w README; brak brakujących par. Każdy plik ma inny SHA-256, również MP3
stopni 5 i 9, mimo identycznego rozmiaru i długości.

PNG: wszystkie **540×540 px**, 32-bit ARGB z kanałem alpha. Dekodowanie
System.Drawing poprawne; narożniki mają alpha 0–2/255. Przejrzano również
kompozycję stopnia 9: ciemna scena z przezroczystym obrzeżem.
Waga pojedynczego obrazu 554 091–676 381 B jest akceptowalna dla pojedynczego
show. Nie ma potrzeby zmieniać dostarczonych obrazów. Zalecane ładowanie
tylko potrzebnej pary i cache; nie pobierać całej paczki podczas startu mapy.
540 px jest rozmiarem dostarczonym, wcześniejsze 1024 px było rekomendacją.
Łącznie PNG: **5 354 999 B (5,35 MB)**, MP3: **539 922 B (0,54 MB)**;
cała paczka: **5 894 921 B (5,89 MB)**.

MP3: wszystkie prawdziwe MP3, **44,1 kHz, stereo, około 128 kb/s**.
Pełne dekodowanie FFmpeg (`-v error -xerror -f null`) zakończone kodem 0
dla każdego pliku. Bitrate jest niższy od wcześniejszej rekomendacji
192–320 kb/s; samo podniesienie bitrate nie poprawi istniejącego nagrania.
Audyt jest techniczny, nie stanowi odsłuchowego zatwierdzenia głośności
ani artystycznego dopasowania wszystkich dźwięków do scen.

| Stopień | Nazwa bazowa | PNG (B) | MP3 (B) | Długość MP3 (s) |
|---|---|---:|---:|---:|
| 1 | consequence_01_fine | 610479 | 84697 | 5.250563 |
| 2 | consequence_02_fine | 614241 | 57112 | 3.526500 |
| 3 | consequence_03_confiscation | 554186 | 48335 | 2.977938 |
| 4 | consequence_04_confiscation | 554091 | 42065 | 2.586063 |
| 5 | consequence_05_confiscation_fine | 556791 | 61710 | 3.813875 |
| 6 | consequence_06_detention | 576661 | 34124 | 2.089750 |
| 7 | consequence_07_detention | 554785 | 20750 | 1.253875 |
| 8 | consequence_08_detention | 657384 | 129419 | 8.045688 |
| 9 | consequence_09_detention | 676381 | 61710 | 3.813875 |

Długości powyżej zmierzono `ffprobe`; kontener MP3 może uwzględniać padding
enkodera. W rendererze nadrzędna jest długość zdekodowanego audio odtwarzanego
przez GameSfx. Dane z audytu mogą służyć jako fallback przy niedostępnym audio;
po podmianie plików trzeba je zmierzyć ponownie.

Tło: osobna czarna/ciemna warstwa z alpha **0.6**, mapa widoczna przez nią.
Obraz i tekst bez wspólnego przygaszenia opacity. Show trwa dokładnie tyle
co SFX, nawet dla krótkiego stopnia 7 (~1,25 s); bez samowolnego wydłużania.
Ważne informacje o karze pozostają dostępne w komunikacie systemowym.
Te ustalenia dotyczą implementacji 143.5a; ten audyt nie włącza odtwarzacza.
