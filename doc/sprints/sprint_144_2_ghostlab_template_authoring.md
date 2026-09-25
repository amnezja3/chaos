# Sprint 144.2 — GhostLab: wspólny kreator i przygotowanie do runtime

Status: **PASS — ODBIÓR ZAMKNIĘTY**, 25 IX 2026. Po PASS [144.1](sprint_144_1_ghostlab_template_registry.md).
Wdrożenie i testy: [runbook 144.2](../runbooks/sprint_144_2_ghostlab_authoring.md).
To rozszerzenie 144, nie dawna sekcja compiler w bazowym planie.
Następny: [144.3 — aktualizacja pro-toolsów i admin](sprint_144_3_pro_tools_glab_alignment.md), następnie 145.

## Zakres

- Templates i edytor generowane z publicznego opisu rejestru. Bez ręcznych
  list i osobnych formularzy dla każdego nowego template_id.
- Kreator pokazuje tylko definicje dopuszczone do GLab w kodzie. Twórca
  modyfikuje ustawienia w granicach kontraktu; admin obserwuje szablony i potomstwo,
  nie projektuje nowych logik ani zakresów działania w panelu.
- Czytelna ścieżka: wybór systemowej funkcji → marka → dozwolone ustawienia
  i prezentacja → podgląd → zapis → Compile → Publish.
- Branding obejmuje nazwę, ikonę, opis i sugerowaną cenę, w granicach walidacji
  i obecnej polityki wyceny. Nie dodaje kodu, uprawnień ani nowych skutków.
- Ikona i opis są jawnymi polami edytowalnymi twórcy (wymaganie 25 IX).
  Szablon dostarcza tylko wartości startowe; zapis, compile i publish nie
  nadpisują wyboru autora domyślną ikoną/opisem rodzica. Korzystać z istniejącego
  obsługiwanego formatu ikon; nowy upload assetów nie jest wymaganiem tego etapu.
  Opis autora oddzielić od systemowego opisu funkcji i ograniczeń.
- Branding zapisany w wersji artefaktu i eksportowany w .glab. Googleplex,
  instalacja, pulpit/FM, panel PvP, okno wyniku i admin pokazują właściwą markę.
  Zmiana brandingu tworzy nową rewizję/build; istniejąca instalacja zachowuje
  swoją wersję do jawnej aktualizacji. Legacy bez pól korzysta z jawnego fallbacku.
- Pokazać „co robi”, „na czym działa”, miejsce uruchomienia, wymagania,
  ograniczenia i wynik. Polityki systemowe mają opis, nie zestaw przełączników.
- Efekty wybierane wyłącznie z dozwolonego katalogu prezentacji. Podgląd jasno
  oznaczony jako demonstracja, bez skanowania, teleportów, kosztów i zmian świata.
- Zachować rewizje, blokadę niezapisanych zmian, nieaktualnego buildu, retry,
  wycofanie, stabilne ID i eksport .glab. Potwierdzenia destrukcyjne czerwone CHAOS.
- Istniejące projekty bez nowych opcjonalnych pól otwierają się poprawnie;
  wartości domyślne nie przepisują automatycznie opublikowanego artefaktu.
- Brak gotowego wykonawcy widoczny w karcie i po publikacji. Bilety, cleaner,
  dysk i skanery z 144.1 pozostają opisanymi kontraktami, nie pozornie działającymi ofertami.

## PASS i wejście do 145

1. Pięć istniejących szablonów można utworzyć, skonfigurować, zapisać,
   skompilować i opublikować wspólną ścieżką, bez sugerowania gotowego runtime.
2. Odbiór UI brandingu, prezentacji, Preview i eksportu; desktop/mobile.
3. Domknąć niepotwierdzone testy bazowego 144: zmiany po Compile, konflikt
   dwóch kart, usunięcie szkicu, izolacja autorów i brak nadpisania starej wersji.
4. Nowa testowa definicja z 144.1 renderuje formularz i walidację bez nowego
   kodu kreatora; brak obsługi pola daje jawną odmowę, nie ciche pominięcie.
5. Regresje istniejących publikacji Syslog i dwóch zmigrowanych projektów admina;
   brak ponownej migracji kont, zmian sald lub zakupionych wersji.
6. Dowody zero-heavy całej ścieżki, aktualny runbook i lista kontraktów dla 145.
7. Dwa produkty jednego szablonu z różnymi ikonami i opisami zachowują branding
   po zapisie, ponownym wejściu, compile, publish, withdraw/republish i eksporcie.
   W runtime odbiór kontynuowany w 145–146; nazwa/ikona rodzica nie wraca po użyciu.

Obowiązuje [zero ciężkiego profilu](../plans/creator_ghostlab_zero_heavy_profile_contract.md).
Wykryte naruszenia naprawiamy od razu, nie przenosimy ich do 145.
