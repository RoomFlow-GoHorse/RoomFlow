import streamlit as st

from views.components.ui_components import badge, empty_state


def reservation_cards(items):
    if not items:
        empty_state("Nenhuma reserva", "Nao ha itens para os filtros selecionados.")
        return
    for item in items:
        st.html(
            f"""
            <div class="rf-card">
              <div style="display:flex;justify-content:space-between;gap:12px">
                <div><strong>{item['title']}</strong><br><span style="color:var(--muted)">{item['space']} - {item['date']} - {item['start']} as {item['end']}</span></div>
                <div>{badge(item['status'])} {badge(item['priority'])}</div>
              </div>
              <p style="color:var(--soft)">{item['justification']}</p>
            </div>
            """
        )
