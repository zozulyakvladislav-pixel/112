# CS2 PC Optimizer

Обновил по вашим комментариям:

1. ✅ Починил считывание характеристик ПК (особенно CPU/GPU на Windows, где `wmic` часто не работает).
2. ✅ Кнопка **Analyze PC** теперь с обработкой ошибок и стабильным обновлением карточек железа.
3. ✅ GUI стал еще современнее: кастомный frameless-интерфейс (без стандартных системных кнопок окна), неон-стиль, HUD-компоновка.
4. ✅ Добавил аниме-стилизацию в интерфейс (блок с anime/neko-эстетикой).

---

## Быстрый старт

```bash
python3 cs2_optimizer.py
```

Проверить распознавание характеристик:

```bash
python3 cs2_optimizer.py --json
```

Запуск GUI:

```bash
python3 cs2_optimizer.py --gui
```

---

## Что улучшено в детекте железа

### CPU
- Linux: `/proc/cpuinfo` → `lscpu`
- macOS: `sysctl machdep.cpu.brand_string`
- Windows: `wmic cpu get name` → fallback `PowerShell Get-CimInstance Win32_Processor`

### GPU
- Linux: `nvidia-smi` → `/proc/driver/nvidia/...` → `lspci` → `/sys/class/drm`
- macOS: `system_profiler SPDisplaysDataType`
- Windows: `wmic win32_VideoController` → fallback `PowerShell Get-CimInstance Win32_VideoController`

### RAM
- `psutil` (если установлен)
- иначе системные fallback-методы по ОС

---

## Интерфейс

- Кастомное окно без стандартных «виндовских» кнопок.
- Свои кнопки закрытия/сворачивания.
- Перемещение окна мышью за верхнюю панель.
- ESC для быстрого выхода.

---

## Остальные возможности

- Профили: `competitive`, `premier`, `streaming`
- CSV benchmark frametime (`--frametimes-csv`)
- Экспорт `cfg` (`--export-cfg`)
- Генерация PowerShell-скрипта для фоновой оптимизации (`--windows-script`)
