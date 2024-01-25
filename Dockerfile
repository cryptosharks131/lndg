FROM python:3-slim
ENV PYTHONUNBUFFERED 1

RUN apk add g++ linux-headers

WORKDIR /lndg
COPY . .

RUN pip install -r requirements.txt
RUN pip install supervisor whitenoise
