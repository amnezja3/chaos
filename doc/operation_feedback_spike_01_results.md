# OFS-SPIKE-01 — wyniki scan_ports

Data: 2026-08-09

Decyzja architektoniczna: `GO`

Zakres decyzji: można rozpocząć generalizację engine'u w `130.8.6.4`.
Decyzja nie włącza OFS na produkcji i nie jest zgodą na cutover kolejnych akcji.

## Co potwierdzono

1. Jeden scheduler tworzy różne przebiegi bez scenariuszy per aplikacja.
2. Dramaturgia scen i techniczne warianty security pozostają rozdzielone.
3. Każda techniczna linia pochodzi z jawnej pary `security -> interaction`.
4. Trzy wybory `feedback.*` zmieniają wyłącznie lokalny `presentation_state`.
5. `MASKUJ` wpływa na kilka kolejnych scen, bez zmiany requestu i gameplayu.
6. Dwie aplikacje używają jednego profilu, ale zachowują własne komendy i logi.
7. Payload przed rozwiązaniem loadera i podczas aktywnego wyboru zatrzymuje dalszy render.
8. Priorytet contentu działa jako `app_structured -> app_legacy -> global_fallback`.

## Deterministyczne transkrypty

Poniższe próbki generuje ten sam composer z kontrolowanym zegarem i RNG.

### Szybki — Quiet Mapper

```text
[instant/boot]
quiet-map --ports
Trasa skanu gotowa.
Budowanie lokalnego profilu skanu.

[instant/probe]
passive service sampling
Odpowiedz detektora zaobserwowana.
Sonda przechodzi do kolejnego zakresu.
```

### Średni — Neon Scanner + MASKUJ

```text
[short/probe]
burst channel sweep
Odpowiedz detektora zaobserwowana.
Maskowana sonda utrzymuje niski profil widocznosci.

[medium/verification]
burst channel sweep
Sprawdzanie odpowiedzi rdzenia firewalla.
Weryfikacja zachowuje maskowany profil sondy.

[medium/security_contact]
burst channel sweep
Odpowiedz detektora zaobserwowana.
Sprawdzanie odpowiedzi rdzenia firewalla.
Kolejny kontakt wykorzysta maskowana trase.
```

### Długi — Quiet Mapper + TRYB SZYBKI

```text
[short/probe]
passive service sampling
Odpowiedz detektora zaobserwowana.
Szybki rytm przygotowuje rozszerzony zakres.

[long/security_contact]
passive service sampling
Odpowiedz detektora zaobserwowana.
Sprawdzanie odpowiedzi rdzenia firewalla.
Kontakt techniczny pozostaje aktywny.

[very_long/verification]
passive service sampling
Odpowiedz detektora zaobserwowana.
Wynik pozostaje niepotwierdzony.
```

## Luki pozostawione świadomie

* 6.3 obsługuje tylko renderer `button_choice` i `scan_ports`.
* Strukturalny `feedback_content` ma runtime projection, ale kreatory nie mają
  jeszcze edytora ani preview — to pozostaje w dalszym planie cutoveru.
* Transport library nie jest losowana i czeka na podłączenie prawdziwych
  sygnałów HTTP/network w późniejszym sprincie.
* Telemetria używa istniejącego `APP_FLOW`; shadow telemetry i agregacja jakości
  nie są częścią spike'a.
* Produkcyjne treści wymagają późniejszej redakcji i testu mobilnego UI.

Żadna z tych luk nie wymaga wyjątku per aplikacja ani naruszenia kontraktu
schedulera, dlatego wynik spike'a to `GO`.
