"""Shared visual helpers for operational tables with native Streamlit actions."""

from contextlib import contextmanager

import streamlit as st


@contextmanager
def operational_table_container(key):
    """Shared table shell; row controls remain owned by their original page."""
    with st.container(key=key, border=True):
        yield


def operational_table(headers, widths, rows, render_row, key, empty_message="Nenhum item encontrado."):
    """Render a native-widget table shell without taking ownership of row actions or keys."""
    with st.container(key=key, border=True):
        header_columns = st.columns(widths, vertical_alignment="center")
        for column, label in zip(header_columns, headers):
            with column:
                st.caption(label)
        if not rows:
            st.info(empty_message, icon=":material/search_off:")
            return
        for row in rows:
            render_row(row, widths)
