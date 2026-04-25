# Agents AI - Project Instructions

Customização do **Odoo 19 Community** via Docker. Leia este arquivo antes de qualquer tarefa.

## Stack

| Componente | Versão |
|---|---|
| Odoo | 19.0 Community |
| PostgreSQL | 16 |
| Python | 3.12 (base da imagem oficial Odoo 19) |

## Estrutura relevante

```
addons/          # Módulos customizados — um diretório por módulo
config/
  odoo.conf      # Produção
  odoo.dev.conf  # Dev (dev_mode ativo, debug log)
scripts/
  scaffold.sh    # Cria esqueleto de novo módulo via odoo scaffold
Dockerfile       # Imagem customizada baseada em odoo:19.0
requirements.txt # Dependências Python extras
```

## Convenções de módulo Odoo

- Nome do diretório: `snake_case`, prefixo `uduu_`
- Versão no manifest: `"19.0.X.Y.Z"` (major.minor.patch)
- Licença: `LGPL-3`
- Todo modelo novo precisa de entrada em `security/ir.model.access.csv`
- Views em `views/`, dados iniciais em `data/`, demos em `demo/`

## Primeiro uso — inicializar banco

O PostgreSQL cria o banco vazio. Na **primeira vez**, inicialize as tabelas do Odoo antes de subir o stack:

```bash
docker compose up -d db
docker compose run --rm odoo odoo -i base -d odoo --without-demo=all --stop-after-init
docker compose up -d
```

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

## Variáveis de ambiente

Copie `.env.example` para `.env` antes de subir. O arquivo `.env` **nunca** é commitado.

## O que não fazer

- Não commitar `.env` ou qualquer arquivo com senhas
- Não editar `odoo.conf` direto no container — edite os arquivos em `config/` e recrie o container
- Não adicionar lógica de negócio no módulo `uduu_base` — ele é apenas a base de dependências comuns
