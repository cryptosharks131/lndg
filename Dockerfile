FROM python:3
ENV PYTHONUNBUFFERED 1
RUN git clone https://github.com/cryptosharks131/lndg.git /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN pip install whitenoise
ENTRYPOINT [ "sh" ]