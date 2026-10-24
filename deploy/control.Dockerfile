FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1'
COPY mobile_api.py mobile_sync.py installation_presence.py classroom.py preparation_state.py configure_owner.py ./
ENV COACH_CLASSROOM_DB=/data/control.sqlite3
EXPOSE 8502
CMD ["python", "-m", "uvicorn", "mobile_api:app", "--host", "0.0.0.0", "--port", "8502"]
