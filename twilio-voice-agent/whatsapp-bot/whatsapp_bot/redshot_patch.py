"""
RedShot 0.1.1 on PyPI ships a SyntaxError in redshot/object/message.py (broken quotes
inside an f-string). A naive fix using .replace('\\n', '\\\\n') inside the f-string
braces is also invalid: f-string expressions cannot contain backslashes.

We rewrite the inner expression to:
  self.text.replace(chr(10), chr(92) + 'n')
"""

from __future__ import annotations

import pathlib
import sys

# Broken wheel: literal \\n between double quotes inside the f-string expression.
_PYPI_NEEDLE = 'self.text.replace("\\n", "\\\\n")'
# Broken "fix" some editors apply: backslashes inside f-string `{...}` (Python rejects).
_BAD_NEEDLE = "self.text.replace(" + repr(chr(10)) + ", " + repr("\\n") + ")"
# Valid inside f-string braces: no backslash tokens in the expression.
_REPLACEMENT = "self.text.replace(chr(10), chr(92) + 'n')"


def ensure_redshot_message_py_fixed() -> bool:
    for entry in sys.path:
        root = pathlib.Path(entry)
        path = root / "redshot" / "object" / "message.py"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if _PYPI_NEEDLE in text:
            text = text.replace(_PYPI_NEEDLE, _REPLACEMENT, 1)
            path.write_text(text, encoding="utf-8")
            return True
        if _BAD_NEEDLE in text:
            text = text.replace(_BAD_NEEDLE, _REPLACEMENT, 1)
            path.write_text(text, encoding="utf-8")
            return True
        return True
    return False
