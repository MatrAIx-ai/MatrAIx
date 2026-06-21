FROM python:3.12-slim

WORKDIR /app

COPY environments/oasis/ /app/environments/oasis/
COPY personas/ /app/personas/

RUN pip install --no-cache-dir pyyaml requests

ENV PLATFORM_URL=http://platform:8000
ENV PERSONA_PATH=personas/Jun20_1k_persona_description/ID0001.yaml
ENV LLM_BASE_URL=http://host.docker.internal:8002/v1
ENV LLM_API_KEY=no-key
ENV LLM_MODEL=Qwen/Qwen3-4B
ENV NUM_STEPS=5

CMD ["python", "-m", "environments.oasis.agents.entrypoint"]
