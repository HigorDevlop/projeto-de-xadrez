FROM python:3.13-slim
WORKDIR /app
# Versões fixas: as mesmas validadas pelos testes locais.
RUN pip install --no-cache-dir 'fastapi==0.165.0' 'uvicorn==0.54.0'
COPY mobile_api.py mobile_sync.py installation_presence.py classroom.py preparation_state.py configure_owner.py ./
# Executa sem privilégios de root; /data pertence ao usuário do serviço
# para que o volume nomeado herde a permissão na primeira criação.
RUN useradd --system --uid 10001 --home-dir /app coach \
    && mkdir -p /data && chown coach:coach /data
USER coach
ENV COACH_CLASSROOM_DB=/data/control.sqlite3
EXPOSE 8502
CMD ["python", "-m", "uvicorn", "mobile_api:app", "--host", "0.0.0.0", "--port", "8502"]
