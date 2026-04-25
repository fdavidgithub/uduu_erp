# Uduu ERP

Customização do Odoo 19 Community via Docker.

## Estrutura

```
.
├── addons/               # Módulos customizados
│   └── uduu_base/        # Módulo base de exemplo
├── config/
│   ├── odoo.conf         # Configuração produção
│   └── odoo.dev.conf     # Configuração desenvolvimento (dev_mode)
├── scripts/
│   └── scaffold.sh       # Cria esqueleto de novo módulo
├── docker-compose.yml
├── docker-compose.dev.yml
├── Dockerfile
└── requirements.txt      # Dependências Python extras
```

## Início rápido

```bash
cp .env.example .env
# Edite .env e defina POSTGRES_PASSWORD

# Produção
docker compose up -d

# Desenvolvimento (hot-reload, debug log)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Acesse: http://localhost:8069

## Criar novo módulo

```bash
./scripts/scaffold.sh meu_modulo
```

## Instalar dependências Python extras

Adicione ao `requirements.txt` e reconstrua:

```bash
docker compose build odoo
```
