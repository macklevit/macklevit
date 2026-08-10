

<div align="center">
  <img height="180em" alt="Estatísticas do GitHub de macklevit, incluindo contribuições privadas" src="stats.svg" />
  <img height="180em" alt="Linguagens mais usadas por macklevit, incluindo repositórios privados" src="top-langs.svg" />
</div>

<!--
Os dois cards são gerados aqui mesmo, por scripts/generate_stats.py e
scripts/generate_top_langs.py, e commitados como SVG no repositório.

Antes o card de stats vinha de uma instância pública do github-readme-stats
no Vercel. Duas razões para ter saído:
  1. Ela quebrou ("Maximum retries exceeded" / PAT_1 ausente) e a instância
     oficial saiu do ar com DEPLOYMENT_PAUSED — um deploy de terceiro pode
     morrer a qualquer momento e leva o README junto.
  2. count_private=true nunca funcionou: aquela instância autentica com o
     token do dono do deploy, não com o meu, então jamais enxergou os repos
     privados. Gerando aqui com o STATS_PAT, restrictedContributionsCount
     entra na conta (704 dos 717 commits do último ano são privados).

Atualização semanal pelo workflow .github/workflows/update-top-langs.yml,
que precisa do secret STATS_PAT (PAT clássico com escopo `repo`).
Testes dos geradores: python3 -m unittest discover -s scripts -p 'test_*.py'
-->
