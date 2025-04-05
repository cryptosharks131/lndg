FROM python:3-slim

ARG LNDG_PORT=8000
ARG SUPERVISOR=1
ENV PYTHONUNBUFFERED 1

# Add group abnd user to run rootless
RUN addgroup -gid 1000 lndg && \
    useradd -r -m -s /bin/bash -g lndg -u 1000 lndg

WORKDIR /lndg

COPY . .

ENV LNDG_PORT=$LNDG_PORT
ENV LNDG_SUPERVISOR=$SUPERVISOR

RUN echo "Install pip deps" && \
    pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install whitenoise

RUN scripts/suinit.sh

EXPOSE $LNDG_PORT

VOLUME [ "/lnd", "/lndg/data" ]

USER 1000

ENTRYPOINT [ "scripts/entrypoint.sh" ]
