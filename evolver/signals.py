#!/usr/bin/env python3
"""
snoopy-evolver/evolver/signals.py
信号触发系统 - 零token开销的事件检测

事件触发机制：
1. 外部事件写signal文件（零token）
2. heartbeat轮询signal文件
3. 有signal才触发演化检查
4. 处理完清除signal
"""

import json
import glob
from pathlib import Path
from datetime import datetime

SIGNALS_DIR = Path.home() / ".openclaw" / "evolver" / "signals"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

SIGNALS = {
    "git_push": "Git push 操作",
    "task_complete": "任务完成",
    "failure": "失败/错误",
    "migration": "文件迁移",
    "new_module": "新模块创建",
    "retry": "重试/返工",
    "low_success_rate": "低成功率",
}

def write_signal(signal_type: str, metadata: dict = None) -> None:
    """写入信号文件，触发演化检查"""
    signal_file = SIGNALS_DIR / f"{signal_type}.signal"
    data = {
        "type": signal_type,
        "ts": datetime.now().isoformat(),
        "metadata": metadata or {}
    }
    with open(signal_file, "w") as f:
        json.dump(data, f)

def read_signals() -> list:
    """读取所有待处理的信号"""
    signals = []
    pattern = str(SIGNALS_DIR / "*.signal")
    for sf in glob.glob(pattern):
        try:
            with open(sf) as f:
                signals.append(json.load(f))
        except:
            pass
    return signals

def clear_signal(signal_type: str) -> None:
    """清除已处理的信号"""
    signal_file = SIGNALS_DIR / f"{signal_type}.signal"
    if signal_file.exists():
        signal_file.unlink()

def clear_all_signals() -> None:
    """清除所有信号"""
    pattern = str(SIGNALS_DIR / "*.signal")
    for sf in glob.glob(pattern):
        Path(sf).unlink()

def has_signals() -> bool:
    """检查是否有待处理信号"""
    pattern = str(SIGNALS_DIR / "*.signal")
    return len(glob.glob(pattern)) > 0

def get_signal_count() -> int:
    """返回待处理信号数量"""
    pattern = str(SIGNALS_DIR / "*.signal")
    return len(glob.glob(pattern))
