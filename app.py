import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load_json(filename: str) -> dict:
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_facts(docs: list[dict]) -> pd.DataFrame:
    """Mock extraction: one row per document, with a naive 'fact' field."""
    rows = []
    for d in docs:
        rows.append(
            {
                "Document": d["id"],
                "Type": d["type"],
                "Year": d["year"],
                "Page": d["page"],
                "Extracted fact": d["text"],
            }
        )
    return pd.DataFrame(rows)


def reconcile(clients_meta: dict, docs: list[dict]) -> tuple[float, list[str]]:
    """Very naive mock reconciliation: sum numeric amounts found in doc text."""
    import re

    total = 0.0
    for d in docs:
        for m in re.findall(r"SGD\s?([\d,]+(?:\.\d+)?)", d["text"]):
            try:
                total += float(m.replace(",", ""))
            except ValueError:
                pass

    declared = clients_meta["declared_net_worth"]
    flags = []
    if total < declared * 0.5:
        flags.append(
            f"Documented amounts (SGD {total:,.0f}) cover less than 50% of declared "
            f"net worth (SGD {declared:,.0f})."
        )
    if total > declared * 1.5:
        flags.append(
            f"Documented amounts (SGD {total:,.0f}) exceed declared net worth "
            f"(SGD {declared:,.0f}) by a large margin."
        )
    return total, flags


def draft_report(client_key: str, meta: dict, docs: list[dict], flags: list[str]) -> str:
    lines = [
        f"# Source of Wealth Report — {meta['name']}",
        "",
        f"**Profile:** {meta['profile']}",
        f"**Declared net worth:** SGD {meta['declared_net_worth']:,.0f}",
        "",
        "## Sources of wealth",
    ]
    for d in docs:
        lines.append(f"- {d['text']}  \n  *Source: {d['id']}, page {d['page']}*")
    lines.append("")
    lines.append("## Evidence table")
    lines.append("| Document | Type | Year | Page | Fact |")
    lines.append("|---|---|---|---|---|")
    for d in docs:
        lines.append(
            f"| {d['id']} | {d['type']} | {d['year']} | {d['page']} | {d['text']} |"
        )
    lines.append("")
    lines.append("## Gaps and red flags")
    if flags:
        for f in flags:
            lines.append(f"- {f}")
    else:
        lines.append("- No automated flags raised. Manual review still required.")
    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="SourceTrace (Prototype)", page_icon="🔎", layout="wide")
    st.title("🔎 SourceTrace — Source of Wealth draft assistant")
    st.caption(
        "Prototype with mock data only. No real client documents are processed. "
        "Not for production use."
    )

    clients = load_json("clients.json")
    documents = load_json("documents.json")

    with st.sidebar:
        st.header("Client")
        client_key = st.selectbox(
            "Select a synthetic client",
            options=list(clients.keys()),
            format_func=lambda k: f"{clients[k]['name']} ({k})",
        )
        st.markdown("---")
        st.markdown(
            "**Note:** This is a demo. Extraction, reconciliation and drafting "
            "are simulated from pre-loaded mock documents."
        )

    meta = clients[client_key]
    docs = documents[client_key]

    col1, col2, col3 = st.columns(3)
    col1.metric("Client", meta["name"])
    col2.metric("Declared net worth", f"SGD {meta['declared_net_worth']:,.0f}")
    col3.metric("Documents in pack", len(docs))

    st.subheader("1. Uploaded document pack (mock)")
    st.dataframe(
        pd.DataFrame(docs)[["id", "type", "year", "page", "text"]],
        use_container_width=True,
        hide_index=True,
    )

    if st.button("Run extraction + reconciliation", type="primary"):
        with st.spinner("Extracting facts and reconciling figures..."):
            facts_df = extract_facts(docs)
            total, flags = reconcile(meta, docs)
            report_md = draft_report(client_key, meta, docs, flags)

        st.subheader("2. Extracted facts")
        st.dataframe(facts_df, use_container_width=True, hide_index=True)

        st.subheader("3. Reconciliation")
        st.write(
            f"Sum of documented SGD amounts: **SGD {total:,.0f}** "
            f"vs declared net worth **SGD {meta['declared_net_worth']:,.0f}**."
        )
        if flags:
            for f in flags:
                st.warning(f)
        else:
            st.success("No reconciliation flags raised by the mock rules.")

        st.subheader("4. Draft Source of Wealth report")
        st.markdown(report_md)

        st.download_button(
            "Download draft report (Markdown)",
            data=report_md,
            file_name=f"sow_draft_{client_key}.md",
            mime="text/markdown",
        )


if __name__ == "__main__":
    main()
