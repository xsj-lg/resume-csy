#!/usr/bin/env python3
from __future__ import annotations

try:
    from backend.controllers.resume_controller import run
except ModuleNotFoundError:
    from app.backend.controllers.resume_controller import run


if __name__ == "__main__":
    run()
