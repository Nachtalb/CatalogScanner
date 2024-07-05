TG_BASE_URL = "https://api.telegram.org/bot"

TG_MAX_DOWNLOAD_SIZE = 20 * 1024 * 1024  # 20 MB
# TG_LOCAL_MAX_DOWNLOAD_SIZE  # no size limit in local mode


def sel(text: str) -> str:
    """Strip each line

    Args:
        text (str): Text to be stripped

    Returns:
        str: Stripped text
    """
    return "\n".join(line.strip() for line in text.splitlines())
