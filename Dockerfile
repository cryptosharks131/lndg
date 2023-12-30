FROM python:3-alpine
ENV PYTHONUNBUFFERED 1
RUN apk add git && git clone https://github.com/cryptosharks131/lndg /app
WORKDIR /app
RUN git checkout "master"
RUN pip install -r requirements.txt
RUN pip install whitenoise
ENTRYPOINT [ "sh" ]