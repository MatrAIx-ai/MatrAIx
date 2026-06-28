FROM python:3.12-slim

WORKDIR /app

COPY environment/oasis/gui/ /app/environment/oasis/gui/
COPY environment/oasis/platform/ /app/environment/oasis/platform/
COPY environment/oasis/__init__.py /app/environment/oasis/__init__.py
COPY environments/__init__.py /app/environments/__init__.py 2>/dev/null || true

RUN pip install --no-cache-dir fastapi uvicorn pydantic

ENV DB_PATH=/app/output/simulation.db
ENV PORT=3000

EXPOSE 3000

CMD python -c "\
import os, sys; sys.path.insert(0, '/app');\
import uvicorn;\
from environment.oasis.gui.app import create_dashboard_app;\
app = create_dashboard_app(db_path=os.environ['DB_PATH']);\
uvicorn.run(app, host='0.0.0.0', port=int(os.environ['PORT']))"
