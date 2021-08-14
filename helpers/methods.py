def is_int(str):
    try:
        int(str)
    except ValueError:
        return False
    else:
        return True


def format_string(string, size):
    if len(string) > size:
        return string[: size - 3] + "..."
    return string

def bullet_list(rows):
    return "\n".join(f"• {row}" for row in rows)