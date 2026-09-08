from views.components.sidebar import render_sidebar


def shell_start(user):
    render_sidebar(user)


def shell_end():
    """Keeps the shared app-shell call site stable for the page router."""
