# CS2 PC Optimizer (MVP)

Мини-приложение на Python, которое:
1. Определяет базовые характеристики компьютера (OS/CPU/RAM/GPU).
2. Подбирает пресет оптимизации для Counter-Strike 2 (`low` / `medium` / `high`).
3. Генерирует рекомендации по launch options и видео-настройкам.
4. Может экспортировать простой `.cfg` файл.

## Быстрый старт

```bash
python3 cs2_optimizer.py
```

JSON-режим:

```bash
python3 cs2_optimizer.py --json
```

Экспорт cfg:

```bash
python3 cs2_optimizer.py --export-cfg autoexec_generated.cfg
```

## Опциональная зависимость

Для более точного определения RAM можно установить `psutil`:

```bash
pip install psutil
```

## Идеи для следующего шага

- GUI (например, `customtkinter` или Electron).
- Бенчмарк FPS (сценарий прогонов карты и логирование времени кадра).
- Автопрофили под разные режимы игры.
- Проверка и оптимизация фоновых процессов Windows.
