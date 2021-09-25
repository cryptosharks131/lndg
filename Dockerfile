FROM python:3
ENV PYTHONUNBUFFERED 1
RUN git clone https://github.com/cryptosharks131/lndg.git /lndg
WORKDIR /lndg
RUN pip install -r requirements.txt
COPY docker-entrypoint.sh /usr/local/etc/entrypoint.sh
RUN ["chmod", "+x", "/usr/local/etc/entrypoint.sh"]
ENTRYPOINT ["/usr/local/etc/entrypoint.sh"]