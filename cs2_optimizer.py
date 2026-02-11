#!/usr/bin/env python3
"""CS2 optimizer helper.

Detects basic hardware characteristics and provides practical CS2 tuning
recommendations.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SystemProfile:
    os: str
    cpu: str
    ram_gb: int | None
    gpu: str


@dataclass
class OptimizationPlan:
    tier: str
    launch_options: list[str]
    video_settings: dict[str, str]
    notes: list[str]


def _run(cmd: list[str]) -> str:
    """Run a command and return stdout or empty string when unavailable."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ""
    return result.stdout.strip()


def detect_ram_gb() -> int | None:
    """Try to detect total RAM in GB."""
    try:
        import psutil  # type: ignore

        return round(psutil.virtual_memory().total / (1024**3))
    except Exception:
        pass

    if platform.system() == "Linux" and os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            content = file.read()
        match = re.search(r"MemTotal:\s+(\d+)\s+kB", content)
        if match:
            kb = int(match.group(1))
            return round(kb / (1024**2))

    if platform.system() == "Darwin":
        out = _run(["sysctl", "-n", "hw.memsize"])
        if out.isdigit():
            return round(int(out) / (1024**3))

    if platform.system() == "Windows":
        out = _run(["wmic", "computersystem", "get", "TotalPhysicalMemory"])
        for token in out.split():
            if token.isdigit():
                return round(int(token) / (1024**3))

    return None


def detect_gpu() -> str:
    """Best-effort GPU detection for Linux/macOS/Windows."""
    system = platform.system()

    if system == "Linux":
        if shutil.which("lspci"):
            out = _run(["lspci"])
            gpus = [line for line in out.splitlines() if "VGA" in line or "3D" in line]
            if gpus:
                return gpus[0].split(":", maxsplit=2)[-1].strip()
        if shutil.which("nvidia-smi"):
            out = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
            if out:
                return out.splitlines()[0].strip()

    if system == "Darwin":
        out = _run(["system_profiler", "SPDisplaysDataType"])
        for line in out.splitlines():
            if "Chipset Model:" in line:
                return line.split(":", maxsplit=1)[1].strip()

    if system == "Windows":
        out = _run(["wmic", "path", "win32_VideoController", "get", "name"])
        lines = [line.strip() for line in out.splitlines() if line.strip() and "Name" not in line]
        if lines:
            return lines[0]

    return "Unknown GPU"


def detect_system() -> SystemProfile:
    cpu_name = platform.processor().strip() or platform.uname().processor or "Unknown CPU"
    return SystemProfile(
        os=f"{platform.system()} {platform.release()}",
        cpu=cpu_name,
        ram_gb=detect_ram_gb(),
        gpu=detect_gpu(),
    )


def classify_tier(profile: SystemProfile) -> str:
    """Rough machine tier used for recommendation presets."""
    ram = profile.ram_gb or 8
    gpu = profile.gpu.lower()

    high_keywords = ["rtx 4070", "rtx 4080", "rtx 4090", "rx 7800", "rx 7900"]
    mid_keywords = [
        "rtx 2060",
        "rtx 3060",
        "gtx 1660",
        "rx 6600",
        "rx 6700",
        "arc a750",
    ]

    if ram >= 32 and any(tag in gpu for tag in high_keywords):
        return "high"
    if ram >= 16 and any(tag in gpu for tag in mid_keywords + high_keywords):
        return "medium"
    return "low"


def build_plan(profile: SystemProfile) -> OptimizationPlan:
    tier = classify_tier(profile)

    if tier == "high":
        video = {
            "Resolution": "1920x1080 or 1280x960 stretched",
            "Boost Player Contrast": "Enabled",
            "V-Sync": "Disabled",
            "NVIDIA Reflex": "Enabled + Boost",
            "Global Shadow Quality": "Low",
            "Model / Texture Detail": "Low or Medium",
            "Multisampling": "2x MSAA",
        }
        notes = [
            "CPU still matters in CS2: keep background apps closed.",
            "Use Fullscreen mode for best frame pacing.",
        ]
    elif tier == "medium":
        video = {
            "Resolution": "1280x960 stretched or 1600x900",
            "Boost Player Contrast": "Enabled",
            "V-Sync": "Disabled",
            "NVIDIA Reflex": "Enabled",
            "Global Shadow Quality": "Low",
            "Model / Texture Detail": "Low",
            "Multisampling": "Off or 2x MSAA",
        }
        notes = [
            "Lower shader and particle settings first if FPS drops in smokes.",
            "Lock FPS slightly below your 1% low for stability.",
        ]
    else:
        video = {
            "Resolution": "1280x720 or 1024x768",
            "Boost Player Contrast": "Enabled",
            "V-Sync": "Disabled",
            "NVIDIA Reflex": "Enabled (if available)",
            "Global Shadow Quality": "Very Low / Low",
            "Model / Texture Detail": "Low",
            "Multisampling": "Off",
        }
        notes = [
            "Use lower resolution to prioritize frame rate and responsiveness.",
            "Keep browser, Discord streaming, and overlays disabled while playing.",
        ]

    launch_options = [
        "-novid",
        "+fps_max 0",
        "+cl_showfps 1",
    ]

    return OptimizationPlan(
        tier=tier,
        launch_options=launch_options,
        video_settings=video,
        notes=notes,
    )


def export_cfg(path: str, plan: OptimizationPlan) -> None:
    lines = [
        "// Auto-generated by cs2_optimizer.py",
        "cl_showfps 1",
        "fps_max 0",
        "r_fullscreen_gamma 2.2",
    ]

    if plan.tier == "low":
        lines += [
            "mat_vsync 0",
            "r_drawparticles 0",
        ]
    elif plan.tier == "medium":
        lines += [
            "mat_vsync 0",
        ]
    else:
        lines += [
            "mat_vsync 0",
        ]

    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect PC specs and generate CS2 optimization recommendations.",
    )
    parser.add_argument("--json", action="store_true", help="Output machine profile and plan as JSON")
    parser.add_argument("--export-cfg", metavar="PATH", help="Write simple CS2 config recommendations")
    args = parser.parse_args()

    profile = detect_system()
    plan = build_plan(profile)

    if args.export_cfg:
        export_cfg(args.export_cfg, plan)

    if args.json:
        print(json.dumps({"system": asdict(profile), "plan": asdict(plan)}, ensure_ascii=False, indent=2))
        return

    print("=== System profile ===")
    print(f"OS: {profile.os}")
    print(f"CPU: {profile.cpu}")
    print(f"RAM: {profile.ram_gb if profile.ram_gb is not None else 'Unknown'} GB")
    print(f"GPU: {profile.gpu}")

    print("\n=== Recommended CS2 preset ===")
    print(f"Tier: {plan.tier}")

    print("\nLaunch options:")
    for item in plan.launch_options:
        print(f"  {item}")

    print("\nVideo settings:")
    for key, value in plan.video_settings.items():
        print(f"  {key}: {value}")

    print("\nNotes:")
    for note in plan.notes:
        print(f"  - {note}")

    if args.export_cfg:
        print(f"\nConfig exported to: {args.export_cfg}")


if __name__ == "__main__":
    main()
