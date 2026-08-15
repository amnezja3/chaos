# OFS SFX assets

Opcjonalne, lokalne pliki MP3 dla semantycznego lifecycle aplikacji:

- `01_intro.mp3`
- `02_choice_available.mp3`
- `03_choice_confirmed.mp3`
- `04_progress_checkpoint.mp3`
- `05_success.mp3`
- `06_failure.mp3`
- `07_runtime_warning.mp3`

Brak pliku jest obsługiwany przez negative cache `GameSfx` i nie może zmieniać
requestu, payloadu, timingu gameplayu ani lifecycle okna. Asset powinien mieć
krótki początek bez ciszy, naturalny koniec i peak dopasowany do wartości
`volume` w manifeście.
