let currentStep = 0;
let typewriterTimer = null;
let isSubmitting = false;

let formData = {
  username: "",
  faction: "",
  role: "",
  password: "",
  confirm_password: "",
  email: "",
  nick: "",
  avatarImage: ""
};

const stepImages = {
  0: "/static/images/install/step1.jpg",
  1: "/static/images/install/step2.jpg",
  2: "/static/images/install/step3.jpg",
  3: "/static/images/install/step4.jpg",
  4: "/static/images/install/step5.jpg",
  5: "/static/images/install/step6.jpg"
};

const rolesByFaction = {
  1: ["Analizator", "Obronca", "Rekonstruktor", "Mediator", "Egzekutor"],
  2: ["Haktywista", "Socjotechnik", "Odslaniacz", "Wizjoner", "Zapalnik"],
  3: ["Broker", "Architekt", "Manipulator", "Egzekutor Zysku", "Kurator Algorytmu"],
  4: ["Iluzjonista", "Wirusolog", "Paranoik", "Rozlamowiec", "Lustrzany Sedzia"]
};

const factions = [
  { id: 1, name: "Straznicy Ladu", icon: "ORDER", image: "/static/images/logo_faction_img_1.png", summary: "Kontrola, stabilnosc i odbudowa sieci." },
  { id: 2, name: "Echo Wolnosci", icon: "ECHO", image: "/static/images/logo_faction_img_2.png", summary: "Jawne slady, wolne pakiety, antysystem." },
  { id: 3, name: "VIREX", icon: "VIRX", image: "/static/images/logo_faction_img_3.png", summary: "Rynek exploitow, zysk i ciche przejecia." },
  { id: 4, name: "Siatka Widmo", icon: "GHOST", image: "/static/images/logo_faction_img_4.png", summary: "Maskowanie, iluzja i operacje bez podpisu." }
];

const avatarData = {
  1: ["avatar-frakcja-1-player-1.png", "avatar-frakcja-1-player-2.png", "avatar-frakcja-1-player-3.png", "avatar-frakcja-1-player-4.png", "avatar-frakcja-1-player-5.png"],
  2: ["avatar-frakcja-2-player-1.png", "avatar-frakcja-2-player-2.png", "avatar-frakcja-2-player-3.png", "avatar-frakcja-2-player-4.png", "avatar-frakcja-2-player-5.png"],
  3: ["avatar-frakcja-3-player-1.png", "avatar-frakcja-3-player-2.png", "avatar-frakcja-3-player-3.png", "avatar-frakcja-3-player-4.png", "avatar-frakcja-3-player-5.png"],
  4: ["avatar-frakcja-4-player-1.png", "avatar-frakcja-4-player-2.png", "avatar-frakcja-4-player-3.png", "avatar-frakcja-4-player-4.png", "avatar-frakcja-4-player-5.png"]
};

const prelogContent = [
  {
    image: "/static/images/epizod-1.png",
    title: "GHOSTSYSTEM // pakiet z przeszlosci",
    text: "Rok 2108. MASA kontroluje miasta, trasy, banki i prywatne wspomnienia. Wlasnie odebrales pakiet, ktorego nie powinno byc w zadnym rejestrze. Pierwszy krok: nadaj sobie login."
  },
  {
    image: "/static/images/epizod-2.png",
    title: "Frakcje // komu zaufasz",
    text: "GhostSystem przetrwal dzieki rozproszonym frakcjom. Kazda widzi siec inaczej i kazda placi inna cene za przewage. Wybierz szyld, pod ktorym rozpoczniesz operacje."
  },
  {
    image: "/static/images/epizod-3.png",
    title: "Rola // twoj pierwszy slad",
    text: "Frakcja daje kierunek, ale rola definiuje styl wejscia. Bedziesz czytal ruch, chronic dostep, manipulowac rynkiem czy znikac z radarow? Wybierz operatora."
  },
  {
    image: "/static/images/epizod-4.png",
    title: "Klucz // zabezpiecz wejscie",
    text: "Haslo jest pierwsza blokada przed cudzym terminalem. Nie musi byc piekne. Ma byc trudne do odgadniecia i wystarczajaco twarde, zeby kupic ci czas."
  },
  {
    image: "/static/images/epizod-5.png",
    title: "Kontakt // martwa skrzynka",
    text: "Podaj kanal odzyskiwania. System uzyje go jako ukrytego punktu synchronizacji. Jesli kiedys zgubisz dostep, to moze byc jedyna rzecz, ktora zostanie."
  },
  {
    image: "/static/images/epizod-6.png",
    title: "Alias // wejscie do miasta",
    text: "Profil jest prawie gotowy. Nadaj sobie nick, sprawdz wybor i uruchom instalacje. Startowa lokalizacja zostanie przydzielona automatycznie z IP albo z listy aktywnych miast."
  }
];

function updateBackgroundImage(stepIndex) {
  const bg = document.getElementById("background-image");
  bg.style.backgroundImage = `url(${stepImages[stepIndex] || ""})`;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}

function typeText(element, text) {
  clearTimeout(typewriterTimer);
  element.textContent = "";
  let index = 0;

  const tick = () => {
    element.textContent = text.slice(0, index);
    index += 1;
    if (index <= text.length) {
      const delay = 10 + Math.floor(Math.random() * 22);
      typewriterTimer = setTimeout(tick, delay);
    }
  };

  tick();
}

function renderStoryPanel(step) {
  const content = prelogContent[step] || prelogContent[0];
  return `
    <section class="onboarding-story">
      <div class="story-image-wrap">
        <img id="prelog-image" src="${content.image}" alt="">
      </div>
      <div class="story-copy">
        <div class="story-kicker">ghost_init / ${String(step + 1).padStart(2, "0")}</div>
        <h1>${escapeHTML(content.title)}</h1>
        <p id="prelog-text"></p>
      </div>
    </section>
  `;
}

function renderShell(step, body, side = "") {
  const layoutClass = side ? " has-identity-panel" : "";
  return `
    <div class="step onboarding-step${layoutClass}">
      ${renderStoryPanel(step)}
      ${side ? `<section class="identity-panel">${side}</section>` : ""}
      <section class="onboarding-console">
        <div class="console-topline">
          <span>operator setup</span>
          <span>${step + 1}/6</span>
        </div>
        <div class="console-body">${body}</div>
        <div class="step-nav">
          ${step > 0 ? `<button type="button" class="ghost-btn secondary" onclick="prevStep()">Wstecz</button>` : ""}
          <button type="button" class="ghost-btn primary js-next-step" onclick="handleNext()">${step === 5 ? "Zakoncz" : "Dalej"}</button>
        </div>
      </section>
    </div>
  `;
}

const steps = [
  () => renderShell(0, `
    <label class="ghost-field">
      <span>Nazwa uzytkownika</span>
      <input type="text" id="username" placeholder="np. CyberPhoenix" autocomplete="username">
    </label>
    <div class="field-hint">Login jest unikalny i bedzie widoczny w czesci systemowych logow.</div>
  `),

  () => {
    const options = factions.map(faction => `
      <button class="choice-card avatar-button" type="button"
        data-img="${faction.image}"
        data-name="${escapeHTML(faction.name)}"
        onclick="selectFaction(${faction.id}, this)">
        <span class="choice-code">${escapeHTML(faction.icon)}</span>
        <strong>${escapeHTML(faction.name)}</strong>
        <small>${escapeHTML(faction.summary)}</small>
      </button>
    `).join("");

    return renderShell(1, `
      <div class="choice-grid faction-options">${options}</div>
    `, `
      <div class="identity-preview">
        <div id="avatar-preview" class="avatar-box faction-preview"></div>
        <div id="avatar-info" class="avatar-info">Wybierz frakcje</div>
      </div>
    `);
  },

  () => {
    const factionId = formData.faction;
    const roles = rolesByFaction[factionId] || [];
    const avatars = avatarData[factionId] || [];
    const content = roles.length
      ? roles.map((roleName, index) => {
          const imgPath = `/static/images/${avatars[index]}`;
          return `
            <button class="choice-card avatar-button" type="button"
              data-img="${imgPath}"
              data-name="${escapeHTML(roleName)}"
              onclick="selectRole(${index + 1}, this)">
              <span class="choice-code">R${index + 1}</span>
              <strong>${escapeHTML(roleName)}</strong>
              <small>Profil operacyjny frakcji.</small>
            </button>
          `;
        }).join("")
      : `<div class="empty-state">Najpierw wybierz frakcje.</div>`;

    return renderShell(2, `
      <div class="choice-grid role-options">${content}</div>
    `, `
      <div class="identity-preview">
        <div id="avatar-preview" class="avatar-box"></div>
        <div id="avatar-info" class="avatar-info">Wybierz role</div>
      </div>
    `);
  },

  () => renderShell(3, `
    <label class="ghost-field">
      <span>Haslo</span>
      <input type="password" id="password" placeholder="Minimum 7 znakow i cyfra" autocomplete="new-password">
    </label>
    <label class="ghost-field">
      <span>Powtorz haslo</span>
      <input type="password" id="confirm_password" placeholder="Potwierdz klucz" autocomplete="new-password">
    </label>
    <div class="field-hint">System wymaga minimum 7 znakow i jednej cyfry.</div>
  `),

  () => renderShell(4, `
    <label class="ghost-field">
      <span>E-mail odzyskiwania</span>
      <input type="email" id="email" placeholder="operator@ghost.net" autocomplete="email">
    </label>
    <div class="field-hint">Adres musi byc unikalny. W grze traktujemy go jak martwa skrzynke.</div>
  `),

  () => {
    const faction = factions.find(item => item.id === Number(formData.faction));
    const roleName = (rolesByFaction[formData.faction] || [])[Number(formData.role) - 1] || "Nie wybrano";
    const avatar = formData.avatarImage || "/static/images/avatar-default.jpg";

    return renderShell(5, `
      <div class="summary-card">
        <img src="${avatar}" alt="">
        <div>
          <p><b>Uzytkownik</b> ${escapeHTML(formData.username)}</p>
          <p><b>Email</b> ${escapeHTML(formData.email)}</p>
          <p><b>Frakcja</b> ${escapeHTML(faction?.name || "Nie wybrano")}</p>
          <p><b>Rola</b> ${escapeHTML(roleName)}</p>
        </div>
      </div>
      <label class="ghost-field">
        <span>Nick gracza</span>
        <input type="text" id="nick" placeholder="np. NullRider" autocomplete="nickname">
      </label>
    `);
  }
];

function updatePrelogArea(step) {
  const textElement = document.getElementById("prelog-text");
  if (textElement) {
    typeText(textElement, prelogContent[step]?.text || "");
  }
}

function showStep(index) {
  isSubmitting = false;
  updateBackgroundImage(index);
  currentStep = index;
  document.getElementById("step-content").innerHTML = steps[index]();
  updatePrelogArea(index);
  updateProgressBar(index);
  document.getElementById("error-msg").innerText = "";

  restoreStepInputs(index);

  if (index === 1 || index === 2) {
    new AvatarSelector({
      imageContainer: "#avatar-preview",
      infoContainer: "#avatar-info",
      buttonSelector: ".avatar-button",
      defaultImage: index === 1
        ? "/static/images/logo_faction-default.jpg"
        : "/static/images/avatar-default.jpg"
    });
    restoreChoiceSelection(index);
  }

  const firstInput = document.querySelector("#step-content input");
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 60);
  }
}

function restoreStepInputs(index) {
  const fields = ["username", "password", "confirm_password", "email", "nick"];
  fields.forEach(id => {
    const input = document.getElementById(id);
    if (input && formData[id]) input.value = formData[id];
  });
}

function restoreChoiceSelection(index) {
  if (index === 1 && formData.faction) {
    const button = document.querySelector(`.faction-options button[onclick*="selectFaction(${formData.faction}"]`);
    if (button) {
      button.classList.add("selected");
      document.querySelector("#avatar-preview").style.backgroundImage = `url('${button.dataset.img}')`;
      document.querySelector("#avatar-info").textContent = `Wybrano: ${button.dataset.name}`;
    }
  }

  if (index === 2 && formData.role) {
    const button = document.querySelector(`.role-options button[onclick*="selectRole(${formData.role}"]`);
    if (button) {
      button.classList.add("selected");
      document.querySelector("#avatar-preview").style.backgroundImage = `url('${button.dataset.img}')`;
      document.querySelector("#avatar-info").textContent = `Wybrano: ${button.dataset.name}`;
    }
  }
}

function updateProgressBar(step) {
  const percent = ((step + 1) / steps.length) * 100;
  document.getElementById("progress-fill").style.width = percent + "%";
  const progressLabel = document.getElementById("progress-label");
  if (progressLabel) progressLabel.textContent = `${step + 1}/6`;
}

function prevStep() {
  if (currentStep > 0) showStep(currentStep - 1);
}

async function handleNext() {
  if (isSubmitting) return;

  const isValid = await validateStep();
  if (!isValid) return;

  if (currentStep < steps.length - 1) {
    showStep(currentStep + 1);
  } else {
    finalizeRegistration();
  }
}

function setError(message) {
  document.getElementById("error-msg").innerText = message || "";
}

function initOnboardingMusic() {
  const audio = document.getElementById("onboarding-music");
  if (!audio) return;

  audio.volume = 0.32;

  const startMusic = () => {
    audio.play()
      .then(() => {
        document.removeEventListener("pointerdown", startMusic);
        document.removeEventListener("keydown", startMusic);
      })
      .catch(() => {});
  };

  startMusic();
  document.addEventListener("pointerdown", startMusic, { passive: true });
  document.addEventListener("keydown", startMusic);
}

async function validateStep() {
  const inputFields = document.querySelectorAll("#step-content input");
  let valid = true;

  inputFields.forEach(input => {
    const value = input.value.trim();
    formData[input.id] = value;
    if (!value) valid = false;
  });

  if (!valid) {
    setError("Uzupelnij wszystkie pola.");
    return false;
  }

  if (currentStep === 0) {
    const response = await fetch("/api/register-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checking_username: formData.username, type_data: "user" })
    });
    const data = await response.json();
    if (!data.success) {
      setError("Ta nazwa uzytkownika jest juz zajeta.");
      return false;
    }
  }

  if (currentStep === 1 && !formData.faction) {
    setError("Wybierz frakcje.");
    return false;
  }

  if (currentStep === 2 && !formData.role) {
    setError("Wybierz role.");
    return false;
  }

  if (currentStep === 3) {
    if (!formData.password || formData.password.length < 7) {
      setError("Haslo musi miec co najmniej 7 znakow.");
      return false;
    }
    if (!/\d/.test(formData.password)) {
      setError("Haslo musi zawierac przynajmniej jedna cyfre.");
      return false;
    }
    if (formData.password !== formData.confirm_password) {
      setError("Hasla nie sa takie same.");
      return false;
    }
  }

  if (currentStep === 4) {
    const response = await fetch("/api/register-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checking_username: formData.email, type_data: "email" })
    });
    const data = await response.json();
    if (!data.success) {
      setError("Ten adres e-mail jest juz zarejestrowany.");
      return false;
    }
  }

  setError("");
  return true;
}

function selectFaction(id, btn) {
  formData.faction = id;
  formData.role = "";
  formData.avatarImage = "";
  document.querySelector("#avatar-info").innerText = `Wybrano: ${btn.dataset.name}`;
  document.querySelector("#avatar-preview").style.backgroundImage = `url('${btn.dataset.img}')`;
  document.querySelectorAll(".faction-options button").forEach(button => button.classList.remove("selected"));
  btn.classList.add("selected");
}

function selectRole(id, btn) {
  formData.role = id;
  formData.avatarImage = btn.dataset.img;
  document.querySelector("#avatar-info").innerText = `Wybrano: ${btn.dataset.name}`;
  document.querySelector("#avatar-preview").style.backgroundImage = `url('${btn.dataset.img}')`;
  document.querySelectorAll(".role-options button").forEach(button => button.classList.remove("selected"));
  btn.classList.add("selected");
}

function finalizeRegistration() {
  if (isSubmitting) return;
  isSubmitting = true;
  const nextButton = document.querySelector(".js-next-step");
  if (nextButton) {
    nextButton.disabled = true;
    nextButton.textContent = "Instaluje...";
  }

  setError("Instalacja profilu...");
  fetch("/api/register-finalize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData)
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        window.location.href = data.redirect;
      } else {
        isSubmitting = false;
        if (nextButton) {
          nextButton.disabled = false;
          nextButton.textContent = "Zakoncz";
        }
        setError(data.error || "Nie udalo sie utworzyc profilu.");
      }
    })
    .catch(() => {
      isSubmitting = false;
      if (nextButton) {
        nextButton.disabled = false;
        nextButton.textContent = "Zakoncz";
      }
      setError("Blad sieci.");
    });
}

document.addEventListener("DOMContentLoaded", () => {
  initOnboardingMusic();
  showStep(0);
});
