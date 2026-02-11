# CS2 PC Optimizer

Обновил приложение по вашим замечаниям:

1. ✅ Улучшено считывание характеристик ПК (CPU/GPU/RAM) с более надежными методами под Linux/Windows/macOS.
2. ✅ Добавлен более современный **Neon**-дизайн GUI (темная тема, карточки железа, акцентные кнопки).
3. ✅ Сохранены все предыдущие возможности (профили, benchmark CSV, windows script, cfg export).

---

## Быстрый старт

```bash
python3 cs2_optimizer.py
```

JSON-режим (проверка, что характеристики считываются):

```bash
python3 cs2_optimizer.py --json
```

Выбор профиля режима:

```bash
python3 cs2_optimizer.py --mode premier
```

Экспорт cfg:

```bash
python3 cs2_optimizer.py --mode competitive --export-cfg autoexec_generated.cfg
```

Запуск GUI:

```bash
python3 cs2_optimizer.py --gui
```

---

## Что улучшено в считывании характеристик

### CPU detection
- Linux: `/proc/cpuinfo` + fallback `lscpu`
- macOS: `sysctl machdep.cpu.brand_string`
- Windows: `wmic cpu get name`

### GPU detection
- Linux: `nvidia-smi` → `/proc/driver/nvidia/gpus/*/information` → `lspci` → `/sys/class/drm`
- macOS: `system_profiler SPDisplaysDataType`
- Windows: `wmic path win32_VideoController get name`

---

## FPS Benchmark (frametime CSV)

Поддерживается CSV с заголовком `frametime_ms` или `ms`.

```bash
python3 cs2_optimizer.py --frametimes-csv frametimes.csv
```

или в JSON:

```bash
python3 cs2_optimizer.py --frametimes-csv frametimes.csv --json
```

---

## Фоновая оптимизация Windows

Проверка тяжелых процессов выполняется автоматически в выводе (на Windows).

Сгенерировать PowerShell-скрипт для закрытия типовых тяжелых процессов:

```bash
python3 cs2_optimizer.py --windows-script optimize_background.ps1
```

---

## Опциональная зависимость

Для более точного определения RAM можно установить `psutil`:

```bash
pip install -r requirements.txt
```
