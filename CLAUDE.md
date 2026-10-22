# Almanaque LSB

Almanaque de estatísticas históricas da Liga Super Basketball (LSB, Rio de Janeiro): rankings de jogadores
(2007–2026), recordes por partida, placares, equipes e comparação, filtrados por categoria (Liga B, Estadual
Amador Masculino/Feminino, Master 35, Master 40…) e temporada. Responda ao usuário em português.

## Arquivos

- `lsb_api.py` – coletor da Genius Sports Warehouse REST API. Comandos: `testar`, `competicoes`, `coletar`
  (opções `--producao`, `--liga ID`, `--ids 1,2`). Gera `lsb_dados.json`.
- `chave_api.txt` – chave da API. **Segredo: nunca exibir, copiar para outro lugar nem publicar.**
- `competicoes_api.csv` – competições com categoria/temporada inferidas (o usuário pode corrigir à mão).
- `Almanaque LSB.html` – o programa (HTML + JS puro, sem dependências). Importa `lsb_dados.json`,
  guarda no IndexedDB do navegador. Se a página tiver `<script id="dados-embutidos">`, abre já com esses dados.
- `publicar.py` – embute `lsb_dados.json` no almanaque e gera `Almanaque LSB - com dados.html` (abrir no
  computador) e `publicado/almanaque.html` (para publicar como link). Rodar após cada coleta.
- `cache_api/`, `amostras/`, `rotas_api.json` – cache das respostas, exemplos da API e rotas descobertas.

## Ambiente

- Python 3.12 instalado em `%LOCALAPPDATA%\Programs\Python\Python312\python.exe` (em terminal novo, `py` funciona).
  Ao rodar pelo PowerShell, defina `$env:PYTHONIOENCODING='utf-8'` (o coletor imprime ✓/✗).
- API de teste: `https://api.test.wh.geniussports.com/v1/basketball/`, cabeçalho `x-api-key`.
  Liga de teste 281, competição 9793, jogo 253740. Dados fictícios e incompletos (65 de 85 jogos sem estatísticas).
- Rotas de estatística que funcionam: `statistics/personmatch/competitions/{id}` e
  `statistics/personmatch/matches/{id}` (o formato `competitions/{id}/statistics/...` dá erro 500).
  `periodNumber=0` traz só o total do jogo.
- Produção (`api.wh.geniussports.com`): liberada em 22/10/2026. `chave_api.txt` = chave de produção
  ("BR-Liga Super Basketball READ API key"); `chave_api_teste.txt` = chave de teste.
  **Liga da LSB = 256.** 184 competições de 2007 a 2026. Comando: `py lsb_api.py coletar --producao --liga 256`.
- Dados de teste guardados em `lsb_dados_teste.json` / `competicoes_api_teste.csv`.

## Interface (v2, 22/10/2026)

- Identidade LSB: preto #201E1E e laranja #F06526 (cores da logomarca oficial), títulos em Big Shoulders Display,
  texto em Archivo. Logomarca oficial (escudo "LSB" com bola) enviada pelo usuário, que pediu para usá-la em todas
  as áreas de logo, inclusive no link: `logo_lsb_original.png` (2156×3363), `logo_lsb.png` (topo, 128×200) e
  `logo_lsb_icone.png` (ícone da aba). `publicar.py` embute as duas em data URI nas duas versões.
- Abas: Resumo (padrão), Rankings, Recordes por jogo, Placares, Equipes, Jogador, Comparar, Competições.
- Filtro por grupos (Adulto, Master, Base, Copas e outras — função `grupo()`), depois categorias do grupo.
- Celular: colunas com classe `opt` somem abaixo de 640px.
- Versão anterior guardada em `versoes/`. Dados embutidos são compactados (`dic` de nomes) por `publicar.py`.

## Link publicado

https://claude.ai/artifact/AjvmsdBQiYpGUZnGDgvnQx (compartilhado como "qualquer pessoa com o link"; quem está
com a página aberta recebe as atualizações na hora). Versões com dados embutidos não mostram os botões de importar;
correções na aba Competições valem só até recarregar (a correção definitiva é no `competicoes_api.csv`). Para atualizar: `py publicar.py` e
publicar de novo `publicado/almanaque.html` passando esse URL.

## Situação dos dados (coleta de 22/10/2026)

5.895 jogos, 101.329 linhas de jogadores, 184 competições (2007–2026); link publicado com ~8,9 MB (limite 16 MB).
- 4.819 jogos: soma dos pontos dos jogadores = placar.
- 681 sem estatísticas de jogadores (206 são W.O.; o resto concentra-se em 2009–2016, sobretudo 2016).
- 395 diferentes: em 316 a soma é menor que o placar (estatística incompleta na própria Genius); 62 são W.O. 20×0
  com só a equipe presente registrada. Não é defeito do coletor.

## Atualização semanal (desde 22/10/2026)

- Tarefa do Agendador do Windows "Almanaque LSB - atualizacao semanal": toda terça às 8h (roda depois, se o PC
  estiver desligado nesse horário; precisa do usuário logado e de internet). Executa `atualizar.bat`:
  `competicoes` → `coletar` → `publicar.py`, com registro em `atualizacao.log` (termina com OK ou FALHOU).
- `coletar` só baixa de novo as temporadas do ano atual e do anterior (cache de 6 h); as antigas vêm do cache.
  `--tudo` força tudo. `competicoes` preserva categoria/temporada já existentes no CSV e só acrescenta as novas
  (para recalcular as categorias com `inferir_categoria`, apague o CSV antes).
- O link NÃO se atualiza sozinho: quando o usuário pedir "atualiza o almanaque", confira o fim do
  `atualizacao.log` (ou rode `atualizar.bat`), rode a conferência de placares e republique `publicado/almanaque.html`.

## Página no WordPress (via GitHub Pages)

- O link do claude.ai não pode ser embutido em outros sites (CSP `frame-ancestors 'self'`). Solução escolhida pelo
  usuário: repositório público `almanaque-lsb` no GitHub + GitHub Pages; o WordPress (outro site, o usuário é
  administrador) mostra o almanaque num iframe.
- Mudanças de interface/layout: o usuário pede aqui; editar `Almanaque LSB.html`, prévia, commit e `git push`.
  O push em `Almanaque LSB.html`, `publicar.py`, `lsb_api.py`, logos ou no workflow dispara a publicação na hora.
  Nunca dar push enquanto uma execução do Actions estiver rodando (o commit dela no fim entraria em conflito):
  confira com `gh run list --limit 1` e faça `git pull --rebase` antes do push.
- `.github/workflows/atualizar.yml`: toda terça 11h UTC (8h Brasília) + "Run workflow" manual + push (acima). Coleta com o secret
  `GENIUS_API_KEY`, guarda `cache_api` no cache do Actions, `publicar.py --site _site`, faz commit de
  `competicoes_api.csv` e `ultima-atualizacao.txt` (mantém o agendamento ativo) e publica no Pages.
- `wordpress/codigo-para-wordpress.html`: iframe + script que ajusta a altura (mensagem `almanaqueLSB` com `altura`
  e `topo`, enviada pelo almanaque quando está dentro de um iframe). `?tema=claro|escuro` fixa o tema.
- `.gitignore` deixa de fora chave, cache, dados gerados e arquivos locais.
- Repositório: https://github.com/guilhermesimoes29-afk/almanaque-lsb (público, criado em 22/10/2026 com
  autorização explícita do usuário). Site: https://guilhermesimoes29-afk.github.io/almanaque-lsb/
  Secret `GENIUS_API_KEY` cadastrado; Pages com build_type=workflow. Git e GitHub CLI (`gh`, logado como
  guilhermesimoes29-afk) instalados. A pasta do projeto é o próprio repositório: depois de mudar algo,
  `git pull` (a rotina faz commits semanais), commit e `git push`.

## Histórico do GitHub Actions

- 22/10/2026: 1ª execução cancelada após 2 h — o secret tinha BOM (cadastrado via pipe do PowerShell 5.1) e toda
  requisição dava UnicodeEncodeError. Corrigido: secret recadastrado com `gh secret set --body`, `ler_chave()`
  remove BOM e recusa chave com caracteres estranhos, `competicoes` sai com erro se a API não responde.
  Nunca cadastrar secret com pipe no PowerShell.
- 22/10/2026: 2ª execução OK em 19,5 min (1.003 chamadas, 5.895 jogos); site no ar (9 MB, ~3,6 s).

## Próximos passos

1. Atualizar: `py lsb_api.py competicoes --producao --liga 256`, revisar o CSV, `coletar --producao --liga 256`,
   `py publicar.py`, republicar `publicado/almanaque.html` no mesmo link.
2. Conferir os dados reais: soma dos pontos dos jogadores = placar de cada jogo; jogos sem estatísticas.
3. Temporadas antigas (desde 2007) podem não estar na API; verificar cobertura por categoria.
