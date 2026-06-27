class AvatarSelector {
    /**
     * ✅ AvatarSelector — klasa do dynamicznego wyboru i podglądu awatara
     *
     * 📌 Co robi:
     * - Pozwala użytkownikowi przeglądać i wybierać avatary poprzez przyciski.
     * - Po najechaniu myszką na przycisk, obrazek zmienia się tymczasowo (podgląd).
     * - Po kliknięciu przycisku:
     *    - obrazek zostaje ustawiony jako domyślny,
     *    - nazwa avatara pokazuje się w polu informacyjnym,
     *    - kliknięty guzik zostaje wizualnie zaznaczony (klasa .selected).
     *
     * 📦 Jak używać:
     *
     * ✅ HTML (to musisz mieć):
     * - 🖼️ #avatar-preview — kontener, gdzie wyświetlany będzie obrazek jako tło
     * - 📛 #avatar-info — miejsce, gdzie będzie pokazywana nazwa avatara
     * - 🔘 .avatar-button — przyciski z atrybutami:
     *     - data-img="ścieżka/do/obrazka.jpg"
     *     - data-name="Nazwa avatara"
     *
     * Przykład przycisku:
     * <button class="avatar-button" data-img="img1.jpg" data-name="Tatry">1</button>
     *
     * ✅ JavaScript:
     * Wywołaj po załadowaniu DOM:
     *
     * new AvatarSelector({
     *   imageContainer: "#avatar-preview",
     *   infoContainer: "#avatar-info",
     *   buttonSelector: ".avatar-button",
     *   defaultImage: "default.jpg"
     * });
     *
     * 💡 Co warto wiedzieć:
     * - Obrazek to tło (background-image) — dla lepszej kontroli stylów.
     * - Stylowanie aktywnego przycisku przez klasę .selected.
     * - Można łatwo rozbudować o zapis do localStorage, formularze, API itd.
     *
     * ✍️ Autorzy i Uczestnicy:
     * - 🧠 Michał „amnezja3” Jankiewicz — pomysł, koncepcja UI, flow, kierunek
     * - 🟩 Lin — kodowanie klasy, logika stanu, mechanika JS
     * - 🟦 Korynt / Carent — dokumentacja, architektura UX, słowo ludzkie
     * - 🔴 Brak / Ferrun — testy, refaktory, siła brutalna, weryfikacja błędów
     *
     * 🔥 Edycja: wersja 1.0 — gotowa do boju w Twoim projekcie
     */

    constructor({ imageContainer, infoContainer, buttonSelector, defaultImage }) {
        this.imageContainer = document.querySelector(imageContainer);
        this.infoContainer = document.querySelector(infoContainer);
        this.buttons = document.querySelectorAll(buttonSelector);
        this.defaultImage = defaultImage;
        this.currentImage = defaultImage;
        this.selectedButton = null;

        this.init();
    }

    init() {
        this.imageContainer.style.backgroundImage = `url('${this.defaultImage}')`;

        this.buttons.forEach(button => {
        const imgSrc = button.dataset.img;
        const name = button.dataset.name;

        button.addEventListener("mouseover", () => {
            this.imageContainer.style.backgroundImage = `url('${imgSrc}')`;
        });

        button.addEventListener("mouseout", () => {
            this.imageContainer.style.backgroundImage = `url('${this.currentImage}')`;
        });

        button.addEventListener("click", () => {
            this.currentImage = imgSrc;
            this.imageContainer.style.backgroundImage = `url('${imgSrc}')`;
            this.infoContainer.textContent = `Wybrano: ${name}`;

            if (this.selectedButton) {
            this.selectedButton.classList.remove("selected");
            }

            button.classList.add("selected");
            this.selectedButton = button;
        });
        });
    }
  }

/*
✅ Założenia:

    Inicjalizacja przez klasę AvatarSelector

    Możesz przekazać:

        kontener z obrazkiem

        kontener z informacją tekstową

        listę przycisków (dowolna liczba)

    Atrybuty data-img i data-name — trzymamy nadal

✅ Użycie:
document.addEventListener("DOMContentLoaded", () => {
  const selector = new AvatarSelector({
    imageContainer: "#avatar-preview",
    infoContainer: "#avatar-info",
    buttonSelector: ".avatar-button",
    defaultImage: "default.jpg"
  });
});

✅ 🎨 CSS (możesz dostosować)

.avatar-box {
  width: 400px;
  height: 300px;
  background-size: cover;
  background-position: center;
  border: 2px solid #ccc;
  margin-bottom: 20px;
}

.avatar-button {
  padding: 10px;
  margin: 5px;
  cursor: pointer;
}

.avatar-button.selected {
  border: 3px solid #00aaff;
  background-color: #e0f7ff;
}

.avatar-info {
  font-size: 18px;
  margin-top: 10px;
  padding: 10px;
  border: 1px dashed #888;
  color: #333;
  width: 400px;
}

✅ 🔧 HTML (minimum struktury, elastyczne)

<div id="avatar-preview" class="avatar-box"></div>
<div id="avatar-info" class="avatar-info">Wybierz swojego avatara</div>

<div class="avatar-buttons">
  <button class="avatar-button" data-img="img1.jpg" data-name="Tatry">1</button>
  <button class="avatar-button" data-img="img2.jpg" data-name="Bałtyk">2</button>
  <button class="avatar-button" data-img="img3.jpg" data-name="Mazury">3</button>
  <button class="avatar-button" data-img="img4.jpg" data-name="Bieszczady">4</button>
</div>
*/