import random
from sys import stderr
from typing import Final

# Neukölln's digest
PROGRESS_INDICATION_CHARCATERS: Final = "✓→🚴✊★☆⯪𓄁𓅯▶️✴️🪇⚒️🧻🚬🗿🎳⏳🌝☕🐑🐞🌼🪱🌸🏵💮️"


def indicate_progress():
    stderr.write(random.choice(PROGRESS_INDICATION_CHARCATERS))
