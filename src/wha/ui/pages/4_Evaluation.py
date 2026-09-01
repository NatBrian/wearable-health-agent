"""Evaluation page runner for Streamlit."""

import streamlit as st

from wha.ui.evaluation import render_evaluation_page


def main() -> None:
    """Entry point for Evaluation page."""
    st.set_page_config(page_title="WHA - Evaluation", page_icon="📊", layout="wide")
    render_evaluation_page()


if __name__ == "__main__":
    main()
