# Cyberner Channels Audit

Sprint 45 — Cyberner Channels Audit + UX Contract.

## Cel

Przygotować Cybernera pod kanały komunikacyjne świata gry bez implementowania
runtime kanałów i bez zmiany backendu wiadomości.

Sprint 45 nie dodaje endpointów, nie tworzy `channel_store`, nie tworzy drugiego
`mail_store`, nie tworzy drugiego inboxa i nie zmienia modelu kontaktów.

## Stan obecny

Cyberner korzysta z istniejących systemów:

* `MailStore`,
* tabela `chat_messages`,
* tabela `contacts`,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `/api/contacts`,
* `system_messages`,
* `openEmailChatWith()`.

Tabela `chat_messages` ma obecnie najważniejsze pola:

* `owner_username`,
* `scope`,
* `peer_name`,
* `sender`,
* `subject`,
* `body`,
* `created_at`,
* `read_at`.

Obecny runtime rozpoznaje tylko dwa techniczne zakresy rozmów:

* `scope = group`, `peer_name = global`,
* `scope = direct`, `peer_name = <player/source>`.

To wystarcza na obecny publiczny czat i rozmowy prywatne, ale nie opisuje
jeszcze jawnie kanałów świata.

## Istniejące dane w bootstrapie

`/api/mail/bootstrap` zwraca obecnie:

* `username`,
* `contacts`,
* `pending_threads`,
* `group_messages`,
* `unread_counts`,
* `group_active_count`.

Frontend ma już:

* `CYBERNER_ICON_LIBRARY`,
* `cybernerSourceForThread()`,
* `cybernerSourceKeyForName()`,
* `cybernerSourceKeyForMessage()`,
* `openEmailChatWith(peer)`,
* `mailMobileView = list/chat`,
* defensive fallbacki dla world/system-like threads.

## Model rozmów

Docelowo Cyberner rozróżnia typ rozmowy od danych kontaktu.

### CHANNEL

Kanał jest trwałym źródłem komunikacji świata.

Kanał nie jest kontaktem użytkownika.

Kanał nie powinien być zapisywany ani traktowany jak wpis w `contacts`.

Kanały Sprintu 46:

* `WORLD`,
* `FRIENDS`,
* `CLAN`.

Kanały przyszłe:

* `FACTION`,
* `TRADE`,
* `EVENT`,
* `WAR`,
* `OPERATION`,
* `RAID`.

### PRIVATE

Prywatna rozmowa jest threadem z graczem albo kontaktem.

Prywatne rozmowy korzystają z istniejącego:

* `scope = direct`,
* `peer_name = <username>`,
* `contacts`,
* `pending_threads`.

### SYSTEM

Thread systemowy jest rozmową prowadzoną przez system gry albo źródło świata.

Przykłady:

* System,
* Ghost Exchange,
* AI Central,
* Misje,
* Marketplace,
* BlackNet,
* NPC.

System/world source może technicznie korzystać z `scope = direct`, ale nie wolno
traktować go jako kontaktu do akceptacji.

### PENDING

Pending request pozostaje stanem contact flow.

Pending nie jest kanałem.

Pending nie może tworzyć drugiego kontaktu ani drugiej rozmowy po akceptacji.

## Nazwy kanałów

Docelowa nazwa publicznego kanału świata to:

```text
WORLD
```

Nie używać `# grupa` jako nazwy docelowej. `# grupa` może pozostać legacy
identyfikatorem UI do czasu Sprintu 46.

`GLOBAL` jest nazwą techniczną. `WORLD` lepiej opisuje kanał świata gry.

## Ikony źródeł

`CYBERNER_ICON_LIBRARY` jest właściwym miejscem dla ikon komunikatora.

Ikona identyfikuje typ źródła, nie konkretną nazwę rozmowy.

Poprawny model:

```text
source = clan
↓
CYBERNER_ICON_LIBRARY.clan
```

Niepoprawny model:

```text
if title == "KLAN"
```

Sprint 46 powinien dodać albo potwierdzić klucze:

* `world`,
* `friends`,
* `clan`.

Obecny klucz `group` może zostać jako alias legacy dla publicznego kanału
świata, ale renderer powinien docelowo korzystać z typu źródła.

## Singletony kanałów

Kanały są singletonami w profilu.

Dla jednego profilu może istnieć tylko jedna rozmowa typu:

* `WORLD`,
* `FRIENDS`,
* `CLAN`.

Konsekwencje dla Sprintu 46:

* `WORLD` mapuje się do istniejącego `scope = group`, `peer_name = global`,
* `FRIENDS` musi mieć stabilny `channel` / `source`, jeśli zostanie pokazany,
* `CLAN` musi mieć stabilny `channel` / `source` oraz znać klan profilu,
* UI nie może tworzyć kanału przez `/api/contacts`,
* kliknięcie kanału nie może tworzyć pending request,
* refresh bootstrapu nie może dublować kanałów.

## Klany

Profil ma już pole `clan`.

Kod mapy i targetów już używa przynależności klanowej w kilku miejscach:

* relacja `same_clan`,
* blokowanie oznaczania własnego klanu jako celu,
* clan vulnerabilities.

Cyberner może stać się pierwszym systemem, który pokazuje klan jako realną
komunikację gameplayową.

Sprint 45 nie implementuje logiki klanów.

Sprint 46 powinien tylko przygotować kanał `CLAN` jako singleton oparty o
istniejącą przynależność profilu, jeśli dane są dostępne.

Przyszłe systemy, takie jak wojny klanów, operacje grupowe, wspólne terytoria i
wydarzenia, powinny pisać do kanału `CLAN`, a nie budować osobne systemy
komunikacji.

## Czy obecna architektura wystarcza?

### WORLD

Tak.

`WORLD` może korzystać z istniejącego:

```text
scope = group
peer_name = global
```

W Sprincie 46 potrzebna jest głównie zmiana read modelu i nazwy prezentacyjnej.

### PRIVATE

Tak.

Prywatne rozmowy i pending requests już działają przez `direct`, `contacts` i
`pending_threads`.

Nie należy ich mieszać z kanałami.

### SYSTEM / WORLD SOURCE

Częściowo.

System, Ghost Exchange i AI Central mogą dziś działać jako direct notification,
ale ich tożsamość jest w frontendzie rozpoznawana głównie po nazwie albo
opcjonalnym `source_type` / `type`.

Sprint 46 powinien preferować jawne `source`, jeśli backend może je zwrócić bez
przebudowy modelu.

### FRIENDS

Częściowo.

Lista kontaktów istnieje, ale nie ma jeszcze jednego wspólnego kanału znajomych.

Kanał `FRIENDS` nie powinien być kontaktem. Jeśli Sprint 46 ma go pokazać jako
aktywny kanał, potrzebuje minimalnego read/runtime oznaczenia `channel=friends`
albo bezpiecznego stanu placeholder bez wysyłania wiadomości.

### CLAN

Częściowo.

Pole `profile.clan` istnieje i jest używane przez systemy mapy, ale mail runtime
nie ma jeszcze kanału klanowego.

Sprint 46 potrzebuje minimalnego `channel=clan` albo `source=clan`, jeśli kanał
ma być aktywny.

## Source czy channel?

Rekomendacja:

* `source` opisuje typ źródła rozmowy i wybór ikony,
* `channel` opisuje singletonowy kanał komunikacji.

Minimalny kontrakt Sprintu 46:

```json
{
  "source": "world",
  "channel": "world",
  "scope": "group",
  "peer": "global",
  "title": "WORLD"
}
```

Dla prywatnej rozmowy:

```json
{
  "source": "player",
  "channel": null,
  "scope": "direct",
  "peer": "username"
}
```

Dla systemowego źródła:

```json
{
  "source": "ghost_exchange",
  "channel": null,
  "scope": "direct",
  "peer": "Ghost Exchange"
}
```

Dla klanu:

```json
{
  "source": "clan",
  "channel": "clan",
  "scope": "channel",
  "peer": "clan:<clan_id_or_name>",
  "title": "KLAN"
}
```

`scope = channel` jest opcjonalnym kierunkiem Sprintu 46. Jeśli da się uniknąć
zmiany walidacji backendu, kanał może najpierw działać jako read model. Nie
wolno jednak tworzyć `channel_store`.

## Ryzyka

Największe ryzyka:

* potraktowanie kanału jako kontaktu,
* dodanie kanałów przez `/api/contacts`,
* rozpoznawanie ikon po tytule zamiast po `source`,
* duplikacja `WORLD` / `FRIENDS` / `CLAN` po każdym bootstrapie,
* stworzenie osobnego `channel_store`,
* stworzenie drugiego inboxa dla systemów świata,
* pomieszanie pending requests z kanałami.

## Kontrakt Sprintu 46

Sprint 46 powinien:

1. Zmienić widoczną nazwę publicznego kanału z `# grupa` na `WORLD`.
2. Dodać klucze `world`, `friends`, `clan` do `CYBERNER_ICON_LIBRARY`.
3. Używać `source` do wyboru ikon.
4. Traktować `WORLD`, `FRIENDS`, `CLAN` jako singletony.
5. Nie zapisywać kanałów w `contacts`.
6. Nie dodawać `channel_store`.
7. Nie dublować prywatnych threadów ani pending requests.
8. Jeśli backend wymaga rozszerzenia, dodać minimalne `source` / `channel` do
   read modelu, nie nową architekturę wiadomości.

## Decyzja

Architektura jest gotowa do Sprintu 46, pod warunkiem że Sprint 46 potraktuje
kanały jako singletonowy read/runtime model nad istniejącym `mail_store`, a nie
jako nowy system wiadomości.

## Decyzje implementacyjne Sprintu 46

Sprint 46 wdrożył minimalny read/runtime kanałów w istniejącym
`/api/mail/bootstrap`.

Backend zwraca teraz listę `channels`, ale nie zapisuje kanałów jako kontaktów i
nie tworzy żadnego `channel_store`.

Wdrożone kanały:

* `WORLD` — aktywny, mapuje się na istniejące `scope = group`,
  `peer = global`.
* `ZNAJOMI` — singletonowy placeholder, oparty o liczbę istniejących kontaktów,
  bez aktywnego runtime wiadomości.
* `KLAN` — singletonowy placeholder widoczny tylko, jeśli profil ma `clan`, bez
  aktywnego runtime wiadomości klanowych.

`source` wybiera typ źródła i ikonę.

`channel` identyfikuje singleton kanału.

Frontend renderuje kanały w osobnej sekcji nad prywatnymi rozmowami. Disabled
placeholdery nie uruchamiają `/api/chats/messages`, nie tworzą kontaktu i nie
generują pending request.
