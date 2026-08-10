

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
     entra na conta — 1021 dos 1037 commits são privados.

O total de commits é somado ano a ano desde a criação da conta, porque
contributionsCollection só aceita janelas de 12 meses. A alternativa seria
search/commits (o que o include_all_commits usa), mas ela não indexa commit
privado direito: devolve 864 onde a soma por janelas devolve 1037.

Atualização semanal pelo workflow .github/workflows/update-top-langs.yml,
que precisa do secret STATS_PAT (PAT clássico com escopo `repo`).
Testes dos geradores: python3 -m unittest discover -s scripts -p 'test_*.py'
-->
