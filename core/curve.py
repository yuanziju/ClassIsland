"""
复习曲线计算器 - FSRS × 艾宾浩斯 融合模型
==========================================

本文件只包含核心算法, 不含任何 I/O 或 CLI 细节, 便于作为原理参考
翻译到其他语言。

三参数状态:
    S (Stability)    稳定性, 单位"天". S 越大, 记忆衰减越慢.
    D (Difficulty)   难度, 取值 [0, 1]. 0 = 最易, 1 = 最难.
    R (Retrievability) 可提取性, 此刻还能回忆起的概率, 取值 (0, 1].

核心衰减公式 (艾宾浩斯, FSRS 内部同样使用):
    R(t) = exp(-t / S)

两种使用方式:
    (A) 纯数字模式 - 直接调用顶层函数:
            next_interval = compute_interval(S=7.0, target_retention=0.9)
            R_now         = retrievability(stability=7.0, elapsed_days=3.0)

    (B) 实例化模式 - 携带状态, 支持动量与用户水平调节:
            learner = ReviewCurve(initial_difficulty=0.5,
                                  momentum=0.2,
                                  user_level=0.6)
            learner.advance(days=learner.next_interval())
            learner.review(grade=0.8, time_spent=30)
            print(learner.next_interval())
"""
from __future__ import annotations

import math


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _clamp01(x: float) -> float:
    """把数值限制在 [0, 1] 区间。"""
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


# ---------------------------------------------------------------------------
# 纯函数 (数字模式)
# ---------------------------------------------------------------------------

def retrievability(stability: float, elapsed_days: float) -> float:
    """
    艾宾浩斯衰减: 经过 elapsed_days 天后, 还能记住的比例。
        R(t) = exp(-t / S)
    """
    if stability <= 0.0:
        return 0.0
    if elapsed_days <= 0.0:
        return 1.0
    return math.exp(-elapsed_days / stability)


def compute_interval(stability: float,
                     target_retention: float = 0.9) -> float:
    """
    给定稳定性 S 和目标保留率 target_R, 计算下一次复习应当经过的天数。
    推导:
        R(t) = exp(-t / S) = target_R
        =>   t = -S * ln(target_R)
    """
    if not 0.0 < target_retention < 1.0:
        raise ValueError("target_retention 必须在 (0, 1) 之间")
    if stability <= 0.0:
        return 0.0
    return -stability * math.log(target_retention)


def update_stability(stability: float,
                     difficulty: float,
                     grade: float,
                     retention: float,
                     momentum: float = 0.0,
                     time_boost: float = 0.0) -> float:
    """
    FSRS 风格的稳定性更新 (融合版)。

    参数:
        grade        本次回忆评分 [0, 1]; < 0.5 视为"忘记"。
        retention    复习前的 R, 越低说明"越险些忘记", 增益越大 (恰当难度效应)。
        momentum     实例化模式才用, 放大稳定性增长, 0 = 关闭。
        time_boost   学习时长带来的额外增益, 例如 time_spent_minutes / 60。
    """
    g = _clamp01(grade)
    D = _clamp01(difficulty)

    # 情况一: 没记住 -> 稳定性大幅缩水 (但不归零, 保留一定残余)。
    if g < 0.5:
        return stability * (0.3 + 0.4 * g)

    # 情况二: 记住了 -> 稳定性增长。
    #   (1 - R)            险些忘记的程度, 实现"恰当难度"效应
    #   (1 - D)            越简单增长越快
    #   g                  回忆质量
    #   (1 + momentum + tb) 实例化模式的动量与时长加成
    gain = (1.0 - retention) * (1.0 - D) * g * (1.0 + momentum + time_boost)
    return stability * (1.0 + gain)


def update_difficulty(difficulty: float, grade: float) -> float:
    """
    难度根据本次表现漂移:
        表现差 (g < 0.5) -> D 升
        表现好 (g > 0.5) -> D 降
    """
    g = _clamp01(grade)
    delta = 0.2 * (0.5 - g)
    return _clamp01(difficulty + delta)


# ---------------------------------------------------------------------------
# 实例化模式
# ---------------------------------------------------------------------------

class ReviewCurve:
    """
    有状态的复习曲线学习器。

    参数:
        initial_difficulty : 初始难度 [0, 1]
        initial_stability  : 初始稳定性(天)
        momentum           : 动量参数, 放大 S 增长; 仅实例化模式有意义
        user_level         : 用户当前水平 [0.1, 1]; 越低 -> 复习频次越高
        target_retention   : 目标保留率, 默认 0.9
    """

    def __init__(self,
                 initial_difficulty: float = 0.5,
                 initial_stability: float = 1.0,
                 momentum: float = 0.0,
                 user_level: float = 1.0,
                 target_retention: float = 0.9):
        self.S: float = max(0.1, initial_stability)
        self.D: float = _clamp01(initial_difficulty)
        self.momentum: float = max(0.0, momentum)
        self.user_level: float = max(0.1, min(1.0, user_level))
        self.target_R: float = target_retention
        self.elapsed: float = 0.0
        self.history: list = []

    def retrievability(self) -> float:
        """当前这一刻的保留率 R。"""
        return retrievability(self.S, self.elapsed)

    def advance(self, days: float) -> None:
        """时间流逝 days 天。"""
        if days > 0.0:
            self.elapsed += days

    def review(self, grade: float, time_spent: float = 0.0) -> dict:
        """
        进行一次复习。

        参数:
            grade      : [0, 1] 标准化回忆评分
            time_spent : 本次学习/复习用时(分钟), 用于"加速学习"增益
        返回:
            本次复习的状态快照 dict
        """
        R = self.retrievability()
        g = _clamp01(grade)
        # 60 分钟封顶为 1.0 的额外增益
        time_boost = min(1.0, time_spent / 60.0) if time_spent > 0 else 0.0

        new_S = update_stability(self.S, self.D, g, R,
                                 momentum=self.momentum,
                                 time_boost=time_boost)
        new_D = update_difficulty(self.D, g)

        self.S = new_S
        self.D = new_D
        self.elapsed = 0.0  # 复习后重新计时

        record = {
            "grade": g,
            "R_before": R,
            "S": self.S,
            "D": self.D,
            "time_spent": time_spent,
        }
        self.history.append(record)
        return record

    def next_interval(self) -> float:
        """
        计算下一次复习的间隔(天)。

        user_level 越低, 间隔越短 (复习越频繁), 实现"水平低则频次高"。
        """
        base = compute_interval(self.S, self.target_R)
        return base * self.user_level
