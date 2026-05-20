# Scraper Mercado Livre — API

API REST para scraping de produtos do Mercado Livre com autenticação por API Key, cache no PostgreSQL e logs de uso.

---

## Estrutura

```
scraper-api/
├── app/
│   ├── main.py           # Entrypoint FastAPI
│   ├── auth.py           # Validação de API Keys
│   ├── cache.py          # Cache de buscas no PostgreSQL
│   ├── config.py         # Configurações via .env
│   ├── database.py       # Conexão async PostgreSQL
│   ├── models.py         # Tabelas do banco
│   ├── scraper.py        # Chamada ao scraper via subprocess
│   └── routers/
│       ├── buscar.py     # GET /buscar
│       └── admin.py      # GET/POST/PATCH/DELETE /admin/*
├── scraper_standalone.py # Scraper Playwright (chamado como subprocess)
├── requirements.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

---

## Setup local (Windows/Linux sem Docker)

### 1. Instalar dependências
```bash
pip install -r requirements.txt
pip install pydantic-settings
playwright install chromium
```

### 2. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Edite o .env com suas configurações
```

### 3. Subir o PostgreSQL (via Docker)
```bash
docker-compose up -d db
```

### 4. Rodar a API
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Setup na VPS (produção)

### 1. Clonar o projeto e configurar .env
```bash
git clone <seu-repo>
cd scraper-api
cp .env.example .env
nano .env   # preencha DATABASE_URL, SECRET_KEY, ADMIN_KEY
```

### 2. Subir tudo com Docker Compose
```bash
docker-compose up -d --build
```

### 3. Verificar se está rodando
```bash
curl http://localhost:8000/health
```

---

## Como usar

### Criar um cliente (admin)
```bash
curl -X POST http://localhost:8000/admin/clientes \
  -H "X-Admin-Key: sua-chave-admin" \
  -H "Content-Type: application/json" \
  -d '{"name": "Cliente Teste", "rate_limit": 10}'
```
Resposta:
```json
{
  "message": "Cliente criado com sucesso.",
  "id": 1,
  "name": "Cliente Teste1",
  "api_key": "a1b2c3d4...",
  "rate_limit": 10
}
```

### Buscar produtos
```bash
curl "http://localhost:8000/buscar?termo=whey+protein&paginas=2" \
  -H "X-API-Key: a1b2c3d4..."
```

### Ver logs
```bash
curl http://localhost:8000/admin/logs \
  -H "X-Admin-Key: sua-chave-admin"
```

### Ver estatísticas
```bash
curl http://localhost:8000/admin/stats \
  -H "X-Admin-Key: sua-chave-admin"
```

---

## Endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/` | — | Status da API |
| GET | `/health` | — | Health check |
| GET | `/buscar` | X-API-Key | Buscar produtos |
| GET | `/admin/clientes` | X-Admin-Key | Listar clientes |
| POST | `/admin/clientes` | X-Admin-Key | Criar cliente |
| PATCH | `/admin/clientes/{id}` | X-Admin-Key | Atualizar cliente |
| DELETE | `/admin/clientes/{id}` | X-Admin-Key | Remover cliente |
| GET | `/admin/logs` | X-Admin-Key | Ver logs |
| GET | `/admin/stats` | X-Admin-Key | Estatísticas |
| GET | `/docs` | — | Swagger UI |
