#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embute o lsb_dados.json no Almanaque LSB (abre já com os dados, sem importar nada):
  - "Almanaque LSB - com dados.html": para abrir com dois cliques no computador
  - publicado/almanaque.html: versão para publicar como link
  - com --site PASTA: só PASTA/index.html, o site do GitHub Pages exibido no WordPress

  py publicar.py
  py publicar.py --site _site
"""
import argparse, base64, json, os, re

PASTA = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(PASTA, "Almanaque LSB.html")
DADOS = os.path.join(PASTA, "lsb_dados.json")
SAIDA = os.path.join(PASTA, "publicado", "almanaque.html")
LOCAL = os.path.join(PASTA, "Almanaque LSB - com dados.html")
AVISO_TESTE = ("Dados da liga de TESTE da Genius Sports: equipes e jogadores não são da LSB. "
               "Servem só para ver o almanaque funcionando até a Genius liberar o acesso à produção.")


def compactar(d):
    """Nomes de equipe/jogador viram índices de um dicionário (o almanaque desfaz ao abrir);
    minutos com 1 casa decimal."""
    col = {c: i for i, c in enumerate(d["colunas"])}
    d["dic"] = {}
    for nome in ("equipe", "jogador"):
        i, idx, lista = col[nome], {}, []
        for r in d["linhas"]:
            v = r[i]
            if v not in idx:
                idx[v] = len(lista); lista.append(v)
            r[i] = idx[v]
        d["dic"][nome] = lista
    if "min" in col:
        m = col["min"]
        for r in d["linhas"]:
            if isinstance(r[m], float): r[m] = round(r[m], 1)


def main(site=None):
    html = open(FONTE, encoding="utf-8").read()
    d = json.load(open(DADOS, encoding="utf-8"))
    d["embutido"] = True
    if d.get("ambiente", "teste") != "producao":
        d["aviso"] = AVISO_TESTE
    compactar(d)
    js = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    embutir = f'<script id="dados-embutidos" type="application/json">{js}</script>\n<script>'

    # Logomarca oficial e ícone da aba entram embutidos nas duas versões
    for arq in ("logo_lsb.png", "logo_lsb_icone.png"):
        caminho = os.path.join(PASTA, arq)
        if os.path.exists(caminho):
            b64 = base64.b64encode(open(caminho, "rb").read()).decode()
            html = html.replace(f'"{arq}"', f'"data:image/png;base64,{b64}"')
    html = html.replace("<script>", embutir, 1)

    # Site (GitHub Pages, exibido no WordPress): página completa como index.html
    if site:
        os.makedirs(site, exist_ok=True)
        destino = os.path.join(site, "index.html")
        open(destino, "w", encoding="utf-8").write(html)
        print(f"Gerado {destino} ({len(html) // 1024} KB, {len(d['jogos'])} jogos, {len(d['linhas'])} linhas).")
        return

    # Versão para abrir direto no computador (dois cliques), já com os dados
    open(LOCAL, "w", encoding="utf-8").write(html)
    print(f"Gerado {LOCAL}")

    # A página publicada recebe <!doctype>, <head> e <body> prontos; tiramos os nossos
    for padrao in (r"<!DOCTYPE html>\s*", r"<html[^>]*>\s*", r"</?head>\s*", r"</?body>\s*", r"</html>\s*",
                   r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*'):
        html = re.sub(padrao, "", html, flags=re.I)
    html = re.sub(r"<title>.*?</title>", "<title>Almanaque LSB</title>", html, count=1)

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    open(SAIDA, "w", encoding="utf-8").write(html)
    print(f"Gerado {SAIDA} ({len(html) // 1024} KB, {len(d['jogos'])} jogos, {len(d['linhas'])} linhas).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Embute os dados no Almanaque LSB")
    ap.add_argument("--site", help="gera só a pasta do site (index.html), usada pelo GitHub Actions")
    main(ap.parse_args().site)
