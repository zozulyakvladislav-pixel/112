# CS2 PC Optimizer

Приложение теперь включает **все идеи из MVP roadmap**:

1. ✅ Определение характеристик ПК (OS/CPU/RAM/GPU).
2. ✅ Подбор оптимизации для CS2 по тиру (`low` / `medium` / `high`).
3. ✅ Профили под разные режимы (`competitive`, `premier`, `streaming`).
4. ✅ Анализ FPS-бенчмарка по CSV frametime (average / 1% low / 0.1% low).
5. ✅ Проверка тяжелых фоновых процессов Windows.
6. ✅ Генерация PowerShell-скрипта для фоновой оптимизации Windows.
7. ✅ GUI на `tkinter`.

---

## Быстрый старт

```bash
python3 cs2_optimizer.py
```

JSON-режим:

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

## FPS Benchmark (frametime CSV)

Поддерживается CSV с заголовком `frametime_ms` или `ms`.

Пример:

```csv
frametime_ms
4.2
4.7
5.1
...
```

Анализ:

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
