# PriceWatch
```bash
python -m venv .venv 

.venv/Scripts/activate

pip install -r requirements.txt

python -m uvicorn app.main:app --reload
```
Откройте: http://127.0.0.1:8000


Или сделайте через docker.desktop
```bash
#Запустите Docker Desktop

docker build -t pricewatch .

docker run -d -p 8000:8000 --name pricewatch-app pricewatch
```

Откройте: http://localhost:8000