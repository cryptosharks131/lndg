FROM python:3
ENV PYTHONUNBUFFERED 1
RUN git clone https://github.com/cryptosharks131/lndg --depth=1 /app
WORKDIR /app
RUN git checkout "master"
RUN pip install -r requirements.txt
RUN pip install whitenoise
ENTRYPOINT [ "sh" ]