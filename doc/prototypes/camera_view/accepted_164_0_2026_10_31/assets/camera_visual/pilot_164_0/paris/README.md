# Paryż — obrazy testowe pilota 164.0

Trzy syntetyczne obrazy zamówione przez operatora 31.10.2026, wygenerowane
wbudowanym narzędziem image_gen. Jedno fikcyjne otoczenie kamery sklepu:

- `paris-01-dusk.png` — zmierzch po deszczu, kadr bazowy.
- `paris-02-night.png` — wariant nocny kadru bazowego.
- `paris-03-dawn.png` — wariant poranny tego samego widoku.

Służą do sprawdzenia prezentacji w pilocie, nie przedstawiają zweryfikowanej
lokalizacji `48.864173348628704, 2.330499567661377`. Nie są fotografiami
Mapillary, materiałem graczy ani transmisją live. Nie przypisywać im CC0
lub licencji zdjęcia Wałowej z wcześniejszego demonstratora.

W podglądzie pokazywać: **Materiał testowy wygenerowany AI — fikcyjny widok Paryża**.
Obrazy nie zawierają HUD, ramki aplikacji ani efektów zakłóceń; te należą do UI.
Warianty oświetlenia nie oznaczają rzeczywistych godzin rejestracji.

Pełne prompty i pochodzenie: [generation.json](generation.json).
Materiały są podłączone do pilota przez autoryzowany endpoint
`/api/camera-visual/media/<receipt>/<frame>`, po weryfikacji aktywatora.
