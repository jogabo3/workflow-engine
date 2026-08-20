import pathlib
path = pathlib.Path(".retry_success_flag")
if not path.exists():
    path.write_text("first_attempt", encoding="utf-8")
    raise SystemExit(1)
print("retry succeeded on second attempt")
