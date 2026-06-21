FROM python:3.12-slim

WORKDIR /app

COPY environments/oasis/ /app/environments/oasis/

RUN pip install --no-cache-dir pyyaml requests fastapi uvicorn pydantic

ENV DB_PATH=:memory:
ENV RECSYS_TYPE=random
ENV MAX_REC_POSTS=50
ENV PORT=8000

EXPOSE 8000

CMD python -c "\
import os, uvicorn;\
from environments.oasis.platform.server import create_app;\
app = create_app(db_path=os.environ['DB_PATH'], recsys_type=os.environ['RECSYS_TYPE'], max_rec_posts=int(os.environ['MAX_REC_POSTS']));\
uvicorn.run(app, host='0.0.0.0', port=int(os.environ['PORT']))"
