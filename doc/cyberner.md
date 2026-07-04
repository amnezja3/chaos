# Cyberner

Cyberner to diegetyczna nazwa komunikatora w CHAOS.

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

* `# grupa` — globalny czat online graczy,
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

Ikony źródeł Cybernera są osobną biblioteką frontendową:

```text
CYBERNER_ICON_LIBRARY
```

Nie korzystają z globalnej biblioteki ikon systemowych. Dzięki temu komunikator
może mieć własny język wizualny i nadal pozostać zgodny z istniejącym runtime.

## Zasady integracji

Cyberner nie tworzy nowego backendu.

Cyberner korzysta z istniejących systemów:

* `mail_store`,
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
