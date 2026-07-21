# Rasa server for RasaHQ/financial-demo, pinned to the last main commit.
# The -spacy-en variant ships rasa[spacy]==3.1.0 plus en_core_web_md, so the
# project trains without extra pip installs.
FROM rasa/rasa:3.1.0-spacy-en

USER root

ADD https://github.com/RasaHQ/financial-demo/archive/7627cebef1571d55855b886cf4ac20459af9566c.tar.gz /tmp/financial-demo.tar.gz
RUN mkdir -p /app/project \
  && tar -xzf /tmp/financial-demo.tar.gz --strip-components=1 -C /app/project \
  && rm /tmp/financial-demo.tar.gz

WORKDIR /app/project

# Point pipeline and action endpoint at the compose service names.
RUN sed -i 's#url: http://localhost:8000#url: http://duckling:8000#' config.yml \
  && sed -i 's#http://localhost:5056/webhook#http://rasa-actions:5055/webhook#' endpoints.yml

# Train at build time so container start is fast and deterministic.
RUN rasa train --fixed-model-name financial-demo \
  && chown -R 1001:1001 /app/project

USER 1001

EXPOSE 5005

CMD ["run", "--enable-api", "--cors", "*", "--port", "5005"]
