import re, difflib, pathlib, sys
old=open(sys.argv[1]).read().splitlines(); new=open("output/pipeline_console.txt").read().splitlines()
num=re.compile(r"(?<![\w.])\d+\.\d+|(?<![\w.])\d{3,}(?![\w.])")
oldn=set(); newn=set()
for l in old: oldn|=set(num.findall(l))
for l in new: newn|=set(num.findall(l))
gone=oldn-newn
def forms(x):
    f=set()
    if "." in x:
        a,b=x.split(".")
        if len(a)+len(b)<3: return f
        for k in range(1,len(b)+1): 
            v=f"{float(x):.{k}f}".replace(".",",")
            f.add(v)
        if len(a)>=3: f.add(str(round(float(x))))
    else: f.add(x)
    return {v for v in f if len(re.sub(r"\D","",v))>=3}
tex=[p for p in pathlib.Path("tese").glob("*.tex")]
txt={p:p.read_text() for p in tex}
hits={}
for x in sorted(gone):
    for v in forms(x):
        if v in {str(n) for n in newn} or v.replace(",",".") in newn: continue
        pat=re.compile(r"(?<![\d,.{])"+re.escape(v).replace(",",r"(?:,|\{,\})")+r"(?![\d}]|\{,\}\d|,\d)")
        for p,s in txt.items():
            for m in pat.finditer(s):
                ln=s.count("\n",0,m.start())+1
                hits.setdefault((p.name,ln),set()).add(f"{v}(<{x})")
for (f,ln),v in sorted(hits.items()):
    line=txt[pathlib.Path("tese")/f].splitlines()[ln-1].strip()
    print(f"{f}:{ln}: {sorted(v)} | {line[:110]}")
