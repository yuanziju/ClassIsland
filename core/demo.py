"""
复习曲线计算器 - 可运行 Demo
===========================

运行:
    python core/demo.py

本文件只是对 core/curve.py 的演示, 不含核心算法本身。
"""
import os
import sys

# 让 demo 在任意目录下都能 import 同级的 curve.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from curve import (
    ReviewCurve,
    compute_interval,
    retrievability,
    update_difficulty,
    update_stability,
)


def line(s: str = "") -> None:
    print(s)


def demo_numeric() -> None:
    """演示纯数字模式: 直接调用顶层函数。"""
    print("=== 模式 A: 纯数字模式 ===")
    print("公式:  R(t) = exp(-t / S)")
    print("       interval = -S * ln(target_R)")
    line()

    # 1) 不同稳定性下的下次复习间隔
    print("[1] 不同 S 下, 维持 90% 保留率所需的复习间隔:")
    for S in (3.0, 7.0, 21.0, 60.0):
        days = compute_interval(S, target_retention=0.9)
        print(f"    S = {S:>5.1f} 天  ->  {days:6.2f} 天后复习")
    line()

    # 2) 不同目标保留率
    print("[2] S=7 天时, 不同目标保留率对应的复习间隔:")
    for target_R in (0.95, 0.90, 0.85, 0.70):
        days = compute_interval(7.0, target_retention=target_R)
        print(f"    target_R = {target_R}  ->  {days:5.2f} 天")
    line()

    # 3) 衰减曲线
    print("[3] S=7 天时, 经过若干天后的保留率 R:")
    for t in (0, 1, 3, 7, 14, 30):
        R = retrievability(7.0, t)
        print(f"    经过 {t:>2} 天  ->  R = {R:.2%}")
    line()

    # 4) 单步稳定性/难度更新
    print("[4] 一次复习后的状态变化 (S=7, D=0.4, grade=0.8, R_before=0.6):")
    new_S = update_stability(7.0, 0.4, grade=0.8, retention=0.6,
                             momentum=0.2, time_boost=0.5)
    new_D = update_difficulty(0.4, grade=0.8)
    print(f"    S: 7.00 -> {new_S:.2f}")
    print(f"    D: 0.40 -> {new_D:.2f}")
    line()


def demo_instantiated() -> None:
    """演示实例化模式: 携带状态, 含动量与用户水平调节。"""
    print("=== 模式 B: 实例化模式 (含动量 + 用户水平) ===")
    line()

    # 两个学习者面对同一份内容, 但 user_level 不同:
    #   weak  : 水平较低 (0.4) -> 复习频次更高 (间隔更短)
    #   strong: 水平正常 (1.0) -> 间隔按公式计算
    weak   = ReviewCurve(initial_difficulty=0.5,
                         initial_stability=7.0,
                         momentum=0.3,
                         user_level=0.4,
                         target_retention=0.9)
    strong = ReviewCurve(initial_difficulty=0.5,
                         initial_stability=7.0,
                         momentum=0.3,
                         user_level=1.0,
                         target_retention=0.9)

    print(f"初始状态:  S={weak.S:.2f}天, D={weak.D:.2f}")
    print(f"  弱生下次间隔: {weak.next_interval():.2f} 天  "
          f"(水平低 -> 频次高)")
    print(f"  强生下次间隔: {strong.next_interval():.2f} 天")
    line()

    # 模拟 5 轮复习: 每轮"等到下次复习日"再 review
    print("模拟 5 轮复习 (每轮 advance 到 next_interval, 再以 grade=0.8, 用时 30 分钟复习):")
    print(f"  {'轮次':>4}  {'弱生 S':>8} {'弱生下次':>9}  "
          f"{'强生 S':>8} {'强生下次':>9}")
    for i in range(5):
        weak.advance(weak.next_interval())
        strong.advance(strong.next_interval())
        weak.review(grade=0.8, time_spent=30)
        strong.review(grade=0.8, time_spent=30)
        print(f"  {i + 1:>4}  {weak.S:>8.2f} {weak.next_interval():>9.2f}  "
              f"{strong.S:>8.2f} {strong.next_interval():>9.2f}")
    line()

    # 演示"忘记"事件
    print("演示一次'忘记' (grade=0.2) 对弱生的影响:")
    S_before = weak.S
    weak.advance(weak.next_interval())
    rec = weak.review(grade=0.2)
    print(f"  R_before     = {rec['R_before']:.2%}")
    print(f"  S: {S_before:.2f} -> {weak.S:.2f}  (大幅缩水)")
    print(f"  D: {rec['D']:.2f}  (难度上升)")
    print(f"  下次复习     = {weak.next_interval():.2f} 天后")
    line()


def main() -> None:
    demo_numeric()
    print()
    demo_instantiated()
    print("\n[Demo 完成]")


if __name__ == "__main__":
    main()
