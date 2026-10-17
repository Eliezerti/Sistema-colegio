"""Publish actual CI results as annotations; never requires artifact download access."""
import argparse,csv,json,re
from pathlib import Path

ANSI=re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')

def command(level,title,message):
    escaped=str(message).replace('%','%25').replace('\r','%0D').replace('\n','%0A')
    return f'::{level} title={title}::{escaped}'

def unit_summary(text):
    text=ANSI.sub('',text)
    found=re.search(r'(?m)^Ran (\d+) tests? in ([0-9.]+)s\s*$',text)
    outcome=re.search(r'(?m)^(OK(?: \([^\n]*\))?|FAILED[^\n]*)$',text)
    return dict(tests=int(found[1]) if found else None,seconds=found[2] if found else None,outcome=outcome[1] if outcome else 'No se encontró el resumen; revisar el registro')

def failure_sections(text,unit=False):
    text=ANSI.sub('',text)
    if unit:
        matches=re.findall(r'(?ms)^(?:ERROR|FAIL): .*?(?=^={20,}|^-{20,}\r?\nRan|\Z)',text)
        if matches:return matches
    # Browser stack traces precede the disposable server's request log.
    return [re.split(r'(?:Colegio|MODO PRUEBA) abierto en http://127\.0\.0\.1:',text,maxsplit=1)[0]]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=int,nargs=4);parser.add_argument('--performance');args=parser.parse_args()
    if args.results is not None:
        names=('unittest','browser','demo','roster');content={name:Path('noche-'+name+'.log').read_text(encoding='utf-8-sig',errors='replace') for name in names}
        actual=dict(exits=dict(zip(names,args.results)),unit=unit_summary(content['unittest']))
        print(command('notice','Resultados reales de las cuatro suites',json.dumps(actual,ensure_ascii=False)))
        for name,code in zip(names,args.results):
            if code:
                for number,section in enumerate(failure_sections(content[name],name=='unittest'),1):
                    chunks=[section[n:n+6000] for n in range(0,len(section),6000)] or ['No hay texto de error; revisar el artefacto.']
                    for part,chunk in enumerate(chunks,1):print(command('error',f'{name} fallo {number}, parte {part} de {len(chunks)}',chunk))
    if args.performance:
        with open(args.performance,encoding='utf-8-sig',newline='') as file:
            for row in csv.DictReader(file):print(command('notice','Medición HTTP real',json.dumps(row,ensure_ascii=False)))
    if args.results is None and not args.performance:parser.error('Indica resultados o archivo de rendimiento.')

if __name__=='__main__':main()
