# Wdrożenie 153 — powłoka PL/EN

Pakiet językowy `153.4`, 496 kluczy PL/EN. EN pozostaje testowe.
Nie ma nowych zależności ani migracji bazy. Nie uruchamiaj naprawy FM ani
inicjalizacji profili przy tym wydaniu. 149–152 pozostają zamrożone.

Komendy na VPS, pojedynczo; po błędzie zatrzymaj wdrożenie.

## 1. Stan i pobranie

```bash
cd ~/app/chaos
git status --short
git rev-parse HEAD > /tmp/chaos-before-153.commit
git pull --ff-only origin main
git log -1 --oneline
```

Oczekiwane: czyste repo przed pull; najnowszy commit
`feat: complete sprint 153 bilingual system shell`. Jeśli są lokalne zmiany,
nie resetuj ich ani nie nadpisuj. Zapis poprzedniego SHA służy rollbackowi.

## 2. Testy izolowane

```bash
.venv/bin/python tools/run_isolated_tests.py tests.test_ghost_i18n tests.test_registration_locale tests.test_desktop_settings_writer tests.test_file_manager_inventory tests.test_session_generation_isolation tests.test_terminal_geolocation_command tests.test_shell_locale tests.test_wallet_runtime_cutover tests.test_wallet_canonical_boundary
```

Oczekiwane: `Ran 105 tests`, `OK`. Dane testowe w katalogu tymczasowym.

```bash
node tests/js/test_ghost_i18n.js &&
node tests/js/test_ghost_i18n_runtime.js &&
node tests/js/test_locale_frame.js &&
node tests/js/test_registration_locale.js &&
node tests/js/test_terminal_pkg.js &&
node tests/js/test_wallet_transfer_idempotency.js &&
node --check static/js/terminal.js
```

Oczekiwane: sześć wyników PASS/OK; kontrola składni bez błędu.
Testy fallbacku celowo wypisują diagnostykę `missing_key`.

## 3. Przeładowanie aplikacji

```bash
pm2 reload chaos
pm2 status
pm2 logs chaos --lines 60 --nostream
```

Oczekiwane: `chaos` online, bez nowych tracebacków przy starcie.
Worker terytoriów i Ollama nie wymagają restartu; limit CPU Ollamy pozostaje.

```bash
curl -fsS https://chaos.re/static/locales/manifest.json
curl -fsS https://chaos.re/ -o /tmp/chaos-153-login.html
grep -F 'ghost-i18n-bootstrap' /tmp/chaos-153-login.html
```

Oczekiwane: manifest `content_version: 153.4`, PL/EN, domena `shell`;
strona logowania zawiera bootstrap językowy. Jeśli statyki korzystają z cache
proxy/CDN, sprawdź zgodność wszystkich domen z manifestem.

## 4. Odbiór produkcyjny

Odśwież pulpit, aby załadować nową wersję JS i katalogów. Sprawdź PL → EN → PL
z otwartym FM, terminalem, profilem, portfelem i niezapisanym formularzem.
Po ponownym logowaniu język konta ma pozostać zapisany; inne konto zachowuje
własny język. Na mobile input musi pozostać nad belką w zwykłym i powiększonym
oknie oraz przy fullscreen gry. Nie wykonuj przelewu tylko do testu wyglądu.
UGC i dokumenty `/about`, `/tips-tricks` pozostają dosłowne.

## Rollback kodu

Jeśli wydanie wymaga cofnięcia, przy czystym repo:

```bash
git switch --detach "$(cat /tmp/chaos-before-153.commit)"
pm2 reload chaos
pm2 status
```

Bez cofania bazy i bez usuwania zapisanych preferencji locale. Odśwież strony
klientów po rollbacku. Powrót na linię wydań: `git switch main` po przygotowaniu
poprawki. Wyniki lokalne: `doc/audits/sprint_153_acceptance.md`.
