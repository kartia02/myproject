FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8000
# 배포 플랫폼이 PORT를 주입한다. 프록시 뒤에서 클라이언트 IP를 복원해야 Rate Limit이 IP별로 동작한다.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
