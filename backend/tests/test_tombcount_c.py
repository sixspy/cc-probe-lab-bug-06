"""待删齐套 · 丙组：打待删与结栏并发不得假满。

契约（题面争用失败测）：
- 并发下出现“正式集为空却齐套满” → 红。
- 并发后两轨编号不得互窜、不得丢失。
"""
from __future__ import annotations

from app.services import 目录
from tests._并发工具 import run_race


def test_并发打待删与结栏无假满():
    果 = run_race(轮数=8, 每批=2, 删光=False)
    assert not 果["错"], 果["错"]
    assert 果["并发执行"] == 8
    # 每轮都真实并发（结栏射新行 ∥ 打待删旧行），两轨不得互窜或丢失。
    assert 果["空正式灯绿"] == 0, "正式集为空时仍亮齐套 → 假满"
    assert 果["最终齐套灯"] is not None


def test_并发删光后齐套灯熄灭():
    果 = run_race(轮数=6, 每批=2, 删光=True)
    assert not 果["错"], 果["错"]
    assert 果["空正式灯绿"] == 0
    灯 = 目录.齐套灯()
    assert 灯["齐套"] is False
    assert 灯["正式行数"] == 0
