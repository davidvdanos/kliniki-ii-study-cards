from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "study-cards-app"
EXAM_DIR = APP / "exam"
SOURCE = ROOT / "Θεματα" / "Θέματα_Εξετάσεων_Κλινική_Ψυχολογία_ΙΙ.docx"


@dataclass
class Line:
    index: int
    text: str
    highlighted: bool
    highlight_text: str


@dataclass
class DevelopmentExam:
    title: str
    meta: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)


@dataclass
class Option:
    label: str
    text: str
    correct: bool = False


@dataclass
class QuizQuestion:
    group: str
    number: int
    prompt: str
    options: list[Option] = field(default_factory=list)
    answer_note: str = ""


def paragraph_lines() -> list[Line]:
    document = Document(str(SOURCE))
    rows: list[Line] = []
    for i, paragraph in enumerate(document.paragraphs):
        text = re.sub(r"\s+", " ", paragraph.text.strip())
        if not text:
            continue
        highlights = [run.text for run in paragraph.runs if run.font.highlight_color is not None and run.text]
        rows.append(Line(i, text, bool(highlights), "".join(highlights).strip()))
    return rows


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def question_number(text: str) -> int | None:
    match = re.match(r"^(\d+)\.\s+", text)
    return int(match.group(1)) if match else None


def option_label(text: str) -> str | None:
    match = re.match(r"^\s*([a-dA-DΑ-Δα-δΒΓΔG1-4ΐ8])[\.\)]\s*", text)
    return match.group(1).upper() if match else None


def normalize_label(label: str) -> str:
    label = label.upper()
    return {"Α": "A", "Β": "B", "Γ": "C", "Δ": "D", "G": "C", "1": "B", "2": "C", "3": "C", "4": "D", "8": "B"}.get(label, label)


def strip_option_prefix(text: str) -> str:
    return re.sub(r"^\s*([a-dA-DΑ-Δα-δΒΓΔG1-4ΐ8])[\.\)]\s*", "", text).strip()


INLINE_OPTION_RE = re.compile(r"(?=(?:^|[\s,;])([a-dA-DΑ-ΔΒΓΔ])[\.\)]\s*)")


def numeric_option_label(text: str, current: QuizQuestion | None) -> str | None:
    if current is None or not current.options:
        return None
    match = re.match(r"^(\d+)\.\s+(.+)$", text)
    if not match:
        return None
    number = int(match.group(1))
    rest = match.group(2).strip()
    if re.match(r"^[a-dA-DΑ-ΔΒΓΔ]\.\s+", rest):
        return None
    if number == 1 and len(current.options) == 1:
        return "B"
    if number == 2 and len(current.options) == 2:
        return "C"
    if number == 8 and len(current.options) == 1:
        return "B"
    return None


def split_inline_options(text: str, highlight_text: str = "") -> list[Option]:
    matches = list(INLINE_OPTION_RE.finditer(text))
    if len(matches) < 2:
        label = option_label(text)
        if not label:
            return []
        return [Option(normalize_label(label), strip_option_prefix(text), bool(highlight_text))]

    options: list[Option] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        segment = text[start:end].strip(" ,;")
        label = option_label(segment)
        if not label:
            continue
        option_text = strip_option_prefix(segment).strip(" ,;")
        segment_key = re.sub(r"[\s,;]+", " ", segment).strip().lower()
        highlight_key = re.sub(r"[\s,;]+", " ", highlight_text).strip().lower()
        is_correct = bool(highlight_key and (highlight_key in segment_key or segment_key in highlight_key))
        options.append(Option(normalize_label(label), option_text, is_correct))
    return options


def parse_development(lines: list[Line]) -> list[DevelopmentExam]:
    dev_lines = [line for line in lines if line.index < 46]
    exams: list[DevelopmentExam] = []
    current: DevelopmentExam | None = None
    collecting_questions = False

    for line in dev_lines:
        text = line.text
        if text in {"Σεπτέμβριος 2024", "Φεβρουάριος, άγνωστη ημερομηνία εξέτασης", "Σεπτέμβριος 2025"}:
            if current:
                exams.append(current)
            current = DevelopmentExam(text)
            collecting_questions = False
            continue
        if current is None:
            continue
        if text == "Θέματα εξέτασης":
            collecting_questions = True
            continue
        if text.startswith("Σημείωση μεταγραφής"):
            current.meta.append(text)
            continue
        if collecting_questions:
            current.questions.append(text)
        elif text not in {"Μάθημα: ΚΛΙΝΙΚΗ ΨΥΧΟΛΟΓΙΑ ΙΙ", "Μάθημα: Κλινική Ψυχολογία ΙΙ"}:
            current.meta.append(text)

    if current:
        exams.append(current)
    return exams


def parse_quiz(lines: list[Line]) -> list[QuizQuestion]:
    quiz_lines = [line for line in lines if line.index >= 46]
    group = "Ομάδα Α"
    questions: list[QuizQuestion] = []
    current: QuizQuestion | None = None
    active_option: Option | None = None

    def finish_current() -> None:
        nonlocal current, active_option
        if current and current.prompt and current.options:
            questions.append(current)
        current = None
        active_option = None

    for line in quiz_lines:
        text = line.text
        upper = text.upper()
        if text.startswith("Θέματα Κλινικής Ψυχολογίας II - Α"):
            finish_current()
            group = "Ομάδα Α"
            continue
        if upper == "ΟΜΑΔΑ Β":
            finish_current()
            group = "Ομάδα Β"
            continue
        if upper == "ΟΜΑΔΑ Δ" or text.startswith("ΘΕΜΑΤΑ ΕΞΕΤΑΣΗΣ - ΟΜΑΔΑ Δ"):
            finish_current()
            group = "Ομάδα Δ"
            continue
        if text.startswith(("Πολλαπλής Επιλογής", "Πηγή:", "Σημείωση:")):
            continue

        number = question_number(text)
        numeric_label = numeric_option_label(text, current)
        if number is not None and numeric_label is None:
            finish_current()
            prompt = re.sub(r"^\d+\.\s*", "", text).strip()
            current = QuizQuestion(group=group, number=number, prompt=prompt)
            continue

        if current is None:
            continue

        inline_options = split_inline_options(text, line.highlight_text)
        starts_first_option = bool(inline_options and inline_options[0].label == "A")
        if inline_options and (current.options or starts_first_option):
            current.options.extend(inline_options)
            active_option = current.options[-1]
            continue

        if numeric_label is not None:
            current.options.append(Option(numeric_label, re.sub(r"^\d+\.\s*", "", text).strip(), line.highlighted))
            active_option = current.options[-1]
            continue

        if active_option is not None and active_option.correct and line.highlighted and not option_label(text):
            active_option.text = f"{active_option.text} {text}".strip()
            continue

        if current.options and len(current.options) < 4 and not option_label(text):
            next_label = ["A", "B", "C", "D"][len(current.options)]
            current.options.append(Option(next_label, text, line.highlighted))
            active_option = current.options[-1]
            continue

        if active_option is not None:
            active_option.text = f"{active_option.text} {text}".strip()
            if line.highlighted:
                active_option.correct = True
            continue

        current.prompt = f"{current.prompt} {text}".strip()

    finish_current()

    for question in questions:
        correct = [opt for opt in question.options if opt.correct]
        if correct:
            question.answer_note = " / ".join(f"{opt.label}. {opt.text}" for opt in correct)
        else:
            question.answer_note = "Δεν υπάρχει καταχωρισμένη σωστή απάντηση με highlight στο Word."

    return questions


def nav(active: str, prefix: str = "../") -> str:
    items = [
        ("Κάρτες", f"{prefix}index.html", active == "cards"),
        ("SOS", f"{prefix}notes/sos-development.html", active == "sos"),
        ("Ωριμότητα", f"{prefix}notes/psychodynamic-maturity-self.html", active == "maturity"),
        ("Διάγνωση", f"{prefix}notes/diagnosis-clinical-assessment.html", active == "diagnosis"),
        ("MSE", f"{prefix}notes/mental-status-examination.html", active == "mse"),
        ("Δεσμός", f"{prefix}notes/attachment-theory.html", active == "attachment"),
        ("Cluster A", f"{prefix}notes/cluster-a.html", active == "cluster-a"),
        ("Cluster B", f"{prefix}notes/cluster-b.html", active == "cluster-b"),
        ("Cluster C", f"{prefix}notes/cluster-c.html", active == "cluster-c"),
        ("Άγχος/PTSD", f"{prefix}notes/anxiety-ptsd.html", active == "anxiety"),
        ("Διάθεση", f"{prefix}notes/mood-disorders.html", active == "mood"),
        ("Ψύχωση", f"{prefix}notes/psychotic-disorders.html", active == "psychosis"),
        ("Τροφή", f"{prefix}notes/eating-disorders.html", active == "eating"),
        ("Ανάπτυξης", f"{prefix}exam/development.html", active == "development"),
        ("Quiz Πολλαπλής", f"{prefix}exam/multiple-choice.html", active == "multiple"),
    ]
    links = "".join(f"<a class=\"nav-tab {'active' if is_active else ''}\" href=\"{href}\">{esc(label)}</a>" for label, href, is_active in items)
    return f"<nav class=\"site-tabs\" aria-label=\"Κύρια πλοήγηση\"><div class=\"site-tabs-inner\">{links}</div></nav>"


def page_head(title: str, extra_script: bool = False) -> str:
    script = '<script src="../exam-quiz.js" defer></script>' if extra_script else ""
    return f"""<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{esc(title)} | Κλινική Ψυχολογία ΙΙ</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+Greek:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="../styles.css" />
    {script}
  </head>"""


def build_development(exams: list[DevelopmentExam]) -> str:
    toc = "".join(f"<a href=\"#{slug(exam.title)}\">{esc(exam.title)}</a>" for exam in exams)
    cards = []
    total = 0
    for exam in exams:
        total += len(exam.questions)
        q_html = "".join(f"<li>{esc(q)}</li>" for q in exam.questions)
        meta_html = "".join(f"<p>{esc(m)}</p>" for m in exam.meta)
        cards.append(
            f"""<section class="exam-section" id="{slug(exam.title)}">
              <h2>{esc(exam.title)}</h2>
              <div class="exam-meta">{meta_html}</div>
              <ol class="development-list">{q_html}</ol>
            </section>"""
        )
    return f"""<!doctype html>
<html lang="el">
  {page_head("Θέματα Ανάπτυξης")}
  <body class="notes-page exam-page">
    {nav("development")}
    <main class="notes-shell">
      <aside class="notes-toc" aria-label="Περιεχόμενα σελίδας">
        <p>Περιεχόμενα</p>
        {toc}
      </aside>
      <article class="notes-article">
        <header class="notes-hero">
          <p class="course-label">Κλινική Ψυχολογία ΙΙ</p>
          <h1>Θέματα Ανάπτυξης</h1>
          <p class="exam-intro">Συγκεντρωμένα θέματα ανάπτυξης από το αρχείο παλιών εξετάσεων. Σύνολο θεμάτων: {total}.</p>
        </header>
        <div class="notes-content">
          {''.join(cards)}
        </div>
      </article>
    </main>
  </body>
</html>
"""


def slug(text: str) -> str:
    value = re.sub(r"\s+", "-", text.strip().lower())
    value = re.sub(r"[^0-9a-zA-Z\u0370-\u03ff-]+", "", value)
    return value.strip("-") or "section"


def build_multiple_choice(questions: list[QuizQuestion]) -> str:
    grouped: dict[str, list[QuizQuestion]] = {}
    for question in questions:
        grouped.setdefault(question.group, []).append(question)
    first_indexes: dict[str, int] = {}
    running_index = 0
    for group, items in grouped.items():
        first_indexes[group] = running_index
        running_index += len(items)
    nav_groups = "".join(
        f"<button type=\"button\" class=\"quiz-jump\" data-target-index=\"{first_indexes[group]}\">{esc(group)} ({len(items)})</button>"
        for group, items in grouped.items()
    )
    cards = []
    q_counter = 0
    for group, items in grouped.items():
        for question in items:
            q_counter += 1
            options = []
            correct_labels = []
            for opt_index, option in enumerate(question.options):
                option_id = f"q{q_counter}-o{opt_index}"
                if option.correct:
                    correct_labels.append(option.label)
                options.append(
                    f"""<label class="quiz-option" for="{option_id}">
                      <input id="{option_id}" type="radio" name="q{q_counter}" value="{esc(option.label)}" data-correct="{'true' if option.correct else 'false'}" />
                      <span class="option-label">{esc(option.label)}</span>
                      <span>{esc(option.text)}</span>
                    </label>"""
                )
            correct_json = esc(json.dumps(correct_labels, ensure_ascii=False))
            hidden_attr = " hidden" if q_counter != 1 else ""
            cards.append(
                f"""<article class="quiz-card" data-question="{q_counter}" data-group="{esc(group)}" data-correct-labels="{correct_json}"{hidden_attr}>
                  <div class="quiz-card-head">
                    <span>{esc(group)}</span>
                    <strong>Ερώτηση {question.number} / {q_counter}</strong>
                  </div>
                  <p class="quiz-prompt">{esc(question.prompt)}</p>
                  <div class="quiz-options">{''.join(options)}</div>
                  <div class="quiz-actions">
                    <button type="button" class="check-answer">Έλεγχος</button>
                    <button type="button" class="reset-answer">Reset ερώτησης</button>
                  </div>
                  <details class="answer-details">
                    <summary>Δες τη σωστή απάντηση</summary>
                    <p>{esc(question.answer_note)}</p>
                  </details>
                  <p class="quiz-feedback" aria-live="polite"></p>
                </article>"""
            )

    return f"""<!doctype html>
<html lang="el">
  {page_head("Quiz Πολλαπλής Επιλογής", extra_script=True)}
  <body class="notes-page exam-page">
    {nav("multiple")}
    <main class="notes-shell">
      <aside class="notes-toc" aria-label="Περιεχόμενα σελίδας">
        <p>Ομάδες</p>
        {nav_groups}
      </aside>
      <article class="notes-article">
        <header class="notes-hero">
          <p class="course-label">Κλινική Ψυχολογία ΙΙ</p>
          <h1>Quiz Πολλαπλής Επιλογής</h1>
          <p class="exam-intro">Διάλεξε απάντηση για άμεσο έλεγχο. Η πρόοδός σου αποθηκεύεται τοπικά στον browser.</p>
          <div class="quiz-score" aria-live="polite">
            <span id="quizAnswered">0</span>/<span id="quizTotal">{len(questions)}</span> απαντημένες
            <strong id="quizCorrect">0 σωστές</strong>
          </div>
          <div class="quiz-toolbar" aria-label="Πλοήγηση quiz">
            <div class="quiz-progress">
              <span id="quizPosition">1</span>/<span>{len(questions)}</span>
              <strong id="quizGroup">Ομάδα</strong>
            </div>
            <div class="quiz-nav-controls">
              <button type="button" id="prevQuestion">Προηγούμενο</button>
              <button type="button" id="nextQuestion">Επόμενο</button>
              <button type="button" id="resetAllAnswers">Reset όλων</button>
            </div>
          </div>
        </header>
        <div class="notes-content quiz-content">
          <div class="quiz-stage" id="quizStage">
            {''.join(cards)}
          </div>
          <div class="quiz-nav-controls quiz-bottom-controls" aria-label="Πλοήγηση κάτω μέρους">
            <button type="button" id="prevQuestionBottom">Προηγούμενο</button>
            <button type="button" id="nextQuestionBottom">Επόμενο</button>
          </div>
        </div>
      </article>
    </main>
  </body>
</html>
"""


def build() -> None:
    lines = paragraph_lines()
    exams = parse_development(lines)
    quiz = parse_quiz(lines)
    EXAM_DIR.mkdir(parents=True, exist_ok=True)
    (EXAM_DIR / "development.html").write_text(build_development(exams), encoding="utf-8")
    (EXAM_DIR / "multiple-choice.html").write_text(build_multiple_choice(quiz), encoding="utf-8")
    print(f"Built {len(exams)} development exam groups and {len(quiz)} quiz questions.")


if __name__ == "__main__":
    build()
