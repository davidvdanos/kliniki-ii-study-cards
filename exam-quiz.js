(function () {
  const cards = Array.from(document.querySelectorAll(".quiz-card"));
  const answeredNode = document.getElementById("quizAnswered");
  const correctNode = document.getElementById("quizCorrect");
  const positionNode = document.getElementById("quizPosition");
  const groupNode = document.getElementById("quizGroup");
  const prevButtons = [document.getElementById("prevQuestion"), document.getElementById("prevQuestionBottom")].filter(Boolean);
  const nextButtons = [document.getElementById("nextQuestion"), document.getElementById("nextQuestionBottom")].filter(Boolean);
  const resetAllButton = document.getElementById("resetAllAnswers");
  const jumpButtons = Array.from(document.querySelectorAll(".quiz-jump"));
  const storageKey = `kliniki-ii-quiz:${window.location.pathname}:v2`;

  let currentIndex = 0;
  let state = loadState();

  function loadState() {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(storageKey) || "{}");
      return {
        currentIndex: Number.isInteger(parsed.currentIndex) ? parsed.currentIndex : 0,
        answers: parsed.answers && typeof parsed.answers === "object" ? parsed.answers : {},
      };
    } catch {
      return { currentIndex: 0, answers: {} };
    }
  }

  function saveState() {
    state.currentIndex = currentIndex;
    const answers = {};
    cards.forEach((card) => {
      const selected = card.querySelector("input[type='radio']:checked");
      if (selected) {
        answers[card.dataset.question] = selected.value;
      }
    });
    state.answers = answers;
    window.localStorage.setItem(storageKey, JSON.stringify(state));
  }

  function clearOptionStates(card) {
    card.querySelectorAll(".quiz-option").forEach((option) => {
      option.classList.remove("is-correct", "is-wrong", "is-missed");
    });
  }

  function gradeCard(card, shouldSave = true) {
    const feedback = card.querySelector(".quiz-feedback");
    const selected = card.querySelector("input[type='radio']:checked");
    clearOptionStates(card);

    if (!selected) {
      delete card.dataset.answered;
      delete card.dataset.correct;
      if (feedback) {
        feedback.textContent = "";
        feedback.className = "quiz-feedback";
      }
      updateScore();
      if (shouldSave) saveState();
      return;
    }

    const selectedOption = selected.closest(".quiz-option");
    const isCorrect = selected.dataset.correct === "true";

    card.querySelectorAll("input[data-correct='true']").forEach((input) => {
      const option = input.closest(".quiz-option");
      if (option) option.classList.add(isCorrect ? "is-correct" : "is-missed");
    });

    if (selectedOption) {
      selectedOption.classList.add(isCorrect ? "is-correct" : "is-wrong");
    }

    card.dataset.answered = "true";
    card.dataset.correct = isCorrect ? "true" : "false";

    if (feedback) {
      feedback.textContent = isCorrect ? "Σωστό." : "Όχι ακριβώς. Η σωστή απάντηση φαίνεται με πράσινο.";
      feedback.className = `quiz-feedback ${isCorrect ? "is-good" : "is-bad"}`;
    }

    updateScore();
    if (shouldSave) saveState();
  }

  function resetCard(card, shouldSave = true) {
    card.querySelectorAll("input[type='radio']").forEach((input) => {
      input.checked = false;
    });
    const details = card.querySelector("details");
    if (details) details.open = false;
    clearOptionStates(card);
    delete card.dataset.answered;
    delete card.dataset.correct;
    const feedback = card.querySelector(".quiz-feedback");
    if (feedback) {
      feedback.textContent = "";
      feedback.className = "quiz-feedback";
    }
    updateScore();
    if (shouldSave) saveState();
  }

  function updateScore() {
    const answered = cards.filter((card) => card.dataset.answered === "true").length;
    const correct = cards.filter((card) => card.dataset.correct === "true").length;
    if (answeredNode) answeredNode.textContent = String(answered);
    if (correctNode) correctNode.textContent = `${correct} σωστές`;
  }

  function setCurrentIndex(nextIndex, shouldSave = true) {
    if (!cards.length) return;
    currentIndex = Math.max(0, Math.min(cards.length - 1, nextIndex));
    cards.forEach((card, index) => {
      card.hidden = index !== currentIndex;
      card.classList.toggle("is-active", index === currentIndex);
    });
    if (positionNode) positionNode.textContent = String(currentIndex + 1);
    if (groupNode) groupNode.textContent = cards[currentIndex]?.dataset.group || "";
    prevButtons.forEach((button) => {
      button.disabled = currentIndex === 0;
    });
    nextButtons.forEach((button) => {
      button.disabled = currentIndex === cards.length - 1;
    });
    jumpButtons.forEach((button) => {
      const target = Number(button.dataset.targetIndex);
      const group = cards[target]?.dataset.group;
      button.classList.toggle("active", group === cards[currentIndex]?.dataset.group);
    });
    if (shouldSave) saveState();
  }

  function restoreAnswers() {
    Object.entries(state.answers || {}).forEach(([question, value]) => {
      const card = cards.find((item) => item.dataset.question === question);
      const input = card?.querySelector(`input[value="${CSS.escape(value)}"]`);
      if (input) {
        input.checked = true;
        gradeCard(card, false);
      }
    });
  }

  cards.forEach((card) => {
    const checkButton = card.querySelector(".check-answer");
    const resetButton = card.querySelector(".reset-answer");

    card.querySelectorAll("input[type='radio']").forEach((input) => {
      input.addEventListener("change", () => gradeCard(card));
    });

    checkButton?.addEventListener("click", () => {
      const selected = card.querySelector("input[type='radio']:checked");
      if (selected) {
        gradeCard(card);
      } else {
        const feedback = card.querySelector(".quiz-feedback");
        if (feedback) {
          feedback.textContent = "Διάλεξε πρώτα μία απάντηση.";
          feedback.className = "quiz-feedback is-neutral";
        }
      }
    });

    resetButton?.addEventListener("click", () => resetCard(card));
  });

  prevButtons.forEach((button) => {
    button.addEventListener("click", () => setCurrentIndex(currentIndex - 1));
  });

  nextButtons.forEach((button) => {
    button.addEventListener("click", () => setCurrentIndex(currentIndex + 1));
  });

  jumpButtons.forEach((button) => {
    button.addEventListener("click", () => setCurrentIndex(Number(button.dataset.targetIndex) || 0));
  });

  resetAllButton?.addEventListener("click", () => {
    cards.forEach((card) => resetCard(card, false));
    state.answers = {};
    setCurrentIndex(0, false);
    window.localStorage.removeItem(storageKey);
    updateScore();
  });

  restoreAnswers();
  setCurrentIndex(Number.isInteger(state.currentIndex) ? state.currentIndex : 0, false);
  updateScore();
})();
