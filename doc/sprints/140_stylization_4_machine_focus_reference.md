# 140.stylization.4 — warstwowa prezentacja grup części

Status: `REFERENCE ACCEPTED / 160–300 IMPLEMENTED / SERVER REVIEW PENDING`.

Autor zaakceptował parę słowami „to jest to implementuj”. Pięć scen grup
wdrożono w istniejącym renderParts, ze wspólnym z parą CSS. Zmiana grup
wyznacza pozycje z czasu sceny (0,9 s), a energetyczne krawędzie podążają
za częściami. Pierścień .3 startuje od końcowych pozycji S1–S5; jego wejście
zachowuje 1,5 s i interpoluje skalę części oraz wymiary pola.
[Wdrożenie i odbiór](../runbooks/deploy_140_stylization_4_focus.md).
Hero 360–420 s pozostają dalszym zakresem .4, poza tym wdrożeniem.

Decyzja autora: w 160–300 s wykorzystać zaakceptowaną chaotyczną kompozycję
części .2. Aktualnie prezentowana piątka na pierwszym planie, pozostałe
wybledzone w głębi. Wszystkie części zachowują połączenia i wspólną oprawę.

## Pierwsza para

- [Desktop 1920×1080 / portrait 1080×1920](../../static/references/ghostsignal/machine-focus-pair.html).
- [Scena w bieżącym viewport](../../static/references/ghostsignal/machine-focus.html).
- Po push/pull: `/static/references/ghostsignal/machine-focus-pair.html`.

Wybrano `machine_group_3` z 04:15 (255 s), odpowiadającą zrzutowi autora.
PHANTOM VEIL: P1–P5 na pierwszym planie, 15 pozostałych części w tle.
To jedna para reprezentatywna dla grup części; hero maszyn 360–420 s
pozostają osobnym zakresem kompozycji .4, bez narzucania identycznego layoutu.

## Pozycje i głębia

Pięć zatwierdzonych adresów pierwszego planu .2 staje się miejscami
prezentowanej piątki: P1→slot V1, P2→V2, …, P5→V5. V1–V5 przechodzą na
dotychczasowe dalsze adresy P1–P5. E/S zachowują swoje adresy. To jawna zamiana
pozycji według numeru części, nie losowanie ani zmiana jej tożsamości.

Pierwszy plan zachowuje większe skrajne sloty (+40%) oraz pozostałe +20%
względem v3, overscan, czytelne nazwy i assety `superpower/` 540×540.
Pozostałe części: `parts/` 128×128, opacity .32/.23/.17, mniejsza skala,
kody widoczne, nazwy dostępne w HTML. Połączenia w tle są słabsze;
żadna krawędź katalogowego pierścienia nie jest usuwana.

Wspólne CSS .2 zapewnia OFS, oddychanie, subtelną łunę hover/focus,
glitch tła i energetyczne krawędzie. Bez nowych bitmap i kontrolera show.
Makieta używa jawnie katalogowego pierścienia; runtime musi użyć zamrożonego
ring_codes. Referencja nie czyta API/bazy i nie emituje zdarzeń gry.

## Integracja po akceptacji

| Czas | Scena | Ekspozycja |
| --- | --- | --- |
| 160–180 | machine_groups | Zbiorcza kompozycja części, zapowiedź czterech grup |
| 180–210 | machine_group_1 | V1–V5 na pierwszym planie |
| 210–240 | machine_group_2 | E1–E5 na pierwszym planie |
| 240–270 | machine_group_3 | P1–P5 na pierwszym planie — ta para |
| 270–300 | machine_group_4 | S1–S5 na pierwszym planie |

Przełączenie grup zmienia pozycję, skalę i głębię, zachowując kod części;
krawędzie podążają za końcami. Odzyskanie po seek ma wynikać z czasu sceny.
Przy integracji trzeba zaktualizować początek `network_expand` w .3:
przejście 300–301,5 s zaczyna się od rzeczywistej końcowej kompozycji S1–S5,
a nie od zastępowanego starego układu grup. Muzyka i timeline pozostają stałe.

## Odbiór pary

Sprawdź wyróżnienie pięciu części, widoczność piętnastu w tle, czytelność
kodów i nazw, overscan oraz zachowane połączenia. Desktop i portrait
powinny mieć tę samą hierarchię głębi. Obejrzyj 10 s efektów i reduced motion.
Potem można rozwijać pozostałe grupy w rendererze. Produkcyjny trigger
pozostaje odłożony do końca stylizacji i montażu .10.
