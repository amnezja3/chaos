let currentStep = 0;
let typewriterTimer = null;
let isSubmitting = false;
let isValidating = false;
let registrationErrorKey = "";
let avatarSelector = null;

function onboardingText(key, params = {}) {
  return window.GhostLocale.t(`onboarding.${key}`, params);
}

function onboardingLabel(key) {
  return `<span data-ghost-i18n="onboarding.${escapeHTML(key)}">${escapeHTML(onboardingText(key))}</span>`;
}

// Refresh only system text. Inputs, selected cards, audio and pending requests survive.
function refreshOnboardingLocale() {
  document.title = onboardingText("title");
  const story = document.getElementById("prelog-text");
  if (story) {
    clearTimeout(typewriterTimer);
    story.textContent = onboardingText(prelogContent[currentStep].textKey);
  }
  for (const button of document.querySelectorAll('[data-name-key]')) {
    button.dataset.name = onboardingText(button.dataset.nameKey);
  }
  const selected = document.querySelector('.avatar-button.selected');
  if (selected) document.getElementById('avatar-info').textContent = onboardingText('selected', {name: selected.dataset.name});
  setError(registrationErrorKey);
}
document.addEventListener('ghost:locale-changed', refreshOnboardingLocale);

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
  { id: 1, icon: "ORDER", image: "/static/images/logo_faction_img_1.png" },
  { id: 2, icon: "ECHO", image: "/static/images/logo_faction_img_2.png" },
  { id: 3, icon: "VIRX", image: "/static/images/logo_faction_img_3.png" },
  { id: 4, icon: "GHOST", image: "/static/images/logo_faction_img_4.png" }
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
    titleKey: "story.0.title", textKey: "story.0.text"
  },
  {
    image: "/static/images/epizod-2.png",
    titleKey: "story.1.title", textKey: "story.1.text"
  },
  {
    image: "/static/images/epizod-3.png",
    titleKey: "story.2.title", textKey: "story.2.text"
  },
  {
    image: "/static/images/epizod-4.png",
    titleKey: "story.3.title", textKey: "story.3.text"
  },
  {
    image: "/static/images/epizod-5.png",
    titleKey: "story.4.title", textKey: "story.4.text"
  },
  {
    image: "/static/images/epizod-6.png",
    titleKey: "story.5.title", textKey: "story.5.text"
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
        <img id="prelog-image" src="${content.image}" alt="" loading="eager">
      </div>
      <div class="story-copy">
        <div class="story-kicker">ghost_init / ${String(step + 1).padStart(2, "0")}</div>
        <h1>${onboardingLabel(content.titleKey)}</h1>
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
          <span>${onboardingLabel("setup")}</span>
          <span>${step + 1}/6</span>
        </div>
        <div class="console-body">${body}</div>
        <div class="step-nav">
          ${step > 0 ? `<button type="button" class="ghost-btn secondary" onclick="prevStep()">${onboardingLabel("back")}</button>` : ""}
          <button type="button" class="ghost-btn primary js-next-step" onclick="handleNext()">${onboardingLabel(step === 5 ? "finish" : "next")}</button>
        </div>
      </section>
    </div>
  `;
}

const steps = [
  () => renderShell(0, `
    <label class="ghost-field">
      <span>${onboardingLabel("username")}</span>
      <input type="text" id="username" data-ghost-i18n-placeholder="onboarding.username_placeholder" placeholder="${escapeHTML(onboardingText("username_placeholder"))}" autocomplete="username">
    </label>
    <div class="field-hint">${onboardingLabel("username_hint")}</div>
  `),

  () => {
    const options = factions.map(faction => `
      <button class="choice-card avatar-button" type="button"
        data-img="${faction.image}" data-name-key="faction.${faction.id}.name"
        data-name="${escapeHTML(onboardingText(`faction.${faction.id}.name`))}"
        onclick="selectFaction(${faction.id}, this)">
        <span class="choice-code">${escapeHTML(faction.icon)}</span>
        <strong>${onboardingLabel(`faction.${faction.id}.name`)}</strong>
        <small>${onboardingLabel(`faction.${faction.id}.summary`)}</small>
      </button>
    `).join("");

    return renderShell(1, `
      <div class="choice-grid faction-options">${options}</div>
    `, `
      <div class="identity-preview">
        <div id="avatar-preview" class="avatar-box faction-preview"></div>
        <div id="avatar-info" class="avatar-info">${onboardingLabel("choose_faction")}</div>
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
              data-img="${imgPath}" data-name-key="role.${factionId}.${index + 1}"
              data-name="${escapeHTML(onboardingText(`role.${factionId}.${index + 1}`))}"
              onclick="selectRole(${index + 1}, this)">
              <span class="choice-code">R${index + 1}</span>
              <strong>${onboardingLabel(`role.${factionId}.${index + 1}`)}</strong>
              <small>${onboardingLabel("role_hint")}</small>
            </button>
          `;
        }).join("")
      : `<div class="empty-state">${onboardingLabel("faction_first")}</div>`;

    return renderShell(2, `
      <div class="choice-grid role-options">${content}</div>
    `, `
      <div class="identity-preview">
        <div id="avatar-preview" class="avatar-box"></div>
        <div id="avatar-info" class="avatar-info">${onboardingLabel("choose_role")}</div>
      </div>
    `);
  },

  () => renderShell(3, `
    <label class="ghost-field">
      <span>${onboardingLabel("password")}</span>
      <input type="password" id="password" data-ghost-i18n-placeholder="onboarding.password_placeholder" placeholder="${escapeHTML(onboardingText("password_placeholder"))}" autocomplete="new-password">
    </label>
    <label class="ghost-field">
      <span>${onboardingLabel("confirm_password")}</span>
      <input type="password" id="confirm_password" data-ghost-i18n-placeholder="onboarding.confirm_placeholder" placeholder="${escapeHTML(onboardingText("confirm_placeholder"))}" autocomplete="new-password">
    </label>
    <div class="field-hint">${onboardingLabel("password_hint")}</div>
  `),

  () => renderShell(4, `
    <label class="ghost-field">
      <span>${onboardingLabel("email")}</span>
      <input type="email" id="email" placeholder="operator@ghost.net" autocomplete="email">
    </label>
    <div class="field-hint">${onboardingLabel("email_hint")}</div>
  `),

  () => {
    const faction = factions.find(item => item.id === Number(formData.faction));
    const avatar = formData.avatarImage || "/static/images/avatar-default.jpg";

    return renderShell(5, `
      <div class="summary-card">
        <img src="${avatar}" alt="">
        <div>
          <p><b>${onboardingLabel("summary_username")}</b> ${escapeHTML(formData.username)}</p>
          <p><b>${onboardingLabel("summary_email")}</b> ${escapeHTML(formData.email)}</p>
          <p><b>${onboardingLabel("summary_faction")}</b> ${onboardingLabel(faction ? `faction.${faction.id}.name` : "not_selected")}</p>
          <p><b>${onboardingLabel("summary_role")}</b> ${onboardingLabel(formData.role ? `role.${formData.faction}.${formData.role}` : "not_selected")}</p>
        </div>
      </div>
      <label class="ghost-field">
        <span>${onboardingLabel("nick")}</span>
        <input type="text" id="nick" data-ghost-i18n-placeholder="onboarding.nick_placeholder" placeholder="${escapeHTML(onboardingText("nick_placeholder"))}" autocomplete="nickname">
      </label>
    `);
  }
];

function updatePrelogArea(step) {
  const textElement = document.getElementById("prelog-text");
  if (textElement) {
    typeText(textElement, onboardingText(prelogContent[step].textKey));
  }
}

function showStep(index) {
  isSubmitting = false;
  updateBackgroundImage(index);
  currentStep = index;
  document.getElementById("step-content").innerHTML = steps[index]();
  updatePrelogArea(index);
  updateProgressBar(index);
  setError("");

  restoreStepInputs(index);

  if (index === 1 || index === 2) {
    avatarSelector = new AvatarSelector({
      imageContainer: "#avatar-preview",
      infoContainer: "#avatar-info",
      buttonSelector: ".avatar-button",
      selectedLabel: name => onboardingText("selected", {name}),
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
      avatarSelector.currentImage = button.dataset.img;
      avatarSelector.selectedButton = button;
      document.querySelector("#avatar-preview").style.backgroundImage = `url('${button.dataset.img}')`;
      document.querySelector("#avatar-info").textContent = onboardingText("selected", {name: button.dataset.name});
    }
  }

  if (index === 2 && formData.role) {
    const button = document.querySelector(`.role-options button[onclick*="selectRole(${formData.role}"]`);
    if (button) {
      button.classList.add("selected");
      avatarSelector.currentImage = button.dataset.img;
      avatarSelector.selectedButton = button;
      document.querySelector("#avatar-preview").style.backgroundImage = `url('${button.dataset.img}')`;
      document.querySelector("#avatar-info").textContent = onboardingText("selected", {name: button.dataset.name});
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
  if (isSubmitting || isValidating) return;
  saveStepInputs();
  if (currentStep > 0) showStep(currentStep - 1);
}

async function handleNext() {
  if (isSubmitting || isValidating) return;
  isValidating = true;
  let isValid;
  try { isValid = await validateStep(); }
  catch (_) { setError("onboarding.network"); return; }
  finally { isValidating = false; }
  if (!isValid) return;

  if (currentStep < steps.length - 1) {
    showStep(currentStep + 1);
  } else {
    finalizeRegistration();
  }
}

function setError(key) {
  registrationErrorKey = key || "";
  document.getElementById("error-msg").textContent = key ? window.GhostLocale.t(key) : "";
}

function saveStepInputs() {
  for (const input of document.querySelectorAll("#step-content input")) formData[input.id] = input.value;
}

function isValidUsername(value) {
  return /^[A-Za-z0-9_][A-Za-z0-9_.-]{2,23}$/.test(String(value || "").trim());
}

function isValidEmail(value) {
  return /^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$/.test(String(value || "").trim());
}

function validatePassword(value) {
  const password = String(value || "");
  if (password.length < 8) return "onboarding.password_short";
  if (password.length > 128) return "onboarding.password_long";
  if (!/[A-Za-z]/.test(password)) return "onboarding.password_letter";
  if (!/\d/.test(password)) return "onboarding.password_digit";
  return "";
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
    setError("onboarding.required");
    return false;
  }

  if (currentStep === 0) {
    if (!isValidUsername(formData.username)) {
      setError("onboarding.username_invalid");
      return false;
    }
    const response = await fetch("/api/register-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checking_username: formData.username, type_data: "user", locale: window.GhostLocale.getLocale() })
    });
    const data = await response.json();
    if (!data.success) {
      setError(data.error_key || "onboarding.username_taken");
      return false;
    }
  }

  if (currentStep === 1 && !formData.faction) {
    setError("onboarding.faction_required");
    return false;
  }

  if (currentStep === 2 && !formData.role) {
    setError("onboarding.role_required");
    return false;
  }

  if (currentStep === 3) {
    const passwordError = validatePassword(formData.password);
    if (passwordError) {
      setError(passwordError);
      return false;
    }
    if (formData.password !== formData.confirm_password) {
      setError("onboarding.password_mismatch");
      return false;
    }
  }

  if (currentStep === 4) {
    if (!isValidEmail(formData.email)) {
      setError("onboarding.email_invalid");
      return false;
    }
    const response = await fetch("/api/register-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ checking_username: formData.email, type_data: "email", locale: window.GhostLocale.getLocale() })
    });
    const data = await response.json();
    if (!data.success) {
      setError(data.error_key || "onboarding.email_taken");
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
  document.querySelector("#avatar-info").innerText = onboardingText("selected", {name: btn.dataset.name});
  document.querySelector("#avatar-preview").style.backgroundImage = `url('${btn.dataset.img}')`;
  document.querySelectorAll(".faction-options button").forEach(button => button.classList.remove("selected"));
  btn.classList.add("selected");
}

function selectRole(id, btn) {
  formData.role = id;
  formData.avatarImage = btn.dataset.img;
  document.querySelector("#avatar-info").innerText = onboardingText("selected", {name: btn.dataset.name});
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
    nextButton.innerHTML = onboardingLabel("installing");
  }

  setError("onboarding.installing_profile");
  fetch("/api/register-finalize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({...formData, locale: window.GhostLocale.getLocale()})
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        window.location.href = data.redirect;
      } else {
        isSubmitting = false;
        if (nextButton) {
          nextButton.disabled = false;
          nextButton.innerHTML = onboardingLabel("finish");
        }
        setError(data.error_key || "onboarding.failed");
      }
    })
    .catch(() => {
      isSubmitting = false;
      if (nextButton) {
        nextButton.disabled = false;
        nextButton.innerHTML = onboardingLabel("finish");
      }
      setError("onboarding.network");
    });
}

document.addEventListener("DOMContentLoaded", () => {
  initOnboardingMusic();
  showStep(0);
  document.title = onboardingText("title");
});
