#!/usr/bin/env python3
"""Confere labels definidos x referenciados nos capitulos da tese."""
import re, glob, sys

definidos = {}
for f in sorted(glob.glob('cap*.tex') + glob.glob('apendice*.tex') + glob.glob('tab_*.tex')):
    txt = open(f, encoding='utf-8').read()
    for m in re.finditer(r'\\label\{([^}]*)\}', txt):
        definidos[m.group(1)] = f
    # labels declarados na chave label= de \begin{lstlisting}[...]
    for m in re.finditer(r'\\begin\{lstlisting\}\[[^\]]*?label=\{?([^,\]}]+)\}?', txt, re.S):
        definidos[m.group(1).strip()] = f
    # labels implicitos dos comandos customizados
    for cmd, pref in (('figura', 'fig'), ('imagem', 'fig'),
                      ('tabela', 'tab'), ('qquadro', 'qua')):
        pass

# labels gerados pelos comandos customizados (5o arg de \figura, 4o de tabela/qquadro/imagem)
for f in sorted(glob.glob('cap*.tex') + glob.glob('apendice*.tex') + glob.glob('tab_*.tex')):
    txt = open(f, encoding='utf-8').read()
    for cmd, pref, pos in (('tabela', 'tab', 4), ('qquadro', 'qua', 4),
                           ('imagem', 'fig', 4), ('figura', 'fig', 5)):
        for m in re.finditer(r'\\' + cmd + r'\s*\n?', txt):
            i = m.end(); args = []
            while len(args) < pos and i < len(txt):
                while i < len(txt) and txt[i] in ' \n\t%':
                    if txt[i] == '%':
                        i = txt.index('\n', i)
                    i += 1
                if i >= len(txt) or txt[i] != '{': break
                d, j = 1, i + 1
                while j < len(txt) and d:
                    if txt[j] == '{': d += 1
                    elif txt[j] == '}': d -= 1
                    j += 1
                args.append(txt[i+1:j-1]); i = j
            if len(args) == pos:
                definidos[f'{pref}:{args[pos-1].strip()}'] = f

referenciados = {}
for f in sorted(glob.glob('cap*.tex') + glob.glob('apendice*.tex') + glob.glob('tab_*.tex')):
    txt = open(f, encoding='utf-8').read()
    for m in re.finditer(r'\\(?:autoref|ref)\{([^}]*)\}', txt):
        referenciados.setdefault(m.group(1), []).append(f)

faltando = {k: v for k, v in referenciados.items() if k not in definidos}
orfaos = {k: v for k, v in definidos.items()
          if k not in referenciados and not k.startswith(('cap:', 'sec:', 'ssec:'))}

print(f"labels definidos ......... {len(definidos)}")
print(f"labels referenciados ..... {len(referenciados)}")
if faltando:
    print(f"\nREFERENCIAS SEM LABEL ({len(faltando)}):")
    for k, v in sorted(faltando.items()):
        print(f"  {k:32s} citado em {', '.join(sorted(set(v)))}")
else:
    print("\nnenhuma referencia pendente")
if orfaos:
    print(f"\nflutuantes nao referenciados ({len(orfaos)}):")
    for k, v in sorted(orfaos.items()):
        print(f"  {k:32s} ({v})")
sys.exit(1 if faltando else 0)
