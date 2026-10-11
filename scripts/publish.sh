#!/usr/bin/env bash
set -euo pipefail
# Ejecutar desde una copia de este proyecto con gh ya autenticado.
cd "$(dirname "$0")/.."
command -v gh >/dev/null || { echo 'Instala GitHub CLI (gh) y ejecuta gh auth login.' >&2; exit 1; }
gh auth status >/dev/null
account_login="$(gh api user --jq .login)"
repo_name="mesachef-studio"
if gh repo view "$account_login/$repo_name" >/dev/null 2>&1; then
 echo "El repositorio $account_login/$repo_name ya existe. No se sobrescribirá; revisa su contenido antes de publicar." >&2
 exit 1
fi
python3 scripts/validate-site.py
if git rev-parse --show-toplevel >/dev/null 2>&1; then
 echo 'Ejecuta este script en una carpeta nueva, fuera de otro repositorio Git.' >&2
 exit 1
fi
git init -b main
git add .
git commit -m 'Publicar MesaChef Studio para GitHub Pages'
gh repo create "$repo_name" --public --source=. --remote=origin --push
gh api --method POST "repos/$account_login/$repo_name/pages" -f build_type=workflow >/dev/null
gh workflow run pages.yml --repo "$account_login/$repo_name"
printf 'Publicación solicitada. Comprueba el resultado en Actions del repositorio %s/%s.\n' "$account_login" "$repo_name"
