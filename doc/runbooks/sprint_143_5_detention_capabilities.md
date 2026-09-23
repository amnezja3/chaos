# 143.5 — aplikacje, Cyberner i kaucja

22 IX 2026: implementacja gotowa do wspólnego wdrożenia 143.2–143.5.
`CHAOS_RESPONSE_DETENTION_ENABLED=true` zapisano we wszystkich czterech
ecosystemach. Nie uruchamiano ani nie restartowano serwera z tego workspace.
Po wdrożeniu odświeżyć także dokument desktopu, aby wczytać nowy JS.

Reguły pochodzą ze snapshotu zapisanego wyroku (`plan_json`), nie z poziomu
incydentu zmieniającego się później. Rejestr i wspólny odczyt capabilities:
`response_network/capabilities.py`. Brak wyroku zachowuje dotychczasowy dostęp.

| Stopień | World | Pozostałe kanały | Aplikacje |
|---|---|---|---|
| 6 | Czytanie i pisanie | Jedno wysłanie łącznie; czytanie bez blokady | Zwykły dostęp, bez ruchu/teleportów |
| 7 | Tylko czytanie | Jak wyżej | Jak wyżej |
| 8 | Niedostępny | Jak wyżej | Jak wyżej |
| 9 | Niedostępny | Jak wyżej, mimo ograniczenia aplikacji | Web Dragon, radio i wyjątek prywatnego Cybernera |

## Wysłanie i odbiór

`response_network/chat_delivery.py` łączy autoryzację World, rezerwację
jednego wysłania, faktyczny zapis/fan-out oraz receipt w jednej transakcji.
Oba istniejące store (wspólne kanały i starsze rozmowy) przyjmują wspólne conn.
Limit jest jeden dla direct, klanu, znajomych i innych kanałów poza World.
Błąd walidacji/dostarczenia nie zużywa limitu. Dwie karty nie wysyłają dwóch
wiadomości; retry z tym samym kluczem i treścią zwraca poprzednią wiadomość.
Zmiana treści lub kanału z tym samym kluczem jest odrzucana.

Odbiór i historia prywatnych rozmów pozostają dostępne. Przynależność do klanu
i pozostałe reguły dostępu nadal obowiązują. Automatyczne komunikaty systemowe
nie zużywają wysłania gracza. Gest zaproszenia do znajomych jest podczas aresztu
zablokowany, bo generowałby dodatkową wiadomość poza kontrolowanym wysłaniem;
dodanie kontaktu do własnej listy i napisanie przez Cybernera pozostają możliwe.

Blokada World obejmuje historię, podgląd bootstrapu, licznik nieprzeczytanych,
delty live i treść powiadomień systemowych. Odfiltrowanie delt zachowuje
serwerowy kursor, więc klient nie wraca bez końca do ukrytej wiadomości.

## Backend i interfejs

Na stopniu 9 jawna lista dopuszcza tylko endpointy powłoki/sesji,
statusu/kaucji, komunikatów, prywatnego Cybernera, katalogów/newsów Web Dragona
i radia. Nieznane endpointy są zablokowane. Ograniczenia obejmują bezpośrednie
API, terminal i wcześniej otwarte aplikacje. Bramka przed żądaniem oraz przed
commit chroni przed wyrokiem nadanym w trakcie akcji. Ruch ma dodatkową,
niezależną bramkę pozycji z 143.3 na każdym stopniu.

`static/js/detention.js` pokazuje więzienie i czas online w miejscu CEL, blokuje
otwarte niedozwolone okna i przywraca je po zwolnieniu. To prezentacja stanu
serwera, bez lokalnego zakończenia wyroku według zegara przeglądarki.
Web Dragon ma tożsamość `browser`; radio `ghost-radio` / `ghost_hack_radio`;
Cyberner `email` / `cyberner`.

Od 23 IX przycisk **Kaucja** występuje przy wiadomości wysłanej z aresztu,
pod adnotacją cenzury prokuratorskiej. Pobiera ofertę z serwera i pokazuje
potwierdzenie CHAOS, związane z konkretnym wyrokiem. Serwer pobiera pieniądze
wyłącznie od zalogowanego płatnika i przekazuje na konto `admin`,
według zapisanej kwoty wyroku. Status i opłacenie kaucji są dostępne również
podczas globalnego show GhostSignal. Nie wymagają uruchomienia portfela.
Szczegóły i korekta wcześniejszej wpłaty:
[kaucja, Cyberner i skarbiec](sprint_143_bail_cyberner_treasury.md).

## Odbiór w grze

Walidacja 22 IX 2026: 56 różnych testów Pythona zakończonych PASS w pakietach
capabilities, HTTP Cybernera, store/migracji i routingu Cybernera, sankcji,
transportu oraz ruchu; 4 testy JS (capabilities, transport, odmowa podróży,
adresowanie powiadomień Cybernera). Dodatkowo kontrola składni JS i diff.
Test wyścigu potwierdza, że blokada nie unieważnia sesji, a test stopnia 9
sprawdza commit nowego aresztu z żądania wykrycia patrolu.

Wdrożenie backendu i workera z aktualnym środowiskiem:

```sh
pm2 startOrRestart ecosystem.web.config.js --update-env
pm2 startOrRestart ecosystem.territory-worker.config.js --update-env
```

Ollama i publisher nie nakładają kar; ich ecosystemy zawierają tę samą flagę
dla spójności konfiguracji. Jej wyłączenie zatrzymuje nowe areszty, ale nie
usuwa zapisanych wyroków i nie wyłącza ich bramek ani zwolnienia.

1. Nowy wyrok stopnia 6: transport, blokada ruchu, World nadal pozwala pisać.
2. Wyślij jedną wiadomość prywatną; kolejne wysłanie w direct/klanie/znajomych
   ma odmowę. Odpowiedź innego gracza nadal dociera. Powtórz po reconnectcie.
3. Stopień 7: World czytelny bez pisania. Stopnie 8–9: World niedostępny także
   w odświeżonym Cybernerze i powiadomieniach.
4. Stopień 9: wcześniej otwarte aplikacje są blokowane; Web Dragon, radio,
   prywatny Cyberner, wylogowanie i kaucja nadal działają.
5. Przerwa offline nie skraca wyroku. Odbycie lub kaucja przywraca pozycję
   i dostęp. Kaucję sprawdzić również z konta drugiego gracza.

143.5a (efekty PNG/SFX nadania konsekwencji) jest osobnym etapem.
Testy automatyczne nie zastępują odbioru autora w grze.
