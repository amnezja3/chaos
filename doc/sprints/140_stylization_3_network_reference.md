# 140.stylization.3 — pierwsza para sieci

Status: `IMPLEMENTED / LOCAL TESTS PASS / OPERATOR ACCEPTED`.

Autor potwierdził NETWORK-2 słowami „to jest to”. Formowanie pierścienia
w 1,5 s zaakceptowane; etap .3 zamknięty. Trigger nadal po pełnej stylizacji.

Integracja: pięć scen w renderMontage/renderParts. Wspólny
`ghost_signal_network.css` i `ghost_signal_network_details.js` obsługują
paletę REF-3, tooltip i dopasowanie kwadratu. Helper nie ma własnego zegara,
API ani stanu gry; usuwa listenery i ResizeObserver po opuszczeniu sceny.
Animacje, węzły i gradienty krawędzi synchronizuje istniejący tick show.
Opis supermocy pochodzi z istniejącego katalogu w lekkim manifeście.
[Procedura odbioru runtime](../runbooks/deploy_140_stylization_3.md).

REF-3: zgodnie z końcową uwagą autora tooltip dopasowano do przygaszonej
szarozielonej palety layoutu (#93b99f, #95a69b, #dfe6dc), ze słabszymi
ramkami i łuną. Etykieta „Supermoc” pozostaje w jednym wierszu.
Autor zaakceptował kierunek słowami „dostosuj kolorystykę do layoutu i mamy to”.

Korekta REF-2: autor zaakceptował kierunek, wskazując elipsę na wąskim ekranie.
Sieć ma teraz kwadratowe pole o boku równym mniejszemu wymiarowi dostępnej
przestrzeni; wspólne pole obejmuje SVG, części i środek. Promień X/Y jest równy.
Tooltip terminalowy na hover/focus/tap pokazuje nazwę, klan, symbol,
supermoc z opisem i maszynę, z katalogu. Escape lub dotknięcie poza zamyka;
panel mieści się w viewport. To nadal referencja, nie zmiana runtime.
Etap .2 oraz para .3 zaakceptowane przez autora. Pięć scen sieci rozwinięto
w istniejącym rendererze po akceptacji tej pary.

## Para

- [Desktop 1920×1080 i portrait 1080×1920](../../static/references/ghostsignal/network-pair.html).
- [Scena w bieżącym viewport](../../static/references/ghostsignal/network.html).
- Po push/pull: `/static/references/ghostsignal/network-pair.html`, bez reloadu.

Wybrana scena: `network_ring`, moment 05:30. Szeroka kompozycja desktop:
typografia po lewej, pierścień po prawej. Portrait: nagłówek nad pionową siecią.
20 części staje się małymi węzłami z zachowanymi kodami i akcentami klanów.
Nazwy pozostają dostępne w HTML. Środek pierścienia pokazuje liczbę węzłów,
nie fikcyjny postęp wysyłania ani gotowość operacyjną.

Topologia makiety to katalogowy TOPOLOGY_ANCHOR, jawnie oznaczony jako
referencja. Kolejność jest przejęta z zaakceptowanej pary części; w runtime
jedynym źródłem będzie zamrożony ring_codes. Bez dodatkowych połączeń.
Docelowy adres: kąt `2π × indeks / 20 − π/2`, X = 50 + 41 cos(kąt),
Y = 50 + 41 sin(kąt), procent kwadratowego pola sieci. Różne kompozycje
desktop/portrait zachowują koło, tożsamość i kolejność węzłów.

Energetyczny rdzeń, łuna, zanikanie i fazy błysków pochodzą ze wspólnego
CSS zaakceptowanego w .2. Reuse wallpaper2.jpg, ikon części 128×128,
OFS i glitch mapy. Bez nowych bitmap, audio, API, bazy czy triggera.
Reduced motion zachowuje statyczną sieć. Makieta pokazuje kompozycję
i dekoracje; nie demonstruje jeszcze animacji transformacji pomiędzy scenami.

## Plan pięciu scen po akceptacji

| Czas | Scena | Kierunek |
| --- | --- | --- |
| 01:30–02:00 | connections | Zachować zaakceptowane adresy czterech planów .2 i energetyczne połączenia |
| 05:00–05:20 | network_expand | Rozwinąć sieć z końcowych pozycji grup maszyn .4; zachować kod i przypisanie |
| 05:20–05:40 | network_ring | Uporządkować węzły w pierścień według zamrożonego ringu; para 05:30 wyznacza stan docelowy |
| 05:40–05:50 | network_tension | Ten sam układ, silniejsze miejscowe impulsy; bez losowania nowych adresów |
| 05:50–06:00 | network_ready | Wyciszyć napięcie, przygotować przekazanie do hero maszyn .4 |

Pozycje początkowe/końcowe muszą zgadzać się na granicach; .4 później
doprecyzuje własne kompozycje maszyn. Czas interpolacji wynika z bieżącego
czasu sceny, również po seek/reconnect. Brak ringu daje jawny brak danych,
a nie rekonstruowaną z katalogu historię.

## Odbiór pary

Oceniamy proporcje pierścienia, czytelność wszystkich 20 kodów, dominantę
typografii i energetyczny charakter połączeń w obu formatach. Obejrzeć 10 s
dekoracji, sprawdzić rzeczywistą szerokość telefonu i reduced motion.
Sprawdzono strukturę 20 kodów/20 krawędzi, zgodność topologii i dostępność
lokalnych assetów. Odbiór wizualny należy do autora; automatyczna przeglądarka
była niedostępna przy poprzednich próbach. Trigger nadal po .1–.9 i montażu .10.
