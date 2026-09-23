"""Structural checks for the student-facing lifecycle notebook."""

from pathlib import Path

import nbformat


NOTEBOOK = Path(__file__).parents[1] / "notebooks/03_04_adjudication_pricing_monitoring.ipynb"


def _markdown(notebook):
    return "\n".join(
        cell["source"] for cell in notebook.cells if cell.cell_type == "markdown"
    )


def test_lifecycle_notebook_has_student_flow_and_explanations():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    markdown = _markdown(notebook)

    required_sections = [
        "Adjudication",
        "Pricing",
        "Monitoring",
        "Line increases",
        "What to notice",
    ]
    positions = [markdown.index(section) for section in required_sections]

    assert positions == sorted(positions)
    assert "flowchart" in markdown.lower() or "```mermaid" in markdown.lower()
    assert "Approve" in markdown and "Refer" in markdown and "Decline" in markdown
    assert "held-out" in markdown.lower()
    assert "same score spine" in markdown.lower()


def test_lifecycle_notebook_keeps_computational_stages_in_order():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    code = "\n".join(
        cell["source"] for cell in notebook.cells if cell.cell_type == "code"
    )

    markers = [
        "decide(X_all, pd_hat, config)",
        "priced = price_population()",
        "ews = ews_watchlist.score_population()",
        "li = li_candidates.score_population()",
    ]
    positions = [code.index(marker) for marker in markers]

    assert positions == sorted(positions)


def test_notebook_explains_and_demonstrates_deterioration_probability_model():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = notebook.cells
    notebook_text = "\n".join(cell["source"] for cell in cells)

    required_explanation = [
        "How deterioration probability is modeled",
        "deterioration_next_6_12mo",
        "LightGBM",
        "util_drift",
        "business_score",
        "risk tier",
    ]
    for phrase in required_explanation:
        assert phrase.lower() in notebook_text.lower()

    explainer_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "markdown" and "How deterioration probability is modeled" in cell["source"]
    )
    scoring_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "code" and "ews = ews_watchlist.score_population()" in cell["source"]
    )
    assert explainer_index < scoring_index

    code = "\n".join(cell["source"] for cell in cells if cell.cell_type == "code")
    assert "train_test_split" in code
    assert "predict_proba" in code


def test_pricing_section_explains_returns_and_compares_three_rate_cases():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = notebook.cells
    pricing_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "markdown" and "## 2. Pricing" in cell["source"]
    )
    pricing_markdown = cells[pricing_index]["source"]
    assert "ROE" in pricing_markdown
    assert "RAROC" in pricing_markdown
    assert "business decision" in pricing_markdown.lower()

    waterfall_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "code" and "case_specs" in cell["source"]
    )
    waterfall_code = cells[waterfall_index]["source"]
    for label in ["Below hurdle", "Above hurdle / below recommended", "Above recommended"]:
        assert label in waterfall_code
    assert "pd.DataFrame" in waterfall_code
    assert waterfall_index > pricing_index


def test_adjudication_section_explains_policy_and_typical_bank_parameters():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = notebook.cells
    section_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "markdown" and "## 1. Adjudication" in cell["source"]
    )
    section = cells[section_index]["source"].lower()

    for phrase in [
        "policy layer",
        "hard knockout",
        "pd zones",
        "refer override",
        "dscr",
        "public_records",
        "prior_delinquencies",
        "leverage",
        "requested_amount / annual_revenue",
        "kyc",
        "collateral",
    ]:
        assert phrase.lower() in section


def test_monitoring_section_explains_in_sample_vs_held_out_capture_gap():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = notebook.cells
    explanation_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "markdown" and "Why in-sample capture can be higher" in cell["source"]
    )
    explanation = cells[explanation_index]["source"].lower()
    for phrase in ["54%", "21%", "overfit", "unseen", "held-out", "gate"]:
        assert phrase.lower() in explanation

    curve_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "code" and "in_sample_10" in cell["source"]
    )
    assert explanation_index < curve_index


def test_line_increase_section_states_exact_offer_rules():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    cells = notebook.cells
    section_index = next(
        i for i, cell in enumerate(cells)
        if cell.cell_type == "markdown" and "## 4. Line increases" in cell["source"]
    )
    section = cells[section_index]["source"].lower()
    for phrase in [
        "0.3121",
        "0.0741",
        "15%",
        "65% utilization",
        "50% of current credit limit",
        "30% of annual revenue",
        "flowchart",
    ]:
        assert phrase.lower() in section
