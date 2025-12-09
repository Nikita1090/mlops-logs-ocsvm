FROM python:3.11-slim


RUN apt-get update && apt-get install -y --no-install-recommends g++ make && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

#C++ sources
RUN mkdir -p /app/cppsrc /app/bin /app/out 
COPY cppsrc/main.cpp /app/cppsrc/main.cpp

RUN g++ -O3 -std=c++17 -o /app/bin/bgl_template_miner /app/cppsrc/main.cpp

#REST-оболочка
COPY app.py config.py ./

EXPOSE 8001
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]

