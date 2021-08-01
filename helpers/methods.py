def is_int(str):
    try:
        int(str)
    except ValueError:
        return False
    else:
        return True
