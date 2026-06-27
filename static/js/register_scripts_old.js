let formData = {};
let currentStep = 1;

const stepImages = {
  1: "/static/images/install/step1.jpg",
  2: "/static/images/install/step2.jpg",
  3: "/static/images/install/step3.jpg",
  4: "/static/images/install/step4.jpg",
  5: "/static/images/install/step5.jpg",
  6: "/static/images/install/step6.jpg",
  7: "/static/images/install/step6.jpg"
};

const rolesByFaction = {
  1: ["Analizator", "Obrońca", "Rekonstruktor", "Mediator", "Egzekutor"],
  2: ["Haktywista", "Socjotechnik", "Odsłaniacz", "Wizjoner", "Zapalnik"],
  3: ["Broker", "Architekt", "Manipulator", "Egzekutor Zysku", "Kurator Algorytmu"],
  4: ["Iluzjonista", "Wirusolog", "Paranoik", "Rozłamowiec", "Lustrzany Sędzia"]
};

function loadRolesForFaction() {
  const factionId = document.getElementById("faction").value;
  const roleButtonsContainer = document.getElementById("role-buttons");
  const roleInput = document.getElementById("role");

  roleButtonsContainer.innerHTML = '';
  roleInput.value = '';

  if (rolesByFaction[factionId]) {
    rolesByFaction[factionId].forEach((role, index) => {
      const btn = document.createElement("button");
      btn.textContent = role;
      btn.onclick = () => {
        // usuń zaznaczenie z innych
        roleButtonsContainer.querySelectorAll("button").forEach(b => b.classList.remove("selected"));
        // zaznacz aktualny
        btn.classList.add("selected");
        // zapisz wartość
        roleInput.value = index + 1;
      };
      roleButtonsContainer.appendChild(btn);
    });
  }
}



function showStep(step) {
  document.querySelectorAll(".step").forEach(div => div.classList.remove("active"));
  document.getElementById(`step-${step}`).classList.add("active");

  console.log("Pokazuję krok:", step);

  // aktualizacja tła i paska
  const bg = document.getElementById("background-image");
  if (stepImages[step]) {
    bg.style.backgroundImage = `url('${stepImages[step]}')`;
  }

  const progress = document.getElementById("progress-fill");
  const percent = (step / 7) * 100;
  progress.style.width = `${percent}%`;
}

function selectFaction(value, el) {
  document.getElementById("faction").value = value;

  // zaznaczony przycisk
  document.querySelectorAll(".faction-options button").forEach(btn => btn.classList.remove("selected"));
  el.classList.add("selected");

  // załaduj role dynamicznie
  loadRolesForFaction();
}



function nextStep(step) {
  const fields = {
    1: "username",
    2: "faction",
    3: "role",
    4: ["password", "confirm_password"],
    5: "email"
  };

  let valid = true;

  if (Array.isArray(fields[step])) {
    fields[step].forEach(id => {
      const val = document.getElementById(id).value.trim();
      formData[id] = val;
      if (!val) valid = false;
    });
  } else {
    const val = document.getElementById(fields[step]).value.trim();
    formData[fields[step]] = val;
    if (!val) valid = false;
  }

  if (!valid) {
    document.getElementById("error-msg").textContent = "Uzupełnij wszystkie pola.";
    return;
  }

  if (step === 4 && formData.password !== formData.confirm_password) {
    document.getElementById("error-msg").textContent = "Hasła się nie zgadzają.";
    return;
  }

  document.getElementById("error-msg").textContent = "";

  // Po zatwierdzeniu frakcji – załaduj dynamiczne role
  if (step === 2) {
    loadRolesForFaction();
  }

  currentStep++;
  showStep(currentStep);
}


function finalize() {
  formData["nick"] = document.getElementById("nick").value.trim();

  if (!formData.nick) {
    document.getElementById("error-msg").textContent = "Podaj nick.";
    return;
  }

  document.getElementById("error-msg").textContent = "";

  fetch("/api/register-finalize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formData)
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        setTimeout(() => {
          const overlay = document.getElementById("form-overlay") || document.body;
          overlay.innerHTML = "<h2>✅ GhostSystem zainstalowany</h2><p>Możesz się teraz zalogować.</p>";
          window.location.href = "/login"; // lub "/desktop", jeśli chcesz od razu zalogować
        }, 4000);

      } else {
        document.getElementById("error-msg").textContent = data.error || "Wystąpił błąd.";
      }
    });
}
