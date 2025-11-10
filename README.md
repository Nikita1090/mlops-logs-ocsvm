# MLOps Logs OCSVM (BGL, микросервисы + Docker)

Система для сбора и анализа логов на датасете **BGL** (LogHub) с обучением модели **One-Class SVM**. Архитектура — микросервисная, каждый сервис в отдельном контейнере.

## Соответствие критериям задания

### 1. Архитектура и модульность (до 20 баллов)

*  **Обязательная часть (10б):**

  * Независимые сервисы (по контейнеру на сервис)
  * `Dockerfile` у каждого сервиса
  * `docker-compose.yml` для локального развёртывания
  * Чёткая структура проекта (папки `services/*`, `configs/*`, `data/*`, `models/*`, `reports/*`)
*  **Дополнительно (частично):**

  * Масштабируемость: архитектура сервисов допускает добавление источников/моделей без изменений API
  * Открытость: структура и зависимости подготовлены для CI (можно подключить GitHub Actions; пайплайн пока не добавлен)

### 2. Collector (до 10 баллов)

*  **Обязательная часть (5б):**

  * REST API: `/health`, `/collect?offset=&limit=` — выдача батчей строк из **сырого файла `BGL.log`**
  * Обработка ошибок: валидация параметров, замена некорректной кодировки `errors="replace"`


### 3. Storage (до 10 баллов)

*  **Обязательная часть (5б):**

  * REST API CRUD для доменных сущностей:

    * `POST /bgl/logs` и `POST /bgl/logs/bulk` (вставка),
    * `GET /bgl/logs` (листинг с параметрами), `GET /bgl/logs/{id}` (чтение)
  * Таблицы: `bgl_logs` (сырые строки + метка), `models` (метаданные моделей)
*  **Дополнительно (не включено по умолчанию):**

  * Расширенный лог действий в файл

### 4. ML Service (до 20 баллов)

*  **Обязательная часть (10б):**

  * REST API:

    * `POST /train` — обучение **TF-IDF + One-Class SVM** на **нормальных** строках
    * `POST /predict` — инференс (метка 1/-1 + decision score)
    * `GET /summary` — состояние/пути модели
  * Хранение артефактов: `models/ocsvm_tfidf_bgl.joblib`
*  **Дополнительно (частично):**

  * Сложность модели: текстовая векторизация (TF-IDF, n-граммы) + OCSVM
  * Версионность: запись в таблицу `models` (поля `name`, `version`, `path`, `metric_aupr`, `notes`)
  * Хранилище моделей: файловая система + метаданные в БД

### 5. Web Master (до 10 баллов)

*  **Обязательная часть (5б):**

  * API сценариев использования:

    * `POST /scenario/collect_and_store` — сбор батча из `.log` и bulk-запись в `bgl_logs`
    * `POST /scenario/train_model` — обучение на нормальном(без аномалий) подмножестве
    * `POST /scenario/infer_last` — инференс на последних N строках
    * `GET /scenario/report` — генерация HTML-отчёта

### 6. Visualization (до 20 баллов)

*  **Обязательная часть (10б):**

  * Интерактивный GUI на Plotly Dash: 4 кнопки по сценариям, поля ввода, вывод JSON-результатов
*  **Дополнительно (частично):**

  * Отчёты HTML доступны из GUI

### 7. Документирование проекта (до 10 баллов)

*  Инструкции по развёртыванию в этом README
*  Текстовое описание поставленной задачи и подхода (см. ниже)
*  Средства запуска/управления: `docker compose up --build`, curl-команды, GUI

---

## Постановка задачи и выбранный подход

* **Задача:** обнаружение аномалий в логах (BGL) без явной разметки норм/аномалий.
* **Данные:** сырые `.log` строки из BGL (LogHub); первый токен строки — метка аномалии. `'-'` трактуется как **норма**, остальные — аномальные.
* **Подход:** обучаем **One-Class SVM** на нормальных строках. Признаки — **TF-IDF** по тексту сообщения (n-граммы 1–2). На инференсе получаем метку (1 — норма, -1 — аномалия) и decision score.

---

## Архитектура (микросервисы)

* **Collector** — читает `data/BGL/BGL.log` построчно, выдаёт батчи JSON (`offset`, `limit`), парсит первый токен как `alert_tag`, сохраняет остаток в `message`.
* **Storage** — Postgres, таблицы `bgl_logs` и `models`, CRUD-эндпоинты.
* **ML Service** — TF-IDF + One-Class SVM: `/train`, `/predict`, `/summary`, артефакты в `models/`.
* **Web Master** — API-gateway и сценарии (4 шт.), отчёт HTML в `reports/`.
* **Visualization** — Dash UI, кнопки: собрать → обучить → инференс → отчёт.

---
## Запуск
### ->
```bash
docker compose up --build
```

### Проверка сервисов

* Collector: `http://localhost:8001/health`
* Storage: `http://localhost:8002/health`
* ML: `http://localhost:8003/health`
* Web Master: `http://localhost:8000/health`
* GUI (Dash): `http://localhost:8050`

---

## Основные сценарии (через GUI)

В `http://localhost:8050`:

1. **Собрать батч**
2. **Обучить модель**
3. **Инференс**: по последним N строкам (возвращаются метки и decision scores).
4. **Отчёт**: сгенерируется HTML с путями артефактов и списком зарегистрированных моделей.

---

## То же, но через `curl`

```bash
# 1) Сбор и запись
curl -X POST "http://localhost:8000/scenario/collect_and_store?offset=0&limit=1000"

# 2) Обучение
curl -X POST "http://localhost:8000/scenario/train_model?limit=50000"

# 3) Инференс
curl -X POST "http://localhost:8000/scenario/infer_last?n=200"

# 4) Отчёт (скачать)
curl -L "http://localhost:8000/scenario/report" -o reports/report.html
```

---

## Конфигурация

* **Collector:** `configs/collector.yaml` — `dataset_path` (BGL.log), `batch_size`, `encoding`
* **Storage:** `configs/storage.yaml` + `.env` для подключения к Postgres
* **ML:** `configs/ml.yaml` — параметры TF-IDF и OCSVM, путь к модели
* **Web Master:** `configs/web.yaml` — URL-ы сервисов, каталог `reports/`
* **Visualization:** `configs/viz.yaml` — URL Web Master

---

## Структура проекта

```
mlops-logs-ocsvm/
  docker-compose.yml
  .env
  README.md
  data/
    BGL/
      BGL.log
  configs/
    collector.yaml
    storage.yaml
    ml.yaml
    web.yaml
    viz.yaml
  services/
    collector/ (FastAPI)
    storage/   (FastAPI + Postgres)
    ml/        (FastAPI + scikit-learn)
    web/       (FastAPI, сценарии + отчёты)
    viz/       (Plotly Dash)
  models/
    .gitkeep
  reports/
    .gitkeep
```



