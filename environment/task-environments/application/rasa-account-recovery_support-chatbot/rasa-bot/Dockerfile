FROM rasa/rasa:3.6.21-full

LABEL org.opencontainers.image.source="https://github.com/RasaHQ/rasa"

USER root
WORKDIR /app

COPY config.yml domain.yml credentials.yml endpoints.yml ./
COPY data ./data

RUN rasa train --fixed-model-name account_recovery

EXPOSE 5005

USER 1001

CMD ["run", "--enable-api", "--cors", "*", "--port", "5005", "--model", "/app/models/account_recovery.tar.gz"]
