DEBUG_ENABLED = False

def set_debug(enabled: bool) -> None:
    global DEBUG_ENABLED
    DEBUG_ENABLED = enabled

def logger(message: str) -> None:
    if DEBUG_ENABLED:
        print(message)