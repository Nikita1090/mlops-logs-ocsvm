FROM python:3.11-slim

# build deps для C++
RUN apt-get update && apt-get install -y --no-install-recommends g++ make && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# C++ sources и директории
RUN mkdir -p /app/cppsrc /app/bin /app/out
# ВНИМАНИЕ: здесь ожидается cppsrc/main.cpp
COPY cppsrc/main.cpp /app/cppsrc/main.cpp

# Компиляция бинарника
RUN g++ -O3 -std=c++17 -o /app/bin/bgl_template_miner /app/cppsrc/main.cpp

# REST-оболочка
COPY app.py config.py ./

EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]

