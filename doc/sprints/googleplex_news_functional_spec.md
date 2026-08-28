# Googleplex News — Functional Specification
## Kontrakt funkcjonalny strony Home/News

Status dokumentu: handoff implementacyjny.

Cel: dodać Googleplex News jako nową powierzchnię prezentacji życia świata CHAOS, bez zmiany istniejących mechanik gry.

Googleplex News jest agregatorem i powierzchnią nawigacyjną. Nie tworzy nowych mechanik gameplayowych i nie staje się nowym source of truth.

---

# 1. Zasada nadrzędna

Googleplex News pokazuje to, co już istnieje w grze:

- aktywność narzędzi,
- zdarzenia,
- konflikty,
- regiony,
- klany,
- podróże,
- pakiety/dane,
- Ghost Exchange,
- BlackNet,
- Cyberner,
- storage/dysk,
- produkty i instalacje Googleplex,
- status systemu,
- później zaakceptowane publikacje LLM.

Każda karta jest projekcją istniejącego systemu.

News nie może sam:

- zmienić terytorium,
- rozpocząć konfliktu,
- kupić produktu bez istniejącego flow,
- wykonać hacka,
- zmienić walletu,
- zmienić inventory,
- wykonać CTA bez istniejącego canonical dispatchera,
- tworzyć nowych faktów gameplayowych.

---

# 2. Dwa typy kart

Każdy wpis jest jednym z dwóch typów:

```text
ACTIONABLE
STAMP_ONLY
```

`ACTIONABLE` posiada canonical target/action.

`STAMP_ONLY` jest wyłącznie informacją.

Frontend nie decyduje sam, że karta jest clickable.

Backend/read model musi jawnie dostarczyć bezpieczną akcję.

---

# 3. Wyszukiwarka Googleplex

Istniejąca wyszukiwarka pozostaje bez zmian funkcjonalnych.

Default:

```text
query = empty
→ pokazujemy Googleplex Home / News
```

Po wpisaniu frazy:

```text
query != empty
→ uruchamia się dotychczasowy flow wyszukiwania
→ pokazują się istniejące wyniki wyszukiwania Googleplex
```

News nie zastępuje wyników wyszukiwania.

Wyczyszczenie query / powrót:

```text
→ wraca Home / News
```

Stan wyszukiwania nie może modyfikować:

- BlackNet,
- Ghost Exchange,
- Cyberner,
- innych okien gry.

---

# 4. Karta narzędzia / aplikacji

Źródło:

```text
Googleplex product/application read model
lub zatwierdzona statystyka użycia
```

Może pokazywać:

- popularność,
- trend,
- liczbę instalacji/pobrań,
- kategorię,
- skrót funkcji,
- asset narzędzia.

Jeżeli karta jest ACTIONABLE:

```text
klik
→ otwiera istniejący szczegół produktu / aplikacji w Googleplex
```

Nie kupuje automatycznie.

Nie instaluje automatycznie.

Purchase/install dalej odbywa się przez istniejący canonical flow.

---

# 5. Karta produktu promowanego / reklamy Googleplex

Może być:

- featured,
- trending,
- sponsorowane przez system gry,
- promocja kategorii,
- nowa aplikacja.

ACTIONABLE:

```text
→ istniejący product detail / catalog focus
```

STAMP_ONLY:

```text
→ brak linku
```

Brak nowych mechanik reklamowych jest wymagany.

To jest tylko nowa prezentacja istniejących produktów.

---

# 6. BlackNet

Karta może prezentować:

- aktywność BlackNet,
- trend sygnałów,
- nowe wpisy,
- interesujące tematy,
- popularność danego obszaru danych.

ACTIONABLE:

```text
→ otwórz istniejący BlackNet
→ opcjonalnie zastosuj istniejący canonical filter/focus
```

Nie tworzymy osobnego BlackNetu w Googleplex.

Nie kopiujemy całego feedu.

Googleplex News jest teaserem / entry pointem.

---

# 7. Ghost Exchange

Karta może pokazywać:

- ogólną aktywność rynku,
- trend transakcji,
- wzrost/spadek,
- aktywność określonej kategorii,
- nową ciekawą paczkę.

ACTIONABLE:

```text
→ otwórz istniejący Ghost Exchange
→ opcjonalnie focus na canonical category/item
```

Nie wykonuje transakcji jednym kliknięciem z News.

Kupno/sprzedaż pozostaje w Ghost Exchange.

---

# 8. Konflikt / region konfliktu

Karta może pokazywać:

- aktywny konflikt,
- poziom aktywności,
- trend,
- rejon,
- liczbę starć,
- zmianę kontroli,
- status zagrożenia.

Dozwolone ACTIONABLE warianty:

```text
FOCUS
→ otwórz mapę
→ focus na canonical region/conflict

TELEPORT
→ tylko jeśli istniejący canonical gameplay flow pozwala graczowi na teleport
→ użyj istniejącego dispatchera
```

Googleplex News nie może sam implementować teleportacji.

Nie może omijać kosztu, cooldownu, entitlementu ani zasad mapy.

Jeśli teleport nie jest aktualnie legalny:

```text
→ karta pozostaje focus-only
lub
→ action jest niedostępne
```

---

# 9. Podróże

Karta może pokazywać:

- popularny kierunek,
- aktywną trasę,
- zmianę ruchu,
- rejon z wysoką aktywnością.

ACTIONABLE:

```text
→ mapa / travel surface
→ focus na canonical route/region
```

Nie rozpoczyna automatycznie podróży, chyba że istniejący gameplay dispatcher ma taki zatwierdzony action i spełnione są jego guards.

---

# 10. Klany

Karta może pokazywać:

- aktywność klanów,
- zmianę pozycji,
- konflikty klanowe,
- obecność w regionie,
- wydarzenie klanowe.

ACTIONABLE tylko wtedy, gdy gra ma istniejącą powierzchnię:

```text
→ clan detail
→ mapa z clan focus
→ istniejący channel
```

W przeciwnym razie:

```text
STAMP_ONLY
```

Googleplex News nie tworzy nowego clan systemu.

---

# 11. Storage / dysk

Karta może prezentować:

- zajętość,
- dostępne rozszerzenie,
- trend zużycia,
- polecany upgrade.

ACTIONABLE:

```text
→ istniejący storage/disk management
lub
→ istniejący product detail rozszerzenia
```

Nie zmienia capacity bez purchase/install flow.

---

# 12. Pakiety danych / pliki

Karta może pokazywać:

- nową paczkę,
- popularną kategorię,
- trend pobrań,
- ostatnio aktywne typy danych.

ACTIONABLE:

```text
→ istniejący file/package detail
→ Ghost Exchange / BlackNet / właściwa surface zależnie od canonical source
```

Nie pobiera automatycznie bez istniejącej mechaniki.

---

# 13. Cyberner

Karta może pokazywać:

- wzrost aktywności,
- kanał/system source z nową informacją,
- nową rozmowę/systemowy broadcast,
- trend komunikacji.

ACTIONABLE:

```text
→ otwórz istniejący Cyberner
→ focus na canonical channel/thread/source
```

Nie tworzy sztucznego unread.

Nie wysyła wiadomości.

Nie tworzy kontaktu tylko przez render karty.

---

# 14. System / maintenance / integrity

Zwykle:

```text
STAMP_ONLY
```

Przykłady funkcji:

- maintenance,
- integrity,
- availability,
- Grid status,
- alert ogólny.

Jeśli istnieje realna strona/status detail:

```text
może być ACTIONABLE
```

ale nie jest to wymagane.

---

# 15. Statystyki globalne

Dolny strip może pokazywać agregaty:

- aktywność graczy,
- liczba konfliktów,
- aktywność rynku,
- liczba transakcji,
- global threat/status,
- system status.

Domyślnie:

```text
STAMP_ONLY
```

Nie każda liczba musi być klikalna.

Jeśli klik prowadzi do istniejącego systemu, action musi być jawnie dostarczone przez read model.

---

# 16. HERO story

HERO wybiera najważniejszy wpis w danym snapshot/feedzie.

Może reprezentować:

- duży konflikt,
- istotne wydarzenie,
- dużą zmianę rynkową,
- ważny GhostSignal,
- krytyczny system event,
- wyjątkowo silny trend.

HERO nie jest nowym typem domenowym.

To tylko:

```text
presentation_weight = hero
```

Jeśli underlying entry ma action:

```text
HERO = ACTIONABLE
```

Jeśli nie ma:

```text
HERO = STAMP_ONLY
```

---

# 17. Hierarchia prezentacji nie zmienia znaczenia

Backend/read model może nadać:

```text
hero
large
medium
small
```

To jest wyłącznie presentation weight.

Nie daje to większych uprawnień.

Nie zmienia truth class.

Nie poszerza audience.

Nie zmienia action.

---

# 18. Proposed generic read model

Minimalny rekord:

```text
news_id
source
source_ref
category
presentation_weight

title
summary
published_at

audience_scope

state
accent_role

asset_id
asset_family
asset_focus_x
asset_focus_y
asset_scale
asset_rotation

primary_stat
secondary_stat

action_type
action_target
action_payload_ref

truth_class
```

Nie wszystkie pola muszą być w pierwszej implementacji, ale read model powinien od początku rozdzielać:

```text
content
presentation
action
```

---

# 19. Allowed action families

Rekomendowane generic actions:

```text
open_googleplex_product
open_googleplex_catalog
open_blacknet
open_blacknet_filtered
open_ghost_exchange
open_ghost_exchange_filtered
open_cyberner
open_cyberner_channel
open_map
focus_map_region
focus_conflict
open_clan
open_storage
open_package
teleport_via_existing_dispatcher
```

Nazwy techniczne należy dopasować do realnych canonical action keys w grze.

Nie tworzyć nowych action keys, jeśli istniejące robią to samo.

---

# 20. Stamp-only categories

Domyślnie bez linku mogą pozostać:

- global system health,
- krótki aggregate stat,
- editorial curiosity,
- historyczny snapshot,
- trend bez istniejącego targetu,
- integrity/encryption stamp,
- maintenance note,
- source/truth badge,
- ogólny ranking bez istniejącej powierzchni detail.

Reguła:

```text
brak canonical action
→ brak interakcji
```

---

# 21. CTA safety

Frontend nie składa targetów ręcznie.

Read model dostarcza:

```text
action_type
opaque/canonical target
```

Klik:

```text
Googleplex News UI
→ existing dispatcher
→ existing validation
→ existing game surface
```

Nigdy:

```text
Googleplex News UI
→ bezpośrednia mutacja stanu
```

---

# 22. Audience

Feed przygotowuje:

```text
public
clan
owner
```

Projection musi nastąpić backendowo.

Frontend nie może otrzymać owner/clan record i dopiero ukrywać go CSS.

Zmiana konta/session:

```text
→ invalidate viewer-bound News state/cache
```

---

# 23. LLM content

Do czasu publisher sprintu:

```text
accepted Inbox candidate
≠ Googleplex News publication
```

News Home może używać:

- deterministycznych wpisów,
- fixture,
- istniejących agregatów.

Po podłączeniu publishera:

```text
ACCEPTED candidate
→ publication receipt
→ Googleplex News read model
```

Surowy output Ollamy nigdy nie trafia bezpośrednio do Home.

---

# 24. Truth/source labels

News może prezentować różne klasy informacji.

UI powinno obsługiwać jawne:

```text
source
truth_class
```

Bez tworzenia dodatkowej logiki gameplayowej.

Przykładowe typy prezentacyjne:

```text
verified
canonical
interpretation
rumor
system
```

Dokładne wartości mają pochodzić z istniejącego kontraktu gry.

---

# 25. Refresh

Googleplex News jest read surface.

Może:

- pobierać page/snapshot,
- odświeżać się po otwarciu,
- okresowo odświeżać bounded feed,
- używać state/version/cursor.

Nie może:

- powodować generacji LLM przez samo otwarcie,
- generować eventów gameplayowych,
- tworzyć nowych tasków przez poll.

---

# 26. Pagination / retention

Feed musi być bounded.

Preferowane:

```text
Home:
najświeższe / najważniejsze 12–24 entries

Full News:
paginacja/cursor
```

Home nie pobiera całego archiwum.

---

# 27. Search vs News

Search i News to dwa osobne tryby tej samej powierzchni.

```text
HOME_MODE
SEARCH_MODE
PRODUCT_DETAIL_MODE
```

Przejście do search nie powinno niszczyć cached Home state, jeśli nie ma takiej potrzeby.

Powrót może odtworzyć poprzednią pozycję scrolla Home.

---

# 28. Navigation isolation

Googleplex News nie może zmieniać filtrów:

- Ghost Exchange,
- BlackNet,
- mapy,
- Cybernera,

dopóki użytkownik jawnie nie kliknie action prowadzącego do danego systemu.

---

# 29. Existing game only

Twardy kontrakt sprintu:

```text
NIE ZMIENIAMY GRY
DODAJEMY GOOGLEPLEX NEWS
```

To oznacza:

- żadnych nowych ekonomii,
- żadnych nowych typów konfliktów,
- żadnych nowych zasad teleportu,
- żadnych nowych inventory semantics,
- żadnych nowych mechanik klanowych,
- żadnych nowych chat semantics.

News tylko:

```text
czyta
agreguje
porządkuje
prezentuje
nawiguje
```

---

# 30. Functional acceptance gate

Googleplex News jest gotowy, jeżeli:

- Home otwiera się bez zmiany istniejącego katalogu,
- wyszukiwarka nadal pokazuje dotychczasowe wyniki,
- karty reprezentują realne systemy gry,
- actionable card prowadzi przez existing canonical action/dispatcher,
- stamp-only card nie reaguje jak link,
- BlackNet teaser otwiera istniejący BlackNet,
- Ghost Exchange teaser otwiera istniejący Exchange,
- tool/product teaser otwiera istniejący Googleplex flow,
- konflikt prowadzi do istniejącej mapy/focus/teleport policy,
- Cyberner prowadzi do istniejącego kanału/surface,
- search, GX, BlackNet i News mają niezależne stany,
- otwarcie News nie wywołuje Ollamy,
- render News nie mutuje gameplayu,
- accepted LLM candidate nie pojawia się bez publication receipt,
- heavy-profile hot path pozostaje zerowy.
