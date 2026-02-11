#!/usr/bin/env python3
"""CS2 optimizer helper.

Features:
- Detects PC specs (OS/CPU/RAM/GPU)
- Generates CS2 optimization plan
- Supports game mode profiles
- Reads frametime CSV and computes FPS benchmark metrics
- Checks common background apps (especially relevant for Windows)
- Provides modern-styled Tkinter GUI
"""

from __future__ import annotations

import argparse
import csv
import importlib
import importlib.util
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SystemProfile:
    os: str
    cpu: str
    ram_gb: int | None
    gpu: str


@dataclass
class OptimizationPlan:
    tier: str
    mode: str
    launch_options: list[str]
    video_settings: dict[str, str]
    notes: list[str]


@dataclass
class BenchmarkResult:
    samples: int
    avg_fps: float
    fps_1_low: float
    fps_0_1_low: float


PROFILE_PRESETS: dict[str, dict[str, object]] = {
    "competitive": {
        "extra_launch_options": ["+rate 786432"],
        "video_overrides": {
            "Motion Blur": "Disabled",
            "FidelityFX Super Resolution": "Disabled",
        },
        "notes": ["Competitive preset prioritizes minimal latency and visual clarity."],
    },
    "premier": {
        "extra_launch_options": ["+cl_teamid_overhead_mode 2"],
        "video_overrides": {
            "Boost Player Contrast": "Enabled",
            "Ambient Occlusion": "Disabled",
        },
        "notes": ["Premier preset keeps visibility high in utility-heavy rounds."],
    },
    "streaming": {
        "extra_launch_options": ["+fps_max 240"],
        "video_overrides": {
            "Multisampling": "Off",
            "Shader Detail": "Low",
        },
        "notes": ["Streaming preset leaves headroom for OBS/recording tools."],
    },
}

HEAVY_BACKGROUND_PROCESSES = [
    "chrome.exe",
    "msedge.exe",
    "opera.exe",
    "discord.exe",
    "obs64.exe",
    "steamwebhelper.exe",
    "onedrive.exe",
    "epicgameslauncher.exe",
    "riotclientservices.exe",
]


def _run(cmd: list[str]) -> str:
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


def detect_cpu() -> str:
    system = platform.system()

    if system == "Linux":
        model_name = ""
        if Path("/proc/cpuinfo").exists():
            content = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"model name\s*:\s*(.+)", content)
            if match:
                model_name = match.group(1).strip()
        if model_name:
            return model_name
        if shutil.which("lscpu"):
            out = _run(["lscpu"])
            for line in out.splitlines():
                if "Model name:" in line:
                    return line.split(":", maxsplit=1)[1].strip()

    if system == "Darwin":
        out = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if out:
            return out

    if system == "Windows":
        out = _run(["wmic", "cpu", "get", "name"])
        lines = [line.strip() for line in out.splitlines() if line.strip() and "Name" not in line]
        if lines:
            return lines[0]

    return platform.processor().strip() or platform.uname().processor or "Unknown CPU"


def detect_ram_gb() -> int | None:
    if importlib.util.find_spec("psutil") is not None:
        psutil = importlib.import_module("psutil")
        return round(psutil.virtual_memory().total / (1024**3))

    if platform.system() == "Linux" and os.path.exists("/proc/meminfo"):
        content = Path("/proc/meminfo").read_text(encoding="utf-8")
        match = re.search(r"MemTotal:\s+(\d+)\s+kB", content)
        if match:
            return round(int(match.group(1)) / (1024**2))

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


def _linux_gpu_from_proc() -> str:
    if Path("/proc/driver/nvidia/gpus").exists():
        for info_file in Path("/proc/driver/nvidia/gpus").glob("*/information"):
            content = info_file.read_text(encoding="utf-8", errors="ignore")
            match = re.search(r"Model:\s*(.+)", content)
            if match:
                return match.group(1).strip()
    return ""


def detect_gpu() -> str:
    system = platform.system()

    if system == "Linux":
        if shutil.which("nvidia-smi"):
            out = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
            if out:
                return out.splitlines()[0].strip()

        proc_gpu = _linux_gpu_from_proc()
        if proc_gpu:
            return proc_gpu

        if shutil.which("lspci"):
            out = _run(["lspci"])
            gpus = [line for line in out.splitlines() if "VGA" in line or "3D" in line or "Display" in line]
            if gpus:
                cleaned = gpus[0].split(":", maxsplit=2)[-1].strip()
                cleaned = re.sub(r"\s*\(rev\s+[0-9a-fA-F]+\)$", "", cleaned)
                return cleaned

        drm_cards = sorted(Path("/sys/class/drm").glob("card*/device/vendor"))
        if drm_cards:
            vendor = drm_cards[0].read_text(encoding="utf-8", errors="ignore").strip()
            vendor_map = {
                "0x10de": "NVIDIA GPU",
                "0x1002": "AMD GPU",
                "0x8086": "Intel GPU",
            }
            return vendor_map.get(vendor.lower(), f"GPU vendor {vendor}")

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
    return SystemProfile(
        os=f"{platform.system()} {platform.release()}",
        cpu=detect_cpu(),
        ram_gb=detect_ram_gb(),
        gpu=detect_gpu(),
    )


def classify_tier(profile: SystemProfile) -> str:
    ram = profile.ram_gb or 8
    gpu = profile.gpu.lower()

    high_keywords = ["rtx 4070", "rtx 4080", "rtx 4090", "rx 7800", "rx 7900"]
    mid_keywords = ["rtx 2060", "rtx 3060", "gtx 1660", "rx 6600", "rx 6700", "arc a750"]

    if ram >= 32 and any(tag in gpu for tag in high_keywords):
        return "high"
    if ram >= 16 and any(tag in gpu for tag in high_keywords + mid_keywords):
        return "medium"
    return "low"


def _base_video_by_tier(tier: str) -> dict[str, str]:
    if tier == "high":
        return {
            "Resolution": "1920x1080 or 1280x960 stretched",
            "Boost Player Contrast": "Enabled",
            "V-Sync": "Disabled",
            "NVIDIA Reflex": "Enabled + Boost",
            "Global Shadow Quality": "Low",
            "Model / Texture Detail": "Low or Medium",
            "Multisampling": "2x MSAA",
        }
    if tier == "medium":
        return {
            "Resolution": "1280x960 stretched or 1600x900",
            "Boost Player Contrast": "Enabled",
            "V-Sync": "Disabled",
            "NVIDIA Reflex": "Enabled",
            "Global Shadow Quality": "Low",
            "Model / Texture Detail": "Low",
            "Multisampling": "Off or 2x MSAA",
        }
    return {
        "Resolution": "1280x720 or 1024x768",
        "Boost Player Contrast": "Enabled",
        "V-Sync": "Disabled",
        "NVIDIA Reflex": "Enabled (if available)",
        "Global Shadow Quality": "Very Low / Low",
        "Model / Texture Detail": "Low",
        "Multisampling": "Off",
    }


def _base_notes_by_tier(tier: str) -> list[str]:
    if tier == "high":
        return [
            "CPU still matters in CS2: keep background apps closed.",
            "Use Fullscreen mode for best frame pacing.",
        ]
    if tier == "medium":
        return [
            "Lower shader and particle settings first if FPS drops in smokes.",
            "Lock FPS slightly below your 1% low for stability.",
        ]
    return [
        "Use lower resolution to prioritize frame rate and responsiveness.",
        "Disable overlays and browser tabs before playing.",
    ]


def build_plan(profile: SystemProfile, mode: str = "competitive") -> OptimizationPlan:
    tier = classify_tier(profile)
    video = _base_video_by_tier(tier)
    notes = _base_notes_by_tier(tier)
    launch_options = ["-novid", "+fps_max 0", "+cl_showfps 1"]

    preset = PROFILE_PRESETS.get(mode, PROFILE_PRESETS["competitive"])
    launch_options.extend(preset["extra_launch_options"])
    video.update(preset["video_overrides"])
    notes.extend(preset["notes"])

    return OptimizationPlan(
        tier=tier,
        mode=mode,
        launch_options=launch_options,
        video_settings=video,
        notes=notes,
    )


def export_cfg(path: str, plan: OptimizationPlan) -> None:
    lines = [
        "// Auto-generated by cs2_optimizer.py",
        "cl_showfps 1",
        "fps_max 0",
        "mat_vsync 0",
    ]

    if plan.mode == "streaming":
        lines.append("fps_max 240")

    if plan.tier == "low":
        lines.extend(["r_drawparticles 0", "r_fullscreen_gamma 2.3"])
    elif plan.tier == "medium":
        lines.append("r_fullscreen_gamma 2.2")
    else:
        lines.append("r_fullscreen_gamma 2.1")

    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int((len(sorted_values) - 1) * p)
    return sorted_values[max(0, min(idx, len(sorted_values) - 1))]


def analyze_frametimes_csv(path: str) -> BenchmarkResult:
    frametimes: list[float] = []
    with open(path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            value = row.get("frametime_ms") or row.get("ms") or ""
            if not value:
                for raw in row.values():
                    if raw and raw.replace(".", "", 1).isdigit():
                        value = raw
                        break
            if value:
                frametimes.append(float(value))

    if len(frametimes) < 10:
        raise ValueError("Not enough frametime samples. Need at least 10 rows.")

    sorted_ft = sorted(frametimes)
    avg_ms = statistics.fmean(frametimes)
    p99_ms = _percentile(sorted_ft, 0.99)
    p999_ms = _percentile(sorted_ft, 0.999)

    return BenchmarkResult(
        samples=len(frametimes),
        avg_fps=round(1000.0 / avg_ms, 2),
        fps_1_low=round(1000.0 / p99_ms, 2),
        fps_0_1_low=round(1000.0 / p999_ms, 2),
    )


def detect_running_background_processes() -> list[str]:
    system = platform.system()
    if system != "Windows":
        return []

    out = _run(["tasklist"])
    running = set()
    for line in out.splitlines():
        exe_name = line.split(maxsplit=1)[0].lower() if line else ""
        if exe_name:
            running.add(exe_name)

    return [name for name in HEAVY_BACKGROUND_PROCESSES if name in running]


def write_windows_optimizer_script(path: str) -> None:
    commands = [
        "$processes = @(\n"
        + ",\n".join([f"  '{name}'" for name in HEAVY_BACKGROUND_PROCESSES])
        + "\n)",
        "foreach ($p in $processes) {",
        "  Get-Process -Name ($p -replace '.exe$','') -ErrorAction SilentlyContinue | Stop-Process -Force",
        "}",
        "Write-Host 'Background optimization script completed.'",
    ]
    Path(path).write_text("\n".join(commands) + "\n", encoding="utf-8")


def _render_text(profile: SystemProfile, plan: OptimizationPlan, benchmark: BenchmarkResult | None) -> str:
    lines = [
        "=== System profile ===",
        f"OS: {profile.os}",
        f"CPU: {profile.cpu}",
        f"RAM: {profile.ram_gb if profile.ram_gb is not None else 'Unknown'} GB",
        f"GPU: {profile.gpu}",
        "",
        "=== Recommended CS2 preset ===",
        f"Tier: {plan.tier}",
        f"Mode: {plan.mode}",
        "",
        "Launch options:",
    ]
    lines.extend([f"  {item}" for item in plan.launch_options])

    lines.append("\nVideo settings:")
    lines.extend([f"  {k}: {v}" for k, v in plan.video_settings.items()])

    lines.append("\nNotes:")
    lines.extend([f"  - {note}" for note in plan.notes])

    if benchmark:
        lines.extend(
            [
                "\n=== Benchmark (frametime CSV) ===",
                f"Samples: {benchmark.samples}",
                f"Average FPS: {benchmark.avg_fps}",
                f"1% Low FPS: {benchmark.fps_1_low}",
                f"0.1% Low FPS: {benchmark.fps_0_1_low}",
            ]
        )

    heavy = detect_running_background_processes()
    if heavy:
        lines.append("\nRunning heavy background apps (Windows):")
        lines.extend([f"  - {proc}" for proc in heavy])

    return "\n".join(lines)


def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, ttk

    root = tk.Tk()
    root.title("CS2 Optimizer — Neon Edition")
    root.geometry("1024x700")
    root.configure(bg="#0B1020")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Main.TFrame", background="#0B1020")
    style.configure("Card.TFrame", background="#151C33")
    style.configure("Header.TLabel", background="#0B1020", foreground="#E2E8F0", font=("Segoe UI", 17, "bold"))
    style.configure("Sub.TLabel", background="#151C33", foreground="#93C5FD", font=("Segoe UI", 10, "bold"))
    style.configure("Body.TLabel", background="#151C33", foreground="#E2E8F0", font=("Segoe UI", 10))
    style.configure("Accent.TButton", background="#2563EB", foreground="#FFFFFF", borderwidth=0, padding=7)
    style.map("Accent.TButton", background=[("active", "#1D4ED8")])

    main = ttk.Frame(root, style="Main.TFrame", padding=14)
    main.pack(fill="both", expand=True)

    top = ttk.Frame(main, style="Main.TFrame")
    top.pack(fill="x")

    ttk.Label(top, text="CS2 Optimizer • Neon UI", style="Header.TLabel").pack(side="left")

    mode_var = tk.StringVar(value="competitive")
    ttk.Label(top, text="Mode", style="Body.TLabel").pack(side="left", padx=(20, 6))
    mode_box = ttk.Combobox(top, textvariable=mode_var, values=list(PROFILE_PRESETS.keys()), width=18, state="readonly")
    mode_box.pack(side="left")

    actions = ttk.Frame(top, style="Main.TFrame")
    actions.pack(side="right")

    cards = ttk.Frame(main, style="Main.TFrame")
    cards.pack(fill="x", pady=(12, 10))

    cpu_var = tk.StringVar(value="CPU: ...")
    gpu_var = tk.StringVar(value="GPU: ...")
    ram_var = tk.StringVar(value="RAM: ...")
    os_var = tk.StringVar(value="OS: ...")

    def make_card(parent: ttk.Frame, title: str, variable: tk.StringVar) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=12)
        frame.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(frame, text=title, style="Sub.TLabel").pack(anchor="w")
        ttk.Label(frame, textvariable=variable, style="Body.TLabel", wraplength=220).pack(anchor="w", pady=(6, 0))

    make_card(cards, "Processor", cpu_var)
    make_card(cards, "Graphics", gpu_var)
    make_card(cards, "Memory", ram_var)
    make_card(cards, "System", os_var)

    output = tk.Text(
        main,
        wrap="word",
        bg="#111827",
        fg="#E5E7EB",
        insertbackground="#E5E7EB",
        relief="flat",
        font=("Consolas", 10),
        padx=14,
        pady=12,
    )
    output.pack(fill="both", expand=True)

    def refresh() -> None:
        profile = detect_system()
        plan = build_plan(profile, mode=mode_var.get())

        cpu_var.set(profile.cpu)
        gpu_var.set(profile.gpu)
        ram_var.set(f"{profile.ram_gb if profile.ram_gb is not None else 'Unknown'} GB")
        os_var.set(profile.os)

        text = _render_text(profile, plan, benchmark=None)
        output.delete("1.0", tk.END)
        output.insert(tk.END, text)

    def export_cfg_gui() -> None:
        profile = detect_system()
        plan = build_plan(profile, mode=mode_var.get())
        path = filedialog.asksaveasfilename(defaultextension=".cfg", filetypes=[("CFG files", "*.cfg")])
        if path:
            export_cfg(path, plan)
            output.insert(tk.END, f"\n\nCFG exported: {path}")

    ttk.Button(actions, text="Analyze PC", style="Accent.TButton", command=refresh).pack(side="left", padx=4)
    ttk.Button(actions, text="Export CFG", style="Accent.TButton", command=export_cfg_gui).pack(side="left", padx=4)

    refresh()
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect PC specs and generate CS2 optimization recommendations.")
    parser.add_argument("--json", action="store_true", help="Output profile/plan as JSON")
    parser.add_argument("--mode", choices=list(PROFILE_PRESETS.keys()), default="competitive", help="Optimization profile")
    parser.add_argument("--export-cfg", metavar="PATH", help="Write CS2 cfg recommendations")
    parser.add_argument("--frametimes-csv", metavar="PATH", help="Analyze frametime CSV and include benchmark stats")
    parser.add_argument(
        "--windows-script",
        metavar="PATH",
        help="Write PowerShell script for closing common heavy background apps",
    )
    parser.add_argument("--gui", action="store_true", help="Open modern desktop GUI (Tkinter)")
    args = parser.parse_args()

    if args.gui:
        run_gui()
        return

    profile = detect_system()
    plan = build_plan(profile, mode=args.mode)

    benchmark: BenchmarkResult | None = None
    if args.frametimes_csv:
        benchmark = analyze_frametimes_csv(args.frametimes_csv)

    if args.export_cfg:
        export_cfg(args.export_cfg, plan)

    if args.windows_script:
        write_windows_optimizer_script(args.windows_script)

    if args.json:
        payload: dict[str, object] = {
            "system": asdict(profile),
            "plan": asdict(plan),
        }
        if benchmark:
            payload["benchmark"] = asdict(benchmark)
        payload["running_heavy_processes"] = detect_running_background_processes()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print(_render_text(profile, plan, benchmark))
    if args.export_cfg:
        print(f"\nConfig exported to: {args.export_cfg}")
    if args.windows_script:
        print(f"Windows optimizer script exported to: {args.windows_script}")


if __name__ == "__main__":
    main()
