# 140.stylization.4 — para hero VIREX ORACLE

Status: `REFERENCE ACCEPTED FOR ALL FOUR / RUNTIME IMPLEMENTED / SERVER REVIEW PENDING`.

Aktualna decyzja autora: para VIREX dotyczy wszystkich czterech maszyn;
pozostałe realizujemy na tym samym schemacie. Zastępuje to wcześniejsze
założenie odrębnych kompozycji poniżej. Wszystkie hero 360–420 s są wdrożone
ze swoimi tłami, obrazami, opisami i komponentami. Odbiór serwerowy otwarty.

Autor zaakceptował wariant 4: ciemny środek tła i płynne rozjaśnienie
ku bokom. Wdrożono go dla `machine_hero_1` (360–375 s). Referencja i runtime
importują wspólny `static/css/ghost_signal_machine_hero.css`. Renderer
korzysta z katalogowych opisów, istniejącego zegara, glitchu i panelu audio.
Manifest udostępnia `purpose` i `risk_extreme`; bez migracji bazy.
Instrukcja: [wdrożenie VIREX](../runbooks/deploy_140_stylization_4_virex.md).
Poniższy opis dokumentuje kolejne korekty zaakceptowanej referencji.

Korekta referencji `machine-hero-2`: desktop pokazuje również specjalizację
i ryzyko skrajne z katalogu, z dodatkowymi akcentami OFS na opisach,
indeksie i nagłówku komponentów. Na portrait wymuszone dwa wiersze
VIREX / ORACLE naprawiają odziedziczony układ flex nagłówka.
Obrys korzysta z ponownego użycia tego samego assetu maszyny; za nim
znajduje się delikatne światło przesuwające się na desktopie.
Na mobile światło jest statyczne i słabsze, bez dodatkowych animacji OFS.
Reduced motion wyłącza nowe animacje. Nadal jest to para do oceny,
przed wdrożeniem hero maszyn do renderera show.
Zakres grup 160–300 s i hero części nad panelem zostały zaakceptowane.
Ta para otwiera hero maszyn w 360–420 s.

- [Desktop 1920×1080 i portrait 1080×1920](../../static/references/ghostsignal/machine-hero-pair.html).
- [Scena w bieżącym viewport](../../static/references/ghostsignal/machine-hero.html).
- Po push/pull: `/static/references/ghostsignal/machine-hero-pair.html`.

Wybrana scena `machine_hero_1`, moment 06:08. Istniejący asset
`signal_sends/machine_virex_oracle.png` 1254×1254 dominuje w kadrze i wchodzi
przed dużą typografię VIREX / ORACLE. Przygaszona szarozielona paleta show
pozostaje bazą, czerwony akcent odpowiada Virex i detalom maszyny.

Desktop: szeroka maszyna po prawej, napis w tle, opis funkcji po lewej,
pięć części w dolnym pasie. Portrait: nagłówek nad dużą maszyną,
opis i części pod nią. Nazwy komponentów na małym ekranie pozostają
dostępne w HTML; widoczne są obrazy i kody. Bez zmiany proporcji assetu.

Opis funkcji i przypisanie V1–V5 pochodzą z katalogu. To rekonstrukcja
wizualna, nie deklaracja nowej aktywacji lub wysłania sygnału. Reuse
efektów OFS/glitch i animacji oddychania; bez nowych bitmap.
W referencji `machine-hero-3` tło zastępuje odpowiedni istniejący asset
`signal_sends/machine_*_active.png`, pod ciemną nakładką zachowującą kolor
maszyny. Standardowy glitch mapy pozostaje nad tłem, ze zmianą poziomu
średni/najwyższy. Na pierwszym planie pozostaje zwykły asset maszyny.
CSS przypisuje cztery tła przez `data-machine`: `virex_oracle`,
`echo_libertas`, `phantom_veil`, `sentinel_aegis`; bieżąca para pokazuje VIREX.
Pozostałe tła zostaną wykorzystane w odrębnych kompozycjach tych maszyn.
Brak API, danych produkcyjnych, muzyki i triggera w referencji.

Do akceptacji: dominanta i skala maszyny, zachodzenie na typografię,
czytelność opisu/komponentów oraz oba formaty. Obserwować 10 s dekoracji
i sprawdzić reduced motion. Sprawdzono lokalne pliki, pięć części i parę
viewportów; nie wykonano automatycznego odbioru wizualnego w przeglądarce.

Po akceptacji rozwijamy hero w istniejącym rendererze. Echo Libertas,
Phantom Veil i Sentinel Aegis wymagają odrębnych kompozycji; ta para
zatwierdza jakość i język wizualny, nie układ „maszyna + panel” powtarzany
cztery razy. Przejście z pierścienia i miks mediów pozostają kontraktem show.
