# Uduu ERP

Customização do Odoo 19 Community via Docker.

## Stack

| Componente | Versão |
|---|---|
| Odoo | 19.0 Community |
| PostgreSQL | 16 |
| Python | 3.12 (base da imagem oficial Odoo 19) |

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

## Primeiro uso — inicializar banco

O PostgreSQL cria o banco vazio. Na **primeira vez**, inicialize as tabelas do Odoo antes de subir o stack:

```bash
docker compose up -d db
docker compose run --rm odoo odoo -i base -d uduu --without-demo=all --stop-after-init
docker compose up -d
```

## Criar novo módulo

```bash
./scripts/scaffold.sh meu_modulo
```

## Convenções de módulo Odoo

- Nome do diretório: `snake_case`, prefixo `uduu_`
- Versão no manifest: `"19.0.X.Y.Z"` (major.minor.patch)
- Licença: `LGPL-3`
- Todo modelo novo precisa de entrada em `security/ir.model.access.csv`
- Views em `views/`, dados iniciais em `data/`, demos em `demo/`

## Comandos frequentes

```bash
# Subir ambiente de desenvolvimento
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Subir produção em background
docker compose up -d

# Criar novo módulo (requer container rodando)
./scripts/scaffold.sh nome_modulo

# Rebuild após alterar requirements.txt ou Dockerfile
docker compose build odoo

# Logs do Odoo
docker compose logs -f odoo

# Shell Python dentro do Odoo
docker compose exec odoo odoo shell -d <database>

# Atualizar módulo específico
docker compose exec odoo odoo -u uduu_base -d <database> --stop-after-init
```

## Instalar dependências Python extras

Adicione ao `requirements.txt` e reconstrua:

```bash
docker compose build odoo
```

## O que não fazer

- Não commitar `.env` ou qualquer arquivo com senhas
- Não editar `odoo.conf` direto no container — edite os arquivos em `config/` e recrie o container
- Não adicionar lógica de negócio no módulo `uduu_base` — ele é apenas a base de dependências comuns
