# Sprint 155 — Ghost System: treści, historia i pełny odbiór PL/EN

Status: **ZAPLANOWANY**, 6 X 2026. Po PASS
[154](sprint_154_ghost_system_apps_catalogs.md). Ostatni sprint programu
rozpoczętego w [153](sprint_153_ghost_system_i18n_foundation.md).

## Cel

Zakres odbioru dotyczy wdrożonego Ghost Systemu; zamrożone sprinty 149–152
nie są zależnością ani warunkiem PASS. Ich przyszłe funkcje przejmą kontrakt i18n
dopiero po osobnej decyzji o wznowieniu.

Domknąć systemowe treści dynamiczne i zapisane, przeprowadzić bezpieczny rollout
oraz udostępnić pełną wersję angielską. Nie dopuścić do produktu, w którym
angielski pulpit nadal otrzymuje polskie systemowe błędy lub narrację.

## 155.1 — zdarzenia i wiadomości

- Komunikaty operacji, logi widoczne graczowi, nagrody LVL/RSP/HC, terytoria,
  wtargnięcia, konflikty, Response Network, konsekwencje, zatrzymanie i więzienie,
  reputacja, portfel, questy/tutoriale oraz GhostNetwork mają klucze i parametry.
  Logi techniczne dla operatora mogą pozostać w jednym języku; tekst pokazany
  graczowi jest częścią zakresu PL/EN.
- Systemowe powiadomienia Cybernera, World i innych kanałów oraz publikacje
  BlackNet i Googleplex News lokalizowane per odbiorca. Wiadomości użytkowników,
  klanowe dokumenty i komentarze pozostają oryginalne. Mieszany kanał musi
  poprawnie obsługiwać oba pochodzenia obok siebie.
- Trwały event przechowuje identyfikator, wersję schematu treści, klucz/parametry
  albo referencję do wariantów publikacji. Język nie wchodzi do dedupe key,
  payment key, receipt ani tożsamości zdarzenia. Odczyt w EN nie tworzy drugiej
  nagrody, alarmu lub wiadomości ani nie odtwarza już zużytego toastu.
- Feed/delta/recovery korzystają z tego samego kontraktu. Zmiana języka
  przerysowuje dostępne wpisy historii, ale zachowuje read cursor, unread,
  kolejność i limity historii World (100 / 14 dni, fallback 10).
- Lokalizowane są również systemowe raporty i dokumenty dostarczane jako pliki.
  Widok/eksport wybiera język, nie zmienia identyfikatora pliku, rozmiaru
  gameplayowego, jakości, zasobów ani wartości paczki na rynku.

## 155.2 — narracja LLM i multimedia

- Rozdzielić kanoniczne fakty/CTA publikacji od tekstu. Systemowa narracja
  otrzymuje wariant PL i EN tej samej wersji treści, z jednym event ID.
  Wariant językowy nie może zmienić celu, kwot, terminów ani skutków akcji.
- Generowanie/przekład systemowej prozy wykonać asynchronicznie przy publikacji
  lub kontrolowanym backfillu, z cache, limitami kolejki, retry i walidacją.
  Nie wywoływać Ollamy przy otwarciu aplikacji ani zmianie języka; nie podwajać
  publikacji per odbiorca. Uwzględnić ograniczenie zasobów Ollamy opisane
  w [hardbugfixie](../hardbugfix/ollama_cpu_quota_2026-10-05.md).
- Gdy model nie dostarczy EN, dostępny jest zatwierdzony szablon PL/EN opisujący
  te same fakty. Nie blokować gameplayu i nie udawać, że polski tekst jest EN.
  Awarię oraz użycie szablonu mierzyć, bez ujawniania prywatnych treści.
- Własne dokumenty, opisy i wiadomości graczy nie trafiają do tego pipeline'u.
  Zgoda na użycie asystenta kreatora nie oznacza zgody na tłumaczenie publikacji.
- Zinwentaryzować napisy w obrazach, canvas/SVG, animacjach, filmach i wypowiedziach
  systemowych. Tekst przenieść do renderowania językowego albo przygotować
  wersje zasobów. Dla systemowej mowy zapewnić wariant językowy oraz napisy;
  efekty bez słów i uzgodnione nazwy własne pozostają wspólne.

## 155.3 — historia i migracja

- Inwentaryzacja istniejących wiadomości, szablonów i produktów przed migracją:
  źródło, liczba, rozmiar, identyfikatory, możliwość odzyskania klucza/parametrów.
- Jednoznaczne stare komunikaty systemowe mapować po źródle i kontrakcie na
  klucze; nie wykonywać globalnego replace polskich słów. Historyczną narrację
  o potwierdzonym autorstwie systemowym uzupełnić wariantami językowymi offline.
  Zachować oryginał i wersję treści dla audytu.
- Niejednoznaczne wpisy pozostają bez zmian do ręcznego rozstrzygnięcia
  pochodzenia. Znane, nadal dostępne graczowi systemowe treści bez EN blokują
  pełny PASS; oznaczenie ich jako „legacy” nie zwalnia z zakresu.
- Skrypt: dry-run z raportem, ograniczone batche, checkpoint, idempotencja,
  możliwość wznowienia i rollback wyłącznie nowych danych lokalizacji.
  Brak ponownego wysyłania wiadomości, resetu read cursor i naliczania nagród.
- Migracje poza requestami; test na kopii danych, backup i instrukcja operatorska.
  Nie modyfikować hurtowo profili, artefaktów graczy ani podpisów kontraktów.

## 155.4 — pełne pokrycie i rollout

- Zamknąć rejestr z 153: aktywne interfejsy, administracja, odzyskanie sesji,
  serwis/offline, ekran startowy, pomoc i treści niedostępne dla zwykłego konta
  muszą mieć pokrycie. Archiwalne, nieużywane pliki oznaczyć jako takie z dowodem,
  aby nie zawyżały deklarowanego pokrycia.
- CI: zgodność kluczy i parametrów PL/EN, wszystkie formy pluralizacji,
  brak uszkodzonych placeholderów, skan nowych literalnych tekstów systemowych,
  kontrola wyjątków oraz test nietłumaczenia UGC. Skan literalów jest pomocą,
  nie dowodem kompletności bez testów działającej aplikacji.
- Playwright i odbiór językowy: pełna pętla gry po angielsku i regresja po polsku,
  desktop/mobile, powiększone okna, fullscreen gry, klawiatura ekranowa,
  długi tekst, różne strefy czasowe. Test automatyczny viewportu uzupełnić
  odbiorem na fizycznym Androidzie i iOS; wyników nie zastępować deklaracją.
- Równoczesne konta PL/EN widzą ten sam świat i saldo. Zmiana języka podczas
  operacji, odbioru delty, tworzenia projektu, podróży i sprzedaży nie powiela
  działań, nie resetuje postępu i nie gubi draftu.
- Porównać baseline czasu startu pulpitu, wielkości bootstrapu/paczek, liczby
  requestów i czasu renderowania. Katalogi domen ładowane na żądanie i cache'owane;
  brak pełnych profili i wywołań tłumacza w zwykłych odczytach.
- Rollout: środowisko testowe → konta testowe PL/EN → włączenie EN dla graczy
  po odbiorze. Rollback wyłącza wybór EN i przywraca PL, zachowując stan gry,
  ustawienia i oryginalne treści. Braki tłumaczeń mają raport z kluczem/domeną,
  bez treści prywatnych wiadomości w telemetrii.

## 155.5 — procedura dodania kolejnego języka

Runbook opisuje: rejestrację locale i kierunku pisma, komplet katalogów,
pluralizację i formaty, fonty/glyphy, warianty narracji i mediów, kontrolę jakości,
testy oraz dopuszczenie do selektora. Zademonstrować dodanie testowego pakietu
przez manifest i katalogi bez nowej gałęzi logiki w aplikacjach. Gotowa wersja
rosyjska/hiszpańska nie jest częścią tych trzech sprintów.

## Twarda bramka końcowa

**PASS 155 / pełne PL–EN** dopiero po spełnieniu wszystkich warunków:

1. 100% wymaganych pozycji inwentarza systemowego ma zatwierdzone PL i EN,
   włącznie z treściami trwałymi, komunikatami błędów i zasobami multimedialnymi.
2. Brak nieuzgodnionych braków EN maskowanych polskim fallbackiem.
3. UGC i nazwy własne zachowane, kontrakty i skutki gameplayowe identyczne.
4. Migracja i rollback sprawdzone; brak ponownej emisji historycznych zdarzeń.
5. Automatyczne testy i odbiór językowy oraz mobilny zaliczone, dowody w raporcie.
6. README, journal, glosariusz, rejestr pokrycia i runbook nowego języka aktualne.

Brak powyższych warunków oznacza dalszą wersję testową, nie częściowe „pełne EN”.
