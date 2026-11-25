"""待删齐套读轨审计。"""
from __future__ import annotations

from app.services import tombcount as core
from app.services import tombcount_cutover as cutover
from app.services import tombcount_dualwrite as dual


def audit_summary() -> dict:
    return {
        "title": "待删齐套审计",
        "core": core.dashboard(),
        "cutover": cutover.board(),
        "dualwrite": dual.dual_board(),
        "half": core.half_fix_display(),
    }
