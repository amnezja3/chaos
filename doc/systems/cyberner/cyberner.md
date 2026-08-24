# Cyberner

Cyberner to diegetyczna nazwa komunikatora w CHAOS.

## Stan runtime po Sprincie 130.8.7

Docelowym źródłem prawdy dla `WORLD` jest `CybernerWorldStore`, a dla `KLAN`
`CybernerClanStore`. `ZNAJOMI` i rozmowy direct świadomie pozostają w lokalnym
`MailStore`. Shared kanały mają cursory per użytkownik, idempotencję po
`client_message_id` i dostawę live przez delta-feed; polling służy do recovery.

Cutover jest chroniony niezależnymi flagami globalną, `WORLD`, `KLAN` i live
delivery. Szczegóły migracji i rollbacku: `doc/runbooks/cyberner_cutover_runbook.md`.

Od Fazy E aplikacja widoczna wcześniej jako Email / Skrzynka mailowa zmienia
tożsamość na Cyberner. Technicznie nadal korzysta z istniejącego `mail_store`,
kontaktów i endpointów wiadomości, ale w świecie gry przestaje być zwykłą
pocztą. Staje się interfejsem komunikacji z Ghost Systemem, graczami,
automatycznymi rynkami danych i zdarzeniami świata.

## Inspiracja

Nazwa nawiązuje do neologizmu Stanisława Lema z Cyberiady.

W lemowskim kontekście cyberner jest figurą cybernetycznego doradcy,
technika wyobraźni i inżyniera stanów wewnętrznych. To nie jest zwykły
operator maszyny. To ktoś, kto pośredniczy między królem, snem, aparatem
i opowieścią.

CHAOS adaptuje tę ideę w innym kierunku.

Cyberner nie steruje dosłownie snami gracza. Cyberner zarządza strumieniem
sygnałów, komunikatów, próśb, ostrzeżeń i szeptów systemu. Jest blisko motywu
ducha, bo działa na granicy:

```text
człowiek
↓
system
↓
wiadomość
↓
intencja
↓
ślad
↓
decyzja
```

To reinkarnacja idei cybernetycznego pośrednika: nie jako maszyna snu, tylko
jako komunikator świata, który tłumaczy cyfrowe zdarzenia na doświadczenie
gracza.

## Znaczenie w CHAOS

Cyberner jest miejscem, gdzie świat gry przemawia do gracza.

Nie jest tylko pocztą.

Nie jest tylko czatem.

Nie jest tylko listą powiadomień.

Cyberner łączy:

* rozmowy z graczami,
* kontakty i prośby o kontakt,
* komunikaty systemowe,
* wiadomości Ghost Exchange,
* ostrzeżenia świata,
* ślady konsekwencji operacji,
* przyszłe głosy frakcji, systemów i automatycznych agentów.

## Filozofia UX

Cyberner ma wyglądać jak komunikator, ale działać jak kanał świata.

Na desktopie może być rozbudowany:

```text
lista rozmów
↓
czat
↓
akcje kontaktu
↓
historia komunikacji
```

Na mobile i narrow ma być prosty:

```text
lista
↓
czat
↓
powrót
```

Gracz nie musi rozumieć `mail_store`, `system_messages`, `pending_threads`
ani `unread_counts`.

Gracz ma czuć, że Cyberner jest nerwem komunikacyjnym jego cyfrowego życia.

## Źródła Rozmów

Cyberner nie myśli folderami.

Cyberner pokazuje źródła komunikacji świata:

* `WORLD` — publiczny kanał świata gry,
* `ZNAJOMI` — kanał znajomych, jeśli runtime go udostępnia,
* `KLAN` — kanał klanu, jeśli profil ma przynależność klanową,
* gracze, znajomi i nieznajomi,
* AI Central,
* Ghost Exchange,
* System,
* Misje,
* przyszłe NPC,
* przyszłe frakcje,
* przyszły Marketplace,
* przyszłe usługi świata.

Każde źródło jest rozmową. Backend może nadal używać `mail_store` i
`system_messages`, ale UI nie powinno rozbijać świata na osobne inboxy ani
osobne centra powiadomień.

Kanały nie są kontaktami.

Kanał jest trwałym źródłem komunikacji świata. Kontakt jest prywatną rozmową z
graczem. Thread systemowy jest rozmową prowadzoną przez system gry albo źródło
świata.

Kanały `WORLD`, `ZNAJOMI` i `KLAN` powinny być traktowane jako singletony:
w jednym profilu może istnieć tylko jedna rozmowa danego typu kanału.

Ikony źródeł Cybernera są osobną biblioteką frontendową:

```text
CYBERNER_ICON_LIBRARY
```

Nie korzystają z globalnej biblioteki ikon systemowych. Dzięki temu komunikator
może mieć własny język wizualny i nadal pozostać zgodny z istniejącym runtime.

Ikona identyfikuje typ źródła, a nie nazwę rozmowy. Renderer powinien wybierać
ikonę po `source` albo `channel`, np. `source = clan` używa
`CYBERNER_ICON_LIBRARY.clan`. Nie powinien rozpoznawać ikony przez warunek typu
`title == "KLAN"`.

Docelowo kanał publiczny nazywa się `WORLD`. Techniczny identyfikator legacy
`group/global` może pozostać pod spodem, jeśli zmiana runtime byłaby ryzykowna.

W Sprintcie 46 `WORLD` jest aktywnym kanałem opartym o istniejący techniczny
thread `scope = group`, `peer = global`.

`ZNAJOMI` i `KLAN` mogą istnieć jako singletonowe placeholdery źródeł
komunikacji, jeśli backend nie ma jeszcze runtime wiadomości dla tych kanałów.
Placeholder kanału nie jest kontaktem i nie powinien uruchamiać contact flow.

## Polish społeczny

Cyberner może pokazywać społeczne sygnały tylko wtedy, gdy istnieje dla nich
źródło prawdy.

Dozwolone są:

* defensywne fallbacki,
* disabled placeholdery,
* wizualne rozróżnienie kanałów, kontaktów, pending i źródeł świata,
* kompaktowe unread badges,
* subtelne animacje aktywnego wątku.

Nie należy udawać aktywnych funkcji, których backend jeszcze nie obsługuje:

* typing,
* last seen,
* pin/favorite,
* mute,
* realny status online poza danymi dostarczanymi przez runtime.

## Kanały i klany

Cyberner rozpoczyna społeczną gałąź CHAOS.

Do tej pory przynależność do klanu była głównie informacją w profilu i wejściem
do wybranych mechanik mapy. Kanał `KLAN` jest pierwszym krokiem, w którym klan
zaczyna wpływać na komunikację świata gry.

Przyszłe systemy, takie jak wojny klanów, operacje grupowe, wspólne terytoria,
wydarzenia frakcyjne i misje klanowe, powinny korzystać z istniejącego Cybernera
oraz kanału `KLAN`, zamiast budować własne komunikatory.

## Zasady integracji

Cyberner nie tworzy osobnego inboxa per funkcja. Kanały współdzielone mają
jednak własne, kanoniczne store'y zamiast legacy fanoutu kopii per odbiorca.

Cyberner korzysta z istniejących systemów:

* `mail_store` dla `ZNAJOMI`, direct i kompatybilności legacy,
* `cyberner_world_store` i `cyberner_clan_store` dla wspólnych strumieni,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `/api/contacts`,
* `system_messages`,
* `openEmailChatWith()`.

Nazwa Email może pozostać wewnętrznym identyfikatorem legacy, jeśli zmiana
app-id byłaby ryzykowna. Widoczna nazwa produktu, aplikacji i UI powinna jednak
przechodzić na Cyberner.

## Ton świata

Cyberner nie jest neutralnym klientem poczty.

To narzędzie Ghost Systemu.

Ma być:

* osobiste,
* lekko niepokojące,
* użytkowe,
* szybkie,
* bliskie graczowi,
* zdolne do przenoszenia głosu świata gry.

Jego komunikaty nie powinny brzmieć jak formularz administracyjny. Powinny być
krótkie, konkretne i osadzone w fikcji CHAOS.

## Decyzja

Przyjęto:

* Email / Skrzynka mailowa zmienia nazwę użytkową na Cyberner.
* Faza E rozwija Cybernera jako komunikator świata gry.
* Backend mailowy pozostaje źródłem prawdy.
* Nazwa Cyberner jest warstwą świata, UX i dokumentacji.
* Implementacja nazwy w UI powinna następować stopniowo, bez łamania legacy
  identyfikatorów aplikacji.

## Aktywne kanały Sprintu 48

W Sprincie 48 `ZNAJOMI` i `KLAN` stają się aktywnymi kanałami Cybernera.

* `ZNAJOMI` używa `scope = channel`, `peer = friends` i rozsyła wiadomości do
  zaakceptowanych kontaktów gracza.
* `KLAN` używa `scope = channel`, `peer = clan:<clan_name>` i rozsyła wiadomości
  do profili z tym samym klanem.
* `KLAN` jest widoczny tylko wtedy, gdy profil ma klan.
* Kanały nadal nie są kontaktami, nie trafiają do `/api/contacts` i nie tworzą
  pending request.
* `WORLD` pozostaje kompatybilnie oparty o `scope = group`, `peer = global`.

## Notification Bridge Sprintu 49

Cyberner korzysta z istniejacego `system_messages` jako mostu do toastow.

Toast Cybernera:

* jest tylko krotkim sygnalem,
* nie pokazuje pelnej tresci rozmowy,
* zawiera zrodlo, ikone i krotki komunikat,
* po kliknieciu otwiera odpowiedni thread Cybernera,
* nie pojawia sie, gdy gracz juz czyta dany thread.

Most nie tworzy drugiego inboxa, drugiego toast systemu ani drugiego unread
managera.
