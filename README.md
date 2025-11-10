# MLOps Logs OCSVM (BGL, микросервисы + Docker)

Система для сбора и анализа логов BGL (LogHub) с выделением шаблонов, TF-IDF векторизацией и обучением модели One-Class SVM. Архитектура микросервисная, каждый сервис в отдельном контейнере.

## Соответствие критериям задания

### 1. Архитектура и модульность

* Независимые сервисы: `collector_cpp`, `storage`, `ml`, `web`, `viz`, `logs_db`
* Каждый сервис имеет Dockerfile
* `docker-compose.yml` для развёртывания
* Конфиги YAML, отдельные папки для данных, моделей и отчётов
* Система допускает добавление новых моделей и источников данных

### 2. Collector (C++)

* Реализован на C++, FastAPI-обёртка для REST
* Задача: обработка `.log` файлов, выделение шаблонов и TF-IDF векторизация
* Выдаёт данные в виде sparse-векторов (`indices`, `values`, `dim`, `is_alert`)
* REST: `/build` (шаблоны + TF-IDF), `/collect_vectors`, `/health`

### 3. Storage (PostgreSQL + FastAPI)

* Таблицы:

  * `bgl_vectors`: sparse-вектора + `is_alert`
  * `models`: реестр моделей (`name`, `version`, `path`, `metric_aupr`, `notes`)
* CRUD-эндпоинты для загрузки и выборки векторов
* Поддержка bulk-вставок
* Эндпоинт обновления метрики модели

### 4. ML Service

* Формат входа: sparse CSR-вектора
* Обучение: One-Class SVM на нормальных событиях
* REST:

  * `/train_vectors`
  * `/predict_vectors`
  * `/summary`
* Модель сохраняется на FS + регистрируется в БД

### 5. Web Master

* API-gateway для сценариев:

  * `/scenario/collect_templates`
  * `/scenario/collect_vectors_batch`
  * `/scenario/train_model_vectors`
  * `/scenario/infer_last_vectors`
  * `/scenario/report` (генерация HTML-отчёта)
* Обработка ошибок, роутинг ко всем сервисам

### 6. Visualization (Dash UI)

* Веб-интерфейс:

  * Построить шаблоны
  * Собрать батч векторов
  * Обучить OCSVM
  * Инференс
  * Генерировать отчёт
* Вывод JSON-ответов
* Ссылка на скачивание отчёта

### 7. Документация

* Этот README

---

## Постановка задачи и подход

* Данные: BGL `*.log`, формат LogHub
* Первый токен строки определяет `is_alert` (`-` = норма)
* C++ строит шаблоны и TF-IDF словарь, генерирует sparse-вектора
* One-Class SVM обучается на нормальных векторах
* Метрика — AUPRC на последних данных (истинные метки из BGL)

---

## Архитектура

| Сервис        | Назначение                                        |
| ------------- | ------------------------------------------------- |
| collector_cpp | C++ лог-парсер, шаблоны, TF-IDF, векторизация     |
| storage       | PostgreSQL + FastAPI, хранение векторов и моделей |
| ml            | Обучение и инференс OCSVM                         |
| web           | API-gateway, сценарии, отчёты                     |
| viz           | Dash UI                                           |
| logs_db       | Postgres контейнер                                |

---

## Запуск

```bash
docker compose up --build -d
```

Проверка:

| Компонент  | URL                                                          |
| ---------- | ------------------------------------------------------------ |
| Collector  | [http://localhost:8001/health](http://localhost:8001/health) |
| Storage    | [http://localhost:8002/health](http://localhost:8002/health) |
| ML         | [http://localhost:8003/health](http://localhost:8003/health) |
| Web Master | [http://localhost:8000/health](http://localhost:8000/health) |
| GUI        | [http://localhost:8050](http://localhost:8050)               |

---

## Сценарии через GUI

1. Построить шаблоны (C++)
2. Собрать вектора (C++)
3. Обучить модель (ML + запись в БД)
4. Инференс по последним N
5. Сгенерировать отчёт (HTML)

---

## Сценарии через curl

```bash
curl -X POST "http://localhost:8000/scenario/collect_templates"

curl -X POST "http://localhost:8000/scenario/collect_vectors_batch?offset=0&limit=2000"

curl -X POST "http://localhost:8000/scenario/train_model_vectors?n=50000"

curl -X POST "http://localhost:8000/scenario/infer_last_vectors?n=1000"

curl -L "http://localhost:8000/scenario/report" -o reports/report.html
```


---

## Конфигурация

* `configs/*.yaml` — параметры сервисов
* `models/` — модели OCSVM и TF-IDF
* `reports/` — HTML-отчёты
