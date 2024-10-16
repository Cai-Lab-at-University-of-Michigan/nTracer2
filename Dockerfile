ARG server_port=8085

FROM python:3.10-slim AS backend-builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++
RUN pip --no-cache-dir install cython
RUN pip --no-cache-dir install --user neuroglancer ngauge flask flask-socketio numpy python-dotenv fastapi "uvicorn[standard]" sse-starlette httpx
COPY backend/compile_cython.py /app/compile_cython.py
COPY backend/algorithm /app/algorithm
WORKDIR /app
RUN python compile_cython.py build_ext --inplace

#FROM python:3.10-slim as db-builder
#RUN apt-get update && apt-get install -y --no-install-recommends libgeos-dev gcc g++ libsqlite3-dev liblz4-dev libbz2-dev libboost-all-dev libx264-dev libzstd-dev
#COPY db /app
#WORKDIR /app
#RUN g++ -O3 app.cpp -Iasio_include -lpthread -lsqlite3 -lz -lx264 -lzstd -std=c++17

FROM node:gallium-alpine3.18 AS dashboard-builder
ARG server_port
ENV REACT_APP_SERVER_PORT=$server_port
COPY dashboard /app
WORKDIR /app
RUN npm install
RUN npm run build

FROM python:3.10-slim
RUN mkdir /app

ARG server_port
ARG neuroglancer_port=8050
ARG cdn_url=https://sonic2.cai-lab.org/data/
ARG dataset_id=packed2
ARG public_url=http://localhost

ENV CDN_URL=$cdn_url
ENV CDN_URL_HOST=$cdn_url
ENV CDN_URL_LOCAL=$cdn_url
ENV CDN_URL_LOCAL_HOST=$cdn_url
ENV NEUROGLANCER_PORT=$neuroglancer_port
ENV SERVER_PORT=$server_port
ENV PUBLIC_URL=$public_url
ENV DATASET_ID=$dataset_id

ENV PATH=/root/.local/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends libx264-dev 
RUN apt-get install -y nginx

COPY backend /app
#COPY --from=db-builder /app/a.out /app/db-server
COPY --from=backend-builder /app/algorithm/astar/*.so ./app/algorithm/astar/
COPY --from=backend-builder /root/.local /root/.local
COPY --from=dashboard-builder /app/build /app/dashboard
#COPY docker_runner.sh /app/docker_runner.sh
#COPY db/data /mnt/data1
COPY /landing /app/landing
WORKDIR /app

EXPOSE $neuroglancer_port
EXPOSE $server_port

RUN chmod +x ./main.py

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["./main.py"]
