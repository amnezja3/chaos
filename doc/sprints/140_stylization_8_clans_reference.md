# .8 — ranking klanów / para referencyjna

Status: PARA ZAAKCEPTOWANA, WDROŻONA. Odbiór runtime klanów pozostaje otwarty.
[Procedura wdrożenia](../runbooks/deploy_140_stylization_8_clans.md).

Wariant clans-ref-2: symbole odtworzone ręcznie jako czyste ścieżki SVG
na podstawie czterech referencji użytkownika, bez napisów, tkaniny i tła.
Pliki w `static/images/ghostnetwork/clans/`: virex.svg (czerwony),
echo_freedom.svg (złoty), phantom_mesh.svg (turkusowy), sentinel_order.svg
(błękitny). To rekonstrukcja wektorowa, nie osadzona bitmapa.
Zastępują wcześniejsze całe plakaty logo_faction_img_*; pole jest teraz
kwadratowe, obraz zachowuje proporcje i pozostaje na przezroczystym tle.

Para: `/static/references/ghostsignal/clans-pair.html?v=clans-ref-1`.
Pełny ekran: `/static/references/ghostsignal/clans.html?v=clans-ref-1`.

Tytuł: katalogowa nazwa klanu. Logotyp z istniejących logo_faction_img_1–4.png,
mały numer pozycji, Clan Ghost Score, suma RSP członków oraz liczba uczestników.
Obok pełna lista czterech klanów, aktywna pozycja z efektem OFS.
Wspólna oprawa rankingu graczy; pole logotypu zachowuje proporcje
systemowych assetów 373 × 1002, bez rozciągania i kadrowania.

Jawnie przykładowe dane: score 180/140/110/70, RSP 14000/10000/7600/4800,
uczestnicy 3/2/2/1. Kolejność według score, nie sumy RSP. RSP nie jest
osobną wypłatą dla klanu; to suma nagród jego uczestników.
Istniejąca projekcja settlement.clans zawiera rank/code/score/rsp/members.

Start: jeden przebieg czterech klanów po 6 s, wspólny dla obu widoków.
Pauza i kolejny klan dostępne wyłącznie na stronie pary. Bez API gry i audio.
Implementacja po akceptacji obejmie istniejące sceny clans i clan_ranking.

Sprawdzone: składnia JS, zgodność identyfikatorów HTML/JS, obecność logotypów.
Ocena desktop/portrait pozostaje w przeglądarce.
