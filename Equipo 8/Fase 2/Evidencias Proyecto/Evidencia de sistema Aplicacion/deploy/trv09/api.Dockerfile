FROM corestream-trv09-api-base:local
ENV PYTHONPATH=/app
COPY --chown=app:app entrypoint.py api.py seed.py verify.py /opt/trv09/
ENTRYPOINT ["python", "/opt/trv09/entrypoint.py"]
CMD ["uvicorn", "api:app", "--app-dir", "/opt/trv09", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*", "--timeout-graceful-shutdown", "8", "--no-access-log"]
HEALTHCHECK --interval=10s --timeout=4s --start-period=60s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1
