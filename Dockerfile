FROM python:3-alpine
ENV PYTHONUNBUFFERED 1

RUN apk add g++ linux-headers
COPY . /app/
WORKDIR /app

RUN pip install -r requirements.txt
RUN pip install supervisor whitenoise
