"""栏贯验：分轨对账。正式轨只比已汇总缓冲，归档轨只比待删缓冲。"""
from __future__ import annotations
from app.db import 连接
from app.seed import 此刻
from app.services import 目录


def 水位对账() -> dict:
    return 目录.汇总对账()


def 跑一次() -> dict:
    conn = 连接()
    try:
        在栏 = conn.execute(
            "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='在栏'"
        ).fetchone()["c"]
        已汇总缓冲 = conn.execute(
            "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='已汇总'"
        ).fetchone()["c"]
        汇总报文 = conn.execute(
            "SELECT COALESCE(SUM(报文数),0) AS c FROM 站点汇总账"
        ).fetchone()["c"]
        坏点 = conn.execute("SELECT COUNT(*) AS c FROM 坏点匣").fetchone()["c"]
        对 = 目录._汇总对账(conn)
        正式行数 = 对["正式"]["行数"]
        归档行数 = 对["归档"]["行数"]
        对齐 = 1 if 对["对齐"] else 0
        if 正式行数 == 0:
            说明 = f"正式集为空：汇总账无未删正式行（归档待删 {对['归档']['报文数']} 笔）"
        elif 对齐:
            说明 = "入栏已汇总与正式汇总报文数一致，待删影子已分轨归档"
        else:
            说明 = (
                f"撕裂：已汇总缓冲={已汇总缓冲} 正式汇总报文={汇总报文}"
                f" 归档待删缓冲={对['归档']['待删报文数']} 归档报文={对['归档']['报文数']}"
            )
        时刻 = 此刻()
        conn.execute(
            """INSERT INTO 栏贯验(时刻,在栏笔数,汇总报文数,坏点笔数,是否对齐,说明)
               VALUES (?,?,?,?,?,?)""",
            (时刻, 在栏, int(汇总报文), 坏点, 对齐, 说明),
        )
        conn.commit()
        return {
            "时刻": 时刻,
            "在栏": 在栏,
            "已汇总缓冲": int(已汇总缓冲),
            "汇总报文": int(汇总报文),
            "正式行数": 正式行数,
            "归档行数": 归档行数,
            "归档待删报文": 对["归档"]["报文数"],
            "坏点": 坏点,
            "是否对齐": bool(对齐),
            "正式齐套": 对["正式齐套"],
            "归档齐套": 对["归档齐套"],
            "说明": 说明,
        }
    finally:
        conn.close()


def 只读快照() -> dict:
    """不落库的贯验快照；正式口径剔除待删影子。"""
    conn = 连接()
    try:
        在栏 = conn.execute(
            "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='在栏'"
        ).fetchone()["c"]
        已汇总缓冲 = conn.execute(
            "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='已汇总'"
        ).fetchone()["c"]
        汇总报文 = conn.execute(
            "SELECT COALESCE(SUM(报文数),0) AS c FROM 站点汇总账"
        ).fetchone()["c"]
        坏点 = conn.execute("SELECT COUNT(*) AS c FROM 坏点匣").fetchone()["c"]
        对 = 目录._汇总对账(conn)
        return {
            "在栏": 在栏,
            "已汇总缓冲": int(已汇总缓冲),
            "汇总报文": int(汇总报文),
            "坏点": 坏点,
            "正式行数": 对["正式"]["行数"],
            "归档行数": 对["归档"]["行数"],
            "归档待删报文": 对["归档"]["报文数"],
            "是否对齐": bool(对["对齐"]),
        }
    finally:
        conn.close()
