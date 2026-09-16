(function () {
  const cards = Array.from(document.querySelectorAll(".quiz-card"));
  const answeredNode = document.getElementById("quizAnswered");
  const correctNode = document.getElementById("quizCorrect");

  function updateScore() {
    const answered = cards.filter((card) => card.dataset.answered === "true").length;
    const correct = cards.filter((card) => card.dataset.correct === "true").length;
    if (answeredNode) answeredNode.textContent = String(answered);
    if (correctNode) correctNode.textContent = `${correct} σωστές`;
  }

  function clearOptionStates(card) {
    card.querySelectorAll(".quiz-option").forEach((option) => {
      option.classList.remove("is-correct", "is-wrong", "is-missed");
    });
  }

  cards.forEach((card) => {
    const feedback = card.querySelector(".quiz-feedback");
    const checkButton = card.querySelector(".check-answer");
    const resetButton = card.querySelector(".reset-answer");

    checkButton?.addEventListener("click", () => {
      const selected = card.querySelector("input[type='radio']:checked");
      clearOptionStates(card);

      if (!selected) {
        if (feedback) {
          feedback.textContent = "Διάλεξε πρώτα μία απάντηση.";
          feedback.className = "quiz-feedback is-neutral";
        }
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
        feedback.textContent = isCorrect ? "Σωστό." : "Όχι ακριβώς. Άνοιξε τη σωστή απάντηση για έλεγχο.";
        feedback.className = `quiz-feedback ${isCorrect ? "is-good" : "is-bad"}`;
      }

      updateScore();
    });

    resetButton?.addEventListener("click", () => {
      card.querySelectorAll("input[type='radio']").forEach((input) => {
        input.checked = false;
      });
      clearOptionStates(card);
      delete card.dataset.answered;
      delete card.dataset.correct;
      if (feedback) {
        feedback.textContent = "";
        feedback.className = "quiz-feedback";
      }
      updateScore();
    });
  });
})();
