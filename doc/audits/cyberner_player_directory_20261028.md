# Cyberner — wspólne wyszukiwanie i kontakty, 28.10.2026

Przyczyna: rejestracja przez Identity Gateway (`identity_gateway/web.py`) nadaje
stałe `username=id_<losowy token>` i osobny publiczny `nick`. Dotyczy tego samego
procesu rejestracji dla Google, Discord, Steam i GitHub. Poprzednia poprawka
wyświetlania nicków w wiadomościach nie dodała wyszukiwania. Pole podpisane
„Nick znajomego” wysyłało tekst jako login do `/api/contacts`; formularz safety
również wymagał loginu. Nick nie był rozwiązywany do właściwego konta.

## Kontrakt

- Nick: publiczna, zmienna etykieta. Wyszukiwanie fragmentu, NFKC/casefold,
  zgodnie z normalizacją rejestracji. Konta historyczne mogą mieć niejednoznaczne
  nazwy; wybieramy konkretny wynik, nie pierwszy przypadkowy rekord.
- `@username`: jednoznaczne ID CHAOS, np. `@main` lub `@id_…`. To prezentacja
  istniejącego klucza, nie nowy numer ani zmiana kluczy w bazie. ID z `@` zachowuje
  wielkość liter; nick można wyszukiwać bez rozróżniania wielkości liter.
- Profil gracza na mapie pokazuje `ID CHAOS / Cyberner` z tym samym `@username`.
  Mapowe akcje nadal wysyłają kanoniczne `actor.username`.
- `player:<username>` to identyfikator celu mapy, a ID konfliktów/operacji odnoszą
  się do innych obiektów. Nie są wejściem wyszukiwarki kontaktów.
- Provider subject, email i liczbowe wewnętrzne ID użytkownika nie są publicznym
  identyfikatorem kontaktu. Katalog nie odczytuje ani nie zwraca tych danych.

## Zmiany

`GET /api/players/search?q=…`: zalogowana, aktualna sesja, 2–100 znaków,
do 20 wyników + sygnał zawężenia. Odczyt publicznych pól z projekcji tożsamości,
bez skanowania JSON profili; nieaktualna projekcja nie staje się wynikiem.
Znaki `%` i `_` są literalne. Brak cache odpowiedzi katalogu.

Wspólny komponent `player_directory.js` dla Cybernera i strony kontaktów/safety.
Wynik pokazuje nick i @ID. Cyberner przekazuje wybrane konto do zaproszenia,
zamiast tworzyć kontakt pod wpisaną etykietą. Safety zachowuje CSRF, generację
sesji, ograniczenia komunikacji, rate limit, akceptację i blokady. Starszy endpoint
kontaktów rozwiązuje dokładny nick/@ID; niejednoznaczność kończy się błędem.
Zaproszenia i lista blokad pokazują nick wraz z ID, operacje pozostają po ID.

## Sprawdzenie lokalne

- `test_player_directory.py`: 5 PASS — cztery formaty kont z bramek, Unicode,
  @ID, kolizje, zmiana nicku, limit wyników, brak emaili, anonimowy dostęp,
  zaproszenie/duplikat/akceptacja/blokada/CSRF, legacy kontakt po nicku.
- `test_communication_safety_web.py`: 8 PASS.
- `test_cyberner_public_names.py`: 2 PASS.
- `test_identity_projection.py`: 4 PASS.
- Playwright MCP, `tests/browser/player_directory.js`: rzeczywisty desktop
  i Cyberner oraz safety API na izolowanej bazie; PL 1440 px / EN 390 px,
  cztery konta, wybór, zaproszenie, akceptacja i @ID. Renderer profilu mapy
  testowany osobno z produkcyjnego szablonu, bez kafli i workerów mapy.
  Brak błędów JS/błędów żądań katalogu i safety; fixture desktopu zwracał dwa
  niezwiązane 409 dla `/launch-queue` przy wyłączonym kontrolerze launch.
  Nie jest to test rzeczywistych logowań u dostawców OAuth. Fixture i przeglądarka
  zamknięte po teście. Składnia JS i `git diff --check` sprawdzone.

## Wdrożenie

Nie wymaga migracji danych, zmiany tożsamości ani ponownego logowania do bramek.
Po pushu, na VPS z obecną konfiguracją:

```bash
cd ~/app/chaos && git pull --ff-only &&
.venv/bin/python -m unittest discover -s tests -p test_player_directory.py &&
.venv/bin/python -m unittest discover -s tests -p test_communication_safety_web.py &&
.venv/bin/python -m unittest discover -s tests -p test_cyberner_public_names.py &&
.venv/bin/python -m unittest discover -s tests -p test_identity_projection.py &&
pm2 startOrReload ecosystem.web.config.js --only chaos --env world_maplark_region --update-env
```

Odświeżyć pulpit, wyszukać znany nick konta bramkowego, wybrać wynik i wysłać
zaproszenie; na drugim koncie zaakceptować. @ID z profilu mapy powinien wskazać
ten sam wynik. To końcowy smoke produkcyjny; całą ścieżkę już sprawdzono lokalnie.
Po poprawnym odbiorze `pm2 save`. Kolektor POI i hierarchia źródeł nie zmieniają się.
