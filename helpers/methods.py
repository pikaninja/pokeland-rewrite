import traceback
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

async def get_permissions(check):
    try:
        # You can pretty much loop these to get all checks from the command.
        check(0) # This would raise an error, because `0` is passed as ctx
    except Exception as e:
        *frames, last_frame = traceback.walk_tb(e.__traceback__) # Iterate through the generator and get the last element
        frame = last_frame[0] # get the first element to get the trace
        return frame.f_locals['perms']