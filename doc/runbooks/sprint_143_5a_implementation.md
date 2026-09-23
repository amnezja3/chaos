# 143.5a — show konsekwencji i widok więzienia

Implementacja lokalna, 23 IX 2026. Nie oznacza wdrożenia ani odbioru wizualnego.

- Prywatna delta powstaje atomowo z wykonaniem kary; claim właściciela receipt
  ma trwałe dedupe między kartami oraz maksymalny wiek 60 s.
- Stopnie 1–9 mają komplet PNG/SFX. Ponowna kontrola: 9 par, PNG 540×540 RGBA,
  łącznie PNG 5 354 999 B, MP3 539 922 B. Fallbacki według audytu assetów.
- PNG jest dekodowane przed SFX; błędne lub wolne ładowanie po 1,5 s pomija
  obraz. Start/koniec GameSfx steruje show, wyciszenie używa długości fallback.
- Mapa pozostaje dostępna na wszystkich stopniach. Stały podstawowy close zoom,
  fokus na zapisane więzienie, ciemna warstwa 60%, brak pan/zoom. Zwolnienie
  przywraca sterowanie. Żadna droga skanu/celowania/ruchu/supermocy nie jest
  odblokowana. GhostNetwork snapshot dopuszczony wyłącznie w widoku mapowym.
- Belka więzienia otwiera CHAOS z czasem wyroku, nazwą więzienia, zasadami
  wiadomości oraz kaucją. Przycisk płatności wymaga kanonicznego salda.

Walidacja: 40 istniejących testów backendu konsekwencji/transportu/capability,
4 nowe testy claim (privacy, race, expiry, rollback i endpoint), 8 testów
kontraktu SFX. Testy JS: GameSfx, show, mapa aresztu, capability, self-bail,
czyszczenie celu, transport, odmowa podróży i kaucja. Sprawdzenie składni JS
i `git diff --check` bez błędów. Bazy testowe są izolowane od danych gry.

Po wdrożeniu kodu zrestartować web i territory worker; odświeżyć desktop/mapę.
Tabela claim powstaje automatycznie przy inicjalizacji DetentionService.
Nie resetować kartotek ani nie odtwarzać historycznych kar.

Odbiór w grze:

1. Nowa wykonana kara: jeden właściwy PNG i SFX, bez podwójnego warning audio.
2. Areszt: przyciemniona mapa więzienia, brak oddalania/przesuwania także na 9;
   po krótkim show czytelne okno wyroku i kaucji, ponownie dostępne z belki.
3. Mute, zamknięta mapa i reconnect: brak opóźnionego SFX/historycznego show;
   komunikat systemowy nadal dostępny. Dwie karty: najwyżej jedno show.
4. Zwolnienie: powrót do zapisanej pozycji i sterowania, bez przywrócenia celu.
5. Mobile i odsłuch wszystkich wariantów pozostają do potwierdzenia wizualnego.
