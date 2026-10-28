(() => {
  const form = document.querySelector(".quiz-form");
  if (!form) return;

  const questions = Array.from(form.querySelectorAll(".question-block"));
  const previousButton = document.querySelector("#quiz-previous");
  const nextButton = document.querySelector("#quiz-next");
  const finishButton = document.querySelector("#quiz-finish");
  const stepLabel = document.querySelector("#quiz-step-label");
  const progressTrack = document.querySelector(".quiz-progress-track");
  const progressValue = document.querySelector("#quiz-progress-value");
  let currentStep = 0;
  const confirmedSteps = Array(questions.length).fill(false);

  function selectedAnswer(question) {
    return question.querySelector("input[type='radio']:checked");
  }

  function preserveAnswerForSubmit(answer) {
    const preserved = document.createElement("input");
    preserved.type = "hidden";
    preserved.name = answer.name;
    preserved.value = answer.value;
    form.appendChild(preserved);
  }

  function showFeedback(question) {
    const answer = selectedAnswer(question);
    const feedback = question.querySelector(".answer-feedback");
    if (!answer) {
      feedback.hidden = true;
      feedback.textContent = "";
      feedback.classList.remove("is-incorrect");
      return false;
    }

    const correct = Number(answer.value) === Number(question.dataset.correct);
    feedback.textContent = correct
      ? `Resposta correta! Você ganhou ${question.dataset.points} pontos.`
      : `Não foi dessa vez. Esta questão valia ${question.dataset.points} pontos. A resposta correta é: ${question.dataset.correctAnswer}`;
    feedback.classList.toggle("is-incorrect", !correct);
    feedback.hidden = false;
    return true;
  }

  function renderStep() {
    questions.forEach((question, index) => {
      question.hidden = index !== currentStep;
    });

    const currentQuestion = questions[currentStep];
    const isConfirmed = confirmedSteps[currentStep];
    const feedback = currentQuestion.querySelector(".answer-feedback");
    if (isConfirmed) {
      showFeedback(currentQuestion);
    } else {
      feedback.hidden = true;
      feedback.textContent = "";
      feedback.classList.remove("is-incorrect");
    }
    currentQuestion.querySelectorAll("input[type='radio']").forEach((input) => {
      input.disabled = isConfirmed;
    });

    stepLabel.textContent = `Pergunta ${currentStep + 1} de ${questions.length}`;
    progressTrack.setAttribute("aria-valuenow", String(currentStep + 1));
    progressValue.style.width = `${((currentStep + 1) / questions.length) * 100}%`;
    previousButton.disabled = currentStep === 0;
    nextButton.hidden = currentStep === questions.length - 1 && isConfirmed;
    nextButton.textContent = isConfirmed ? "Próxima pergunta" : "Confirmar resposta";
    nextButton.disabled = isConfirmed ? currentStep === questions.length - 1 : !selectedAnswer(currentQuestion);
    finishButton.hidden = currentStep !== questions.length - 1 || !isConfirmed;
    finishButton.disabled = !isConfirmed;
  }

  questions.forEach((question) => {
    question.addEventListener("change", () => {
      if (question !== questions[currentStep] || confirmedSteps[currentStep]) return;
      nextButton.disabled = !selectedAnswer(question);
    });
  });

  previousButton.addEventListener("click", () => {
    if (currentStep > 0) {
      currentStep -= 1;
      renderStep();
    }
  });

  nextButton.addEventListener("click", () => {
    if (!selectedAnswer(questions[currentStep])) return;

    if (!confirmedSteps[currentStep]) {
      preserveAnswerForSubmit(selectedAnswer(questions[currentStep]));
      confirmedSteps[currentStep] = true;
      renderStep();
      return;
    }

    if (currentStep < questions.length - 1) {
      currentStep += 1;
      renderStep();
    }
  });

  form.addEventListener("submit", (event) => {
    if (questions.some((question, index) => !confirmedSteps[index] || !selectedAnswer(question))) {
      event.preventDefault();
    }
  });

  renderStep();
})();