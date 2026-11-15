FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends stockfish \
 && rm -rf /var/lib/apt/lists/*

ENV STOCKFISH_PATH=/usr/games/stockfish \
    CHESS_DIGEST_OUT=/out \
    CHESS_DIGEST_SITE=/site \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY chessdigest ./chessdigest

ENTRYPOINT ["python", "-m", "chessdigest"]
