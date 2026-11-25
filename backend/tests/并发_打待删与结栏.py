#!/usr/bin/env python3
"""并发脚本：打待删 × 结栏 压测，输出可区分的齐套读集。

用法（开发机，无容器时）：
    PYTHONPATH=backend .venv/bin/python backend/tests/并发_打待删与结栏.py --轮数 20

脚本使用独立临时库，不动运行中的数据目录。
退出码：0 = 两轨自洽且无假满；1 = 发现假满/串轨/丢失。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

_根 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_根 / "backend"))

os.environ.setdefault("夹具目录", str(_根 / "fixtures"))


def _初始化(目录: Path) -> None:
    os.environ["数据目录"] = str(目录)
    import app.db as db

    db.数据目录 = 目录
    db.库路径 = 目录 / "探栏.db"
    from app import seed

    seed.初始化库()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--轮数", type=int, default=12)
    ap.add_argument("--每批", type=int, default=2)
    ap.add_argument("--删光", action="store_true", help="每轮把剩余正式行也打待删")
    ap.add_argument("--存储", default="", help="数据目录；默认临时目录")
    args = ap.parse_args(argv)

    from tests._并发工具 import run_race

    if args.存储:
        存储 = Path(args.存储)
        存储.mkdir(parents=True, exist_ok=True)
        _初始化(存储)
        果 = run_race(轮数=args.轮数, 每批=args.每批, 删光=args.删光)
    else:
        with tempfile.TemporaryDirectory(prefix="探栏-并发-") as td:
            _初始化(Path(td))
            果 = run_race(轮数=args.轮数, 每批=args.每批, 删光=args.删光)

    print(json.dumps(果, ensure_ascii=False, indent=2, default=str))
    return 0 if not 果["错"] and 果["空正式灯绿"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
