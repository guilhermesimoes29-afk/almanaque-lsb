#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coletor da LSB pela API oficial da Genius Sports (Warehouse REST API).
Gera lsb_dados.json para importar no Almanaque LSB.

PREPARAÇÃO (uma vez)
  1) py -m pip install requests
  2) Crie, na mesma pasta deste arquivo, um arquivo de texto chamado
     chave_api.txt contendo SOMENTE a chave que veio no ZIP da Genius.
     (Nunca envie esse arquivo a ninguém nem cole a chave em conversas.)

COMANDOS
  py lsb_api.py testar
      Confere a chave e descobre os caminhos certos da API usando a liga,
      competição e jogo de teste (281 / 9793 / 253740). Salva respostas de
      exemplo na pasta "amostras" (sem a chave).

  py lsb_api.py competicoes
      Lista as competições da liga e cria competicoes_api.csv
      (confira/corrija categoria e temporada).

  py lsb_api.py coletar
      Baixa jogos e estatísticas de todas as competições do CSV e
      cria lsb_dados.json.

OPÇÕES
  --producao        usa o ambiente de produção (quando a Genius liberar)
  --liga 281        ID da liga (no teste é 281; na produção será o da LSB)
  --ids 9793,9800   coleta só estas competições
"""
import argparse, csv, hashlib, json, os, re, sys, time, unicodedata
from datetime import datetime

try:
    import requests
except ImportError:
    print("Instale a dependência:  py -m pip install requests"); sys.exit(1)

BASES = {
    "teste": "https://api.test.wh.geniussports.com/v1/basketball/",
    "producao": "https://api.wh.geniussports.com/v1/basketball/",
}
TESTE = {"liga": 281, "comp": 9793, "jogo": 253740}
PASTA = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(PASTA, "cache_api")
TTL_LISTAS = 6 * 3600          # listas (competições, jogos) valem 6 h
STATUS_FINAL = {"COMPLETE", "FINISHED", "CONFIRMED", "OFFICIAL", "PROTESTED"}

# Caminhos possíveis para cada recurso; o comando "testar" descobre qual funciona
CANDIDATOS = {
    "competicoes": ["leagues/{liga}/competitions"],
    "jogos": ["competitions/{comp}/matches"],
    "jogo": ["matches/{jogo}"],
    "pessoas": ["leagues/{liga}/persons"],
    # os formatos "statistics/..." são os que respondem (os outros dão erro 500)
    "stats_comp": ["statistics/personmatch/competitions/{comp}",
                   "competitions/{comp}/statistics/personmatch"],
    "stats_jogo": ["statistics/personmatch/matches/{jogo}",
                   "matches/{jogo}/statistics/personmatch"],
    "time_jogo": ["statistics/teammatch/matches/{jogo}",
                  "matches/{jogo}/statistics/teammatch"],
}
ROTAS_ARQ = os.path.join(PASTA, "rotas_api.json")
CHAMADAS = 0


# ---------------------------------------------------------------- acesso
def ler_chave():
    k = os.environ.get("GENIUS_API_KEY", "").strip()
    arq = os.path.join(PASTA, "chave_api.txt")
    if not k and os.path.exists(arq):
        k = open(arq, encoding="utf-8").read().strip()
    k = k.replace("﻿", "").strip()   # marca de codificação (BOM) e espaços que editores e o PowerShell acrescentam
    if not k:
        print("Chave não encontrada. Crie o arquivo chave_api.txt com a chave da Genius.")
        sys.exit(1)
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", k):
        print("A chave tem caracteres inesperados (só letras e números são válidos). Confira chave_api.txt "
              "ou o secret GENIUS_API_KEY no GitHub.")
        sys.exit(1)
    return k


class API:
    def __init__(self, base, chave, pausa=0.25):
        self.base, self.pausa = base, pausa
        self.s = requests.Session()
        self.s.headers.update({"x-api-key": chave, "Accept": "application/json"})

    def _cache(self, url):
        h = hashlib.sha1(url.encode()).hexdigest()
        return os.path.join(CACHE, h[:2], h + ".json")

    def get(self, caminho, params=None, ttl=None):
        """ttl=None: cache permanente; ttl=0: sem cache; ttl=N: segundos."""
        global CHAMADAS
        params = dict(params or {})
        q = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        url = self.base + caminho + ("?" + q if q else "")
        arq = self._cache(url)
        if ttl != 0 and os.path.exists(arq):
            if ttl is None or time.time() - os.path.getmtime(arq) < ttl:
                return json.load(open(arq, encoding="utf-8"))
        for t in range(3):
            try:
                r = self.s.get(self.base + caminho, params=params, timeout=40)
                CHAMADAS += 1
                time.sleep(self.pausa)
                if r.status_code in (401, 403):
                    return {"_erro": r.status_code, "_texto": r.text[:300]}
                if r.status_code == 404:
                    return {"_erro": 404}
                if r.status_code == 429 or r.status_code >= 500:
                    time.sleep(3 + 5 * t); continue
                d = r.json()
                os.makedirs(os.path.dirname(arq), exist_ok=True)
                json.dump(d, open(arq, "w", encoding="utf-8"), ensure_ascii=False)
                return d
            except (requests.RequestException, ValueError) as e:
                print(f"    ! falha de conexão ({e.__class__.__name__}), tentando de novo…")
                time.sleep(3 + 5 * t)
        return {"_erro": "conexao"}

    def lista(self, caminho, params=None, ttl=None):
        """Busca todas as páginas (500 por vez)."""
        tudo, offset = [], 0
        while True:
            p = dict(params or {}); p.update(limit=500, offset=offset)
            d = self.get(caminho, p, ttl)
            if "_erro" in d:
                return None if not tudo else tudo
            dados = extrair_lista(d)
            tudo += dados
            if len(dados) < 500:
                return tudo
            offset += 500


def extrair_lista(d):
    x = d.get("response", d).get("data", d) if isinstance(d, dict) else d
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for v in x.values():
            if isinstance(v, list):
                return v
        return [x]
    return []


def extrair_obj(d):
    x = d.get("response", d).get("data", d) if isinstance(d, dict) else d
    return x[0] if isinstance(x, list) and x else x


def rotas():
    return json.load(open(ROTAS_ARQ, encoding="utf-8")) if os.path.exists(ROTAS_ARQ) else {}


def caminho(nome, **kw):
    r = rotas().get(nome) or CANDIDATOS[nome][0]
    return r.format(**kw)


# ---------------------------------------------------------------- utilidades
def pega(o, *chaves, padrao=None):
    for c in chaves:
        if isinstance(o, dict) and o.get(c) not in (None, ""):
            return o[c]
    return padrao


def num(v):
    if v in (None, ""):
        return 0
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    m = re.match(r"^(\d+):(\d{1,2})", s)
    if m:
        return round(int(m.group(1)) + int(m.group(2)) / 60, 2)
    try:
        f = float(s.replace(",", ".")); return int(f) if f.is_integer() else f
    except ValueError:
        return 0


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def inferir_categoria(nome):
    anos = re.findall(r"(20\d\d)", nome or "")
    temp = int(anos[0]) if anos else None
    up = sem_acento(nome or "").upper()
    m = re.search(r"MASTER\s*\+?\s*(\d{2})", up)
    s = re.match(r"^SUB\s*(\d{2})\b", up)
    if m: cat = f"Master {m.group(1)}"
    elif s: cat = f"Sub {s.group(1)} " + ("Feminino" if "FEM" in up else "Masculino")
    elif re.search(r"\bLIGA\s*B\b", up): cat = "Liga B"
    elif "COPA BRASIL" in up: cat = "Copa Brasil Amador"
    elif re.match(r"^(LIVRE\s+)?FEMININO\b", up): cat = "Estadual Amador Feminino"
    elif "ESTADUAL" in up or "AMADOR" in up:
        cat = "Estadual Amador Feminino" if "FEM" in up else "Estadual Amador Masculino"
    else:
        cat = re.sub(r"\s+", " ", re.sub(r"20\d\d(\s*[-/]\s*(20)?\d\d\b)?", " ", nome or "")).strip(" -–") or "Sem categoria"
    return cat, temp


def nome_pessoa(o):
    n = pega(o, "personName", "name", "fullName", "displayName")
    if n: return str(n).strip()
    p = o.get("person") if isinstance(o.get("person"), dict) else {}
    a = pega(o, "firstName", padrao="") or pega(p, "firstName", padrao="")
    b = pega(o, "familyName", "lastName", padrao="") or pega(p, "familyName", "lastName", padrao="")
    return f"{a} {b}".strip() or pega(p, "name", padrao="")


# Campos de estatística da API -> nomes do Almanaque
CAMPOS = {
    "min": ["sMinutes"], "pts": ["sPoints"],
    "fgm": ["sFieldGoalsMade"], "fga": ["sFieldGoalsAttempted"],
    "p2m": ["sTwoPointersMade"], "p2a": ["sTwoPointersAttempted"],
    "p3m": ["sThreePointersMade"], "p3a": ["sThreePointersAttempted"],
    "ftm": ["sFreeThrowsMade"], "fta": ["sFreeThrowsAttempted"],
    "oreb": ["sReboundsOffensive"], "dreb": ["sReboundsDefensive"], "reb": ["sReboundsTotal"],
    "ast": ["sAssists"], "stl": ["sSteals"], "blk": ["sBlocks"],
    "tov": ["sTurnovers"], "pf": ["sFoulsPersonal", "sFoulsTotal"],
    "eff": ["sEfficiency", "sIndex"], "pm": ["sPlusMinusPoints"],
}
ORDEM = ["num", "min", "pts", "fgm", "fga", "p2m", "p2a", "p3m", "p3a", "ftm", "fta",
         "oreb", "dreb", "reb", "ast", "stl", "blk", "tov", "pf", "eff", "pm"]
COLUNAS = ["jogo", "comp", "equipe", "jogadorId", "jogador"] + ORDEM


def periodo_total(r):
    p = pega(r, "periodNumber", "period", padrao=0)
    return str(p) in ("0", "")


# ---------------------------------------------------------------- comandos
def cmd_testar(api, args):
    os.makedirs(os.path.join(PASTA, "amostras"), exist_ok=True)
    kw = {"liga": args.liga or TESTE["liga"], "comp": TESTE["comp"], "jogo": TESTE["jogo"]}
    achadas, ok_geral = {}, True
    print(f"Ambiente: {api.base}\n")
    for nome, cands in CANDIDATOS.items():
        achou = False
        for c in cands:
            cam = c.format(**kw)
            d = api.get(cam, {"limit": 20}, ttl=0)
            erro = d.get("_erro") if isinstance(d, dict) else None
            if erro in (401, 403):
                print(f"  ✗ {nome}: chave recusada ({erro}). Confira o chave_api.txt.")
                print("    Resposta:", d.get("_texto", "")); return
            if not erro:
                n = len(extrair_lista(d))
                json.dump(d, open(os.path.join(PASTA, "amostras", nome + ".json"), "w", encoding="utf-8"),
                          ensure_ascii=False, indent=1)
                print(f"  ✓ {nome:12s} -> {c}  ({n} registros)")
                achadas[nome] = c; achou = True; break
        if not achou:
            ok_geral = ok_geral and nome not in ("competicoes", "jogos")
            print(f"  – {nome:12s} não respondeu nos caminhos conhecidos")
    json.dump(achadas, open(ROTAS_ARQ, "w"), indent=1)
    print(f"\nChamadas usadas: {CHAMADAS}. Respostas de exemplo salvas na pasta 'amostras'.")
    if "stats_comp" not in achadas and "stats_jogo" not in achadas:
        print("\nATENÇÃO: não encontrei as estatísticas de jogadores. Envie os arquivos da pasta"
              " 'amostras' para ajustar o coletor.")
    elif ok_geral:
        print("\nTudo certo! Próximo passo:  py lsb_api.py competicoes" + (" --liga 281" if not args.producao else ""))


def cmd_competicoes(api, args):
    liga = args.liga or TESTE["liga"]
    comps = api.lista(caminho("competicoes", liga=liga), ttl=0)
    if comps is None:
        print("Não consegui listar as competições. Rode primeiro:  py lsb_api.py testar"); sys.exit(1)
    linhas = []
    for c in comps:
        cid = pega(c, "competitionId", "id")
        nome = pega(c, "competitionName", "name", padrao="")
        cat, temp = inferir_categoria(nome)
        ano = pega(c, "year", "season")
        if not temp and ano and re.match(r"^\d{4}", str(ano)):
            temp = int(str(ano)[:4])
        linhas.append({"id": cid, "nome": nome, "categoria": cat, "temporada": temp or ""})
    # Mantém categoria/temporada de quem já está no CSV (podem ter sido corrigidas à mão)
    arq = os.path.join(PASTA, "competicoes_api.csv")
    antigas = {}
    if os.path.exists(arq):
        antigas = {r.get("id"): r for r in csv.DictReader(open(arq, encoding="utf-8-sig"), delimiter=";")}
    novas = 0
    for l in linhas:
        a = antigas.get(str(l["id"]))
        if a: l["categoria"], l["temporada"] = a.get("categoria") or l["categoria"], a.get("temporada") or l["temporada"]
        else: novas += 1
    linhas.sort(key=lambda x: (str(x["temporada"]), x["nome"]))
    with open(arq, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "nome", "categoria", "temporada"], delimiter=";")
        w.writeheader(); w.writerows(linhas)
    print(f"{len(linhas)} competições salvas em competicoes_api.csv, {novas} novas (chamadas usadas: {CHAMADAS}).")
    print("Confira categoria/temporada e depois rode:  py lsb_api.py coletar" + (" --liga 281" if not args.producao else ""))


def ler_csv(filtro):
    arq = os.path.join(PASTA, "competicoes_api.csv")
    if not os.path.exists(arq):
        print("Falta o competicoes_api.csv. Rode antes:  py lsb_api.py competicoes"); sys.exit(1)
    out = []
    for r in csv.DictReader(open(arq, encoding="utf-8-sig"), delimiter=";"):
        try: cid = int(r["id"])
        except (ValueError, KeyError): continue
        if filtro and cid not in filtro: continue
        t = (r.get("temporada") or "").strip()
        out.append({"id": cid, "nome": r.get("nome", ""), "categoria": r.get("categoria") or "Sem categoria",
                    "temporada": int(t) if t.isdigit() else None})
    return out


def info_jogo(m):
    """Retorna (id, data, finalizado, [(teamId, nome, placar, mandante)])."""
    mid = pega(m, "matchId", "id")
    data = str(pega(m, "matchTime", "matchDate", "startTime", padrao=""))[:10]
    status = str(pega(m, "matchStatus", "status", padrao="")).upper()
    comp = m.get("competitors") or m.get("teams") or []
    lados = []
    for c in comp:
        tid = pega(c, "teamId", "competitorId")
        nome = pega(c, "teamName", "competitorName", "name", padrao="") or pega(c.get("team") or {}, "teamName", "name", padrao="")
        placar = num(pega(c, "scoreString", "score", "points", padrao=0))
        casa = str(pega(c, "isHomeCompetitor", "home", padrao="")).lower() in ("1", "true")
        lados.append((tid, nome, placar, casa))
    lados.sort(key=lambda x: not x[3])
    final = status in STATUS_FINAL or (status == "" and sum(l[2] for l in lados) > 0)
    return mid, data, final, lados


def ttl_comp(c, args):
    """Temporadas antigas não mudam: ficam no cache para sempre, salvo com --tudo.
    A atual e a anterior são baixadas de novo quando o cache passa de 6 h."""
    ativa = not c["temporada"] or c["temporada"] >= datetime.now().year - 1
    return TTL_LISTAS if (ativa or args.tudo) else None


def cmd_coletar(api, args):
    filtro = {int(x) for x in args.ids.split(",")} if args.ids else set()
    comps = ler_csv(filtro)
    liga = args.liga or TESTE["liga"]
    nomes = {}
    pessoas = api.lista(caminho("pessoas", liga=liga), ttl=TTL_LISTAS) or []
    for p in pessoas:
        pid = pega(p, "personId", "id")
        if pid: nomes[pid] = nome_pessoa(p)
    jogos, linhas = [], []
    tem_comp = "stats_comp" in rotas()
    for i, c in enumerate(comps, 1):
        ttl = ttl_comp(c, args)
        lista = api.lista(caminho("jogos", comp=c["id"]), ttl=ttl) or []
        info = {}
        for m in lista:
            mid, data, final, lados = info_jogo(m)
            if mid and final and len(lados) >= 2:
                info[mid] = (data, lados)
        print(f"[{i}/{len(comps)}] {c['nome']} ({c['categoria']} {c['temporada'] or ''}): {len(info)} jogos finalizados")
        regs = []
        if tem_comp:
            regs = api.lista(caminho("stats_comp", comp=c["id"]), {"periodNumber": 0}, ttl=ttl) or []
        if not regs:
            for mid in info:
                regs += api.lista(caminho("stats_jogo", jogo=mid), ttl=None) or []
        por_jogo = {}
        for r in regs:
            if periodo_total(r):
                por_jogo.setdefault(pega(r, "matchId"), []).append(r)
        for mid, (data, lados) in info.items():
            nome_time = {l[0]: l[1] for l in lados}
            jogos.append({"id": mid, "comp": c["id"], "data": data, "casa": lados[0][1], "fora": lados[1][1],
                          "pc": lados[0][2], "pf": lados[1][2]})
            for r in por_jogo.get(mid, []):
                pid = pega(r, "personId")
                nome = nome_pessoa(r) or nomes.get(pid) or f"Jogador {pid}"
                tid = pega(r, "teamId")
                v = {k: num(pega(r, *ks, padrao=0)) for k, ks in CAMPOS.items()}
                v["num"] = str(pega(r, "shirtNumber", "playingNumber", padrao=""))
                linhas.append([mid, c["id"], nome_time.get(tid) or pega(r, "teamName", padrao=""), pid, nome] +
                              [v.get(k, 0) for k in ORDEM])
        salvar(args.saida, comps, jogos, linhas, args)
    salvar(args.saida, comps, jogos, linhas, args)
    print(f"\nPronto: {len(jogos)} jogos e {len(linhas)} linhas de jogadores em {args.saida}")
    print(f"Chamadas à API nesta execução: {CHAMADAS} (o restante veio do cache).")


def salvar(destino, comps, jogos, linhas, args):
    json.dump({"formato": "almanaque-lsb", "versao": 1, "fonte": "Genius Sports Warehouse API",
               "ambiente": "producao" if args.producao else "teste", "liga": args.liga or TESTE["liga"],
               "gerado_em": datetime.now().isoformat(timespec="seconds"),
               "competicoes": comps, "jogos": jogos, "colunas": COLUNAS, "linhas": linhas},
              open(os.path.join(PASTA, destino), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def main():
    ap = argparse.ArgumentParser(description="Coletor da LSB pela API da Genius Sports")
    ap.add_argument("comando", choices=["testar", "competicoes", "coletar"])
    ap.add_argument("--producao", action="store_true", help="usar o ambiente de produção")
    ap.add_argument("--liga", type=int, help="ID da liga (teste: 281)")
    ap.add_argument("--ids", help="IDs de competição separados por vírgula")
    ap.add_argument("--saida", default="lsb_dados.json")
    ap.add_argument("--tudo", action="store_true", help="baixar de novo também as temporadas antigas")
    args = ap.parse_args()
    api = API(BASES["producao" if args.producao else "teste"], ler_chave())
    if args.producao and not args.liga and args.comando != "testar":
        ligas = api.lista("leagues", ttl=0)
        if ligas is None:
            print("A chave ainda não tem acesso à produção (a Genius precisa liberar)."); return
        print("Informe o ID da liga com --liga. Ligas disponíveis para esta chave:")
        for l in ligas:
            print(f"  {pega(l, 'leagueId', 'id')}  {pega(l, 'leagueName', 'name', padrao='')}")
        return
    {"testar": cmd_testar, "competicoes": cmd_competicoes, "coletar": cmd_coletar}[args.comando](api, args)


if __name__ == "__main__":
    main()
