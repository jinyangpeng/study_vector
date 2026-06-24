#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
study_vector 工具链检测脚本
供 justfile 调用，避免 PowerShell 多行 script 的退出码重置 / 字符串引号问题。

退出码：
  0 = 工具链完整
  非 0 = 缺失
stdout 输出表格化报告。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Tuple

# 强制 stdout/stderr 用 UTF-8（Windows GBK 控制台会卡 emoji）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


def check_binary(name: str, version_flag: str = "--version") -> Tuple[bool, str]:
    """检查可执行文件是否存在并能跑出版本号。"""
    path = shutil.which(name)
    if not path:
        return False, "缺失"
    try:
        out = subprocess.run(
            [name, version_flag],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode != 0:
            return False, f"退出码 {out.returncode}"
        first = (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr) else ""
        return True, first
    except Exception as e:  # noqa: BLE001
        return False, f"异常: {e}"


def check_python_uv() -> Tuple[bool, str]:
    """检查 `python -m uv` 是否可用（uv 作为 Python 模块安装）。"""
    py = shutil.which("python")
    if not py:
        return False, "python 不在 PATH"
    try:
        out = subprocess.run(
            [py, "-m", "uv", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return True, out.stdout.strip()
        return False, "uv 模块不可用"
    except Exception as e:  # noqa: BLE001
        return False, f"异常: {e}"


def main() -> int:
    """主函数：检测工具链并打印报告，返回总体状态码。"""
    items: list[tuple[str, bool, str]] = []

    # 必检：docker / node / just
    for name in ("docker", "node", "just"):
        ok, info = check_binary(name)
        items.append((name, ok, info))

    # 必检：uv（先看二进制，再看 python -m uv）
    uv_ok, uv_info = check_binary("uv")
    if not uv_ok:
        uv_ok, uv_info = check_python_uv()
    items.append(("uv", uv_ok, uv_info))

    # 选检：python（没它也能跑 docker，但 uv 必须有 python）
    py_ok, py_info = check_binary("python")
    items.append(("python", py_ok, py_info))

    # 输出报告（给 just 当 stdout 用）
    # 用 ASCII 字符避免 Windows GBK 控制台编码问题
    print(">>> 检查工具链...")
    for name, ok, info in items:
        mark = "[OK]" if ok else "[X]"
        if name == "uv" and ok and "python" in info:
            cmd = "python -m uv"
        elif name == "uv" and ok:
            cmd = "uv"
        else:
            cmd = name
        print(f"  {mark} {cmd:<12} {info}")

    if all(ok for _, ok, _ in items):
        print("[OK] 工具链就绪")
        return 0
    print("[X] 工具链不完整")
    return 1


if __name__ == "__main__":
    sys.exit(main())
