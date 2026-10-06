errors = [0.0, None]
try:
    print(max(errors) if errors else 0.0)
except TypeError as exc:
    print(type(exc).__name__ + ':', exc)
