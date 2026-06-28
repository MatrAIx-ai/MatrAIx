FROM python:3.12-slim

WORKDIR /app

COPY environment/oasis/ /app/environment/oasis/
COPY persona/ /app/persona/

RUN pip install --no-cache-dir pyyaml requests

ENV PLATFORM_URL=http://platform:8000
ENV PERSONA_PATH=persona/datasets/bench-dev-sample/persona_0001.yaml
ENV LLM_BASE_URL=http://host.docker.internal:8002/v1
ENV LLM_API_KEY=no-key
ENV LLM_MODEL=Qwen/Qwen3-4B
ENV NUM_STEPS=5

CMD ["python", "-m", "environment.oasis.agents.entrypoint"]
