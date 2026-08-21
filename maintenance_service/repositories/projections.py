def update_window(window, state, effective_from):
    window.version += 1
    window.effective_from = effective_from
    window.timezone = state["timezone"]
    window.rule = state["rule"]
    window.priority = state["priority"]
    window.active = state["active"]
    window.save()
    return window
