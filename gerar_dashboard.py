#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PipeLovers - Gerador de Dashboard de Engajamento
=================================================
Arquivos necessários (mesma pasta):
  consumo.csv      -> relatório de consumo da plataforma
  clientes.csv     -> base de clientes (Status + CSM)
  usuarios.csv     -> base completa de usuários
  nao_iniciou.csv  -> relatório de quem nunca assistiu
"""

import csv, json, os, sys, re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

CONSUMO_CSV    = "consumo.csv"
CLIENTES_CSV   = "clientes.csv"
USUARIOS_CSV   = "usuarios.csv"
NAO_INICIOU_CSV = "nao_iniciou.csv"
OUTPUT_HTML    = "index.html"

ALIASES = {
    'Intelbras 2':'Intelbras','INTELBRAS 2':'Intelbras',
    'Baldussi':'Baldussi Telecon',
    'Teruya Ferramentas':'Teruya','TERUYA FERRAMENTAS':'Teruya',
    'AYKO':'Ayko Tech','SINCH':'Sinch','Centric':'Centric Solutions',
    'TR EPI':'TR EPIS','AMPCO METAL':'AMPCO','Clínica Experts':'Clinica Experts',
    'TotalPass SMB':'TotalPass','TOTALPASS SMB':'TotalPass',
    'TotalPass SMB 1':'TotalPass','TotalPass SMB 2':'TotalPass',
    'TotalPass Enterprise':'TotalPass','TotalPass TP WEB':'TotalPass','TP WEB':'TotalPass',
    'Okser Software':'Okser',
    'Conexão Sistemas':'Conexão Sistemas de Próteses',
    'Conexão Sistemas de Protese':'Conexão Sistemas de Próteses',
    'MAILBIZ':'Mailbiz','MAILBIZ TECNOLOGIA':'Mailbiz',
    'Triibo':'Synoro','TRIIBO':'Synoro','Triibo e Axyma':'Synoro','Axyma':'Synoro',
    'Valeti':'Valeti App',
    'WebMais Sistemas':'WebMais','WEBMAIS':'WebMais','Webmais':'WebMais',
    'Sidrasul Sistemas Hidráulicos Ltda':'Sidrasul',
    'Gradisa Soluções em Ferro':'Gradisa','HSM DO BRASIL S.A.':'HSM',
    'TECH IND':'Tech-Ind','RDamasco Soluções Industriaisi':'R&Damasco',
    'Urânia Projetores':'Urânia Planetário','Strada Mob LTDA':'Strada Mobi',
    'E AI Educa':'E aí','Kalashi':'Kalashi Marcas e Patentes',
    'Omni Acessoria':'Omni Assessoria','MAGIS5':'Magis5','Ceramica City':'Cerâmica City',
    'Vinho Tinta':'VinhoTinta',
    "Facilit'Air: Soluções por Drones":"Facilit'air",'Gen':'GNM Engenharia',
    'Hytec Automação Industrial':'Hytec','Innovo':'Innovoc',
    'INNTECNET SOFTWARE':'Inntecnet','INOVAMOTION':'Inovamotion Industria e tecnologia Ltda',
    'LID TRAVEL':'LID Travel Viagens e Turismo',
    'Lolis Transportes Internacionais':'Lolis Transportes',
    'Merc':'Agrocomm comercio','Couto Tech':'Couto Tech Soluções Energéticas',
    'UP':'Nelson Wilians Group','Oximed Gases':'Oximed',
    'Seaps Consultoria':'SEAPS','SQUAD':'Squad Terceirização',
    'VoltBras':'Volt','SolarVolt':'Volt',
    '2P':'2P Group','ALS BRASIL':'ALS','Alpha':'Alpha cm',
    'Alta Geotecnia Ambiental SA':'Alta Geotecnia','Bistex Alimentos':'Bistex',
    'Cubos':'Cubos Tecnologia','DV2 TOTVS':'DV2','Engeform Energia':'Engeform',
    'Enkel Informática':'Enkel','FORSA':'Forsa Brasil','GOO':'Goo! Life',
    'GZV IT SOLUTIONS':'GZV','Golden Cloud Technology':'Golden Cloud',
    'Goose Educação':'Goose','Great people esg':'Great People',
    'Grupo Nobre Embalagem':'Nobre Embalagem','Hubee design':'Hubee',
    'Icom':'Icom Marketing','JCR':'JCR Tecnologia',
    'Localize Digital':'Localize','Localize Digital LTDA':'Localize',
    'Logithink Tecnologia':'Logithink','Oxy Camaras Hiperbáricas':'Oxy Camara',
    'Popedi Brasil':'Popedi','RunRun':'Runrun.it','STOA':'Grupo STOA',
    'Samba':'Samba Tech','TARGIT':'Targit Brasil','Wiki Consultoria':'Wiki',
}

STATUS_PRIORITY = {'Ativo':0,'Try and Buy':1,'Inativo':2,'Churn':3,'':4}
TODAY = datetime.now(timezone.utc)
THIS_MONTH = TODAY.strftime('%Y-%m')
_y,_m = TODAY.year, TODAY.month
CURRENT_MONTH = f"{_y:04d}-{_m:02d}"
_m2=_m-1; _y2=_y if _m2>0 else _y-1; _m2=_m2 if _m2>0 else 12
PREV_MONTH = f"{_y2:04d}-{_m2:02d}"
THREE_MONTHS_AGO = TODAY - timedelta(days=90)

def encontrar_csv(nome, prefixos):
    pasta = os.path.dirname(os.path.abspath(__file__))
    c = os.path.join(pasta, nome)
    if os.path.exists(c): return c
    for f in os.listdir(pasta):
        if f.lower().endswith('.csv') and any(f.lower().startswith(p.lower()) for p in prefixos):
            print(f"  Auto-detectado: {f}")
            return os.path.join(pasta, f)
    return None

def get_grupo(product_name):
    p = (product_name or '').lower()
    if 'executiv' in p: return 'Executivos'
    if 'pré-vend' in p or 'pre-vend' in p or 'sdr' in p: return 'Pré-Vendas'
    if 'fullpass' in p or 'full pass' in p: return 'FullPass'
    if 'gestão' in p or 'gestao' in p: return 'Gestão'
    if 'canais' in p or 'parcerias' in p: return 'Canais & Parcerias'
    if 'certific' in p: return 'Certificação'
    if 'class' in p: return 'PipeLovers Class'
    if 'plus' in p: return 'PipeLovers PLUS+'
    if 'programa' in p: return 'Prog. Gestão'
    return 'Outros'

def get_flag(days, monthly):
    if CURRENT_MONTH in monthly and PREV_MONTH in monthly: return 'offensive'
    if days < 30: return 'green'
    if days < 60: return 'yellow'
    if days < 90: return 'red'
    return 'black'

def processar():
    print("\nPipeLovers - Dashboard de Engajamento")
    print("=" * 45)

    p_consumo  = encontrar_csv(CONSUMO_CSV,    ['consumo','pipelovers_b2b','consumption'])
    p_clientes = encontrar_csv(CLIENTES_CSV,   ['clientes','base_de_clientes','planilha'])
    p_usuarios = encontrar_csv(USUARIOS_CSV,   ['usuarios','membros'])
    p_nao      = encontrar_csv(NAO_INICIOU_CSV,['nao_iniciou','report_nao','nunca'])

    for nome, caminho in [('consumo',p_consumo),('clientes',p_clientes)]:
        if not caminho:
            print(f"\nERRO: '{nome}.csv' nao encontrado."); sys.exit(1)

    # ── Clientes ──
    clientes_raw = {}
    with open(p_clientes, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            emp = row.get('Empresa','').strip()
            if not emp: continue
            st  = (row.get('Status') or row.get(' Status') or '').strip()
            csm = row.get('CSM','').strip()
            if emp not in clientes_raw or STATUS_PRIORITY.get(st,4) < STATUS_PRIORITY.get(clientes_raw[emp]['status'],4):
                clientes_raw[emp] = {'status':st,'csm':csm}

    lower_to_nome = {e.lower():e for e in clientes_raw}
    ativas_raw    = {e for e,d in clientes_raw.items() if d['status']=='Ativo'}
    ativas_lower  = {e.lower():e for e in ativas_raw}

    def resolve(company):
        if company in clientes_raw: return company, clientes_raw[company]
        canon = ALIASES.get(company)
        if canon and canon in clientes_raw: return canon, clientes_raw[canon]
        m = lower_to_nome.get(company.lower())
        if m: return m, clientes_raw[m]
        return company, {}

    def is_ativa(company):
        if company in ativas_raw: return True
        canon = ALIASES.get(company)
        if canon and canon in ativas_raw: return True
        return company.lower() in ativas_lower

    # ── Consumo ──
    print("Carregando consumo...")
    user_map = {}
    mes_total  = defaultdict(set)
    mes_grupo_total = defaultdict(lambda: defaultdict(set))
    empresa_aulas_recentes = defaultdict(int)

    with open(p_consumo, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            email   = row.get('user_email','').strip().lower()
            company = row.get('company','').strip()
            if not email: continue
            date_s  = row.get('first_consumed_at','')
            creat_s = row.get('user_created_at','')
            name    = row.get('user_full_name','').strip()
            grupo   = get_grupo(row.get('product_name',''))
            try: dt = datetime.fromisoformat(date_s.replace('Z','+00:00'))
            except: dt = None
            try: cr = datetime.fromisoformat(creat_s.replace('Z','+00:00'))
            except: cr = None

            if email not in user_map:
                user_map[email] = {'email':email,'name':name,'company':company,
                                   'last_consumed':None,'total_consumed':0,
                                   'created_at':cr,'monthly':defaultdict(int)}
            u = user_map[email]
            if dt:
                if not u['last_consumed'] or dt > u['last_consumed']: u['last_consumed'] = dt
                mes = dt.strftime('%Y-%m')
                u['monthly'][mes] += 1
                mes_total[mes].add(email)
                mes_grupo_total[mes][grupo].add(email)
                if dt >= THREE_MONTHS_AGO:
                    empresa_aulas_recentes[company] += 1
            u['total_consumed'] += 1
            if cr and (not u['created_at'] or cr < u['created_at']): u['created_at'] = cr

    print(f"  {len(user_map):,} usuários únicos")

    # ── Usuários ──
    all_users_base = {}
    if p_usuarios:
        with open(p_usuarios, encoding='utf-8') as f:
            for row in csv.DictReader(f):
                em = (row.get('Url do E-mail do Membro') or row.get('email') or '').strip().lower()
                if '@' not in em: continue
                name = (row.get('Nome Completo') or f"{row.get('Nome','')} {row.get('Sobrenome','')}".strip())
                company = (row.get('Nome da Empresa') or row.get('company') or '').strip()
                if em not in all_users_base:
                    all_users_base[em] = {'name':name.strip(),'company':company}

    # ── Cruzar ──
    users_list   = []
    orphan_users = []
    not_found_set = defaultdict(lambda: {'total':0,'teve_consumo':False,'co_status':''})
    mes_ativos   = defaultdict(set)
    mes_grupo_ativos = defaultdict(lambda: defaultdict(set))

    for email, uinfo in all_users_base.items():
        company = uinfo['company']
        if not company: continue
        canon, info = resolve(company)
        co_status = info.get('status','')
        csm       = info.get('csm','')
        cons      = user_map.get(email, {})
        last_dt   = cons.get('last_consumed')
        days      = int((TODAY - last_dt).days) if last_dt else 9999
        monthly   = dict(cons.get('monthly', {}))
        flag      = get_flag(days, monthly)
        created_at = cons.get('created_at')

        entry = {
            'email': email, 'name': uinfo['name'] or cons.get('name',''),
            'company': canon, 'co_status': co_status, 'csm': csm,
            'total_consumed': cons.get('total_consumed',0),
            'last_consumed': last_dt.strftime('%Y-%m-%d') if last_dt else '',
            'days_inactive': days, 'flag': flag,
            'active_this_month': THIS_MONTH in monthly,
            'created_at': created_at.strftime('%Y-%m-%d') if created_at else '',
            'monthly': monthly,
            'never_consumed': cons.get('total_consumed',0) == 0,
        }

        if is_ativa(company):
            users_list.append(entry)
            # Para gráficos: registrar meses de atividade
            for mes in monthly:
                mes_ativos[mes].add(email)
                # Recuperar grupo do consumo
            if email in user_map:
                for mes, cnt in user_map[email]['monthly'].items():
                    mes_ativos[mes].add(email)
        else:
            if last_dt and last_dt >= THREE_MONTHS_AGO:
                orphan_users.append({**entry,'company':company,'co_status':co_status})
            not_found_set[canon]['total'] += 1
            not_found_set[canon]['co_status'] = co_status
            if cons.get('total_consumed',0) > 0: not_found_set[canon]['teve_consumo'] = True

    # Recalcular mes_ativos e mes_grupo_ativos usando apenas emails ativos
    emails_ativos = {u['email'] for u in users_list}
    mes_ativos2 = defaultdict(set)
    mes_grupo_ativos2 = defaultdict(lambda: defaultdict(set))
    for email in emails_ativos:
        if email in user_map:
            for mes in user_map[email]['monthly']:
                mes_ativos2[mes].add(email)
    # Para grupos, precisamos do product_name — re-scan consumo para ativos
    with open(p_consumo, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            em = row.get('user_email','').strip().lower()
            if em not in emails_ativos: continue
            d = row.get('first_consumed_at','')
            mes = d[:7] if d else ''
            if mes:
                grupo = get_grupo(row.get('product_name',''))
                mes_grupo_ativos2[mes][grupo].add(em)

    # ── Dados dos gráficos ──
    all_meses = sorted(set(list(mes_total.keys()) + list(mes_ativos2.keys())))
    meses_sorted = all_meses[-18:]
    grupos_principais = ['Executivos','Pré-Vendas','FullPass','Gestão','Canais & Parcerias']

    evolucao_total  = [len(mes_total.get(m,set()))   for m in meses_sorted]
    evolucao_ativos = [len(mes_ativos2.get(m,set()))  for m in meses_sorted]
    grupos_total    = {g:[len(mes_grupo_total[m].get(g,set()))   for m in meses_sorted] for g in grupos_principais}
    grupos_ativos   = {g:[len(mes_grupo_ativos2[m].get(g,set())) for m in meses_sorted] for g in grupos_principais}

    retencao = []
    for i in range(1, len(meses_sorted)):
        ma,mb = meses_sorted[i-1], meses_sorted[i]
        ua = mes_ativos2.get(ma,set())
        ub = mes_ativos2.get(mb,set())
        retidos = ua & ub if ua else set()
        taxa = round(len(retidos)/len(ua)*100) if ua else 0
        retencao.append({'mes':mb,'taxa':taxa,'retidos':len(retidos),'base':len(ua)})

    empresas_ativas_set = {u['company'] for u in users_list}
    ranking = sorted(
        [(emp,cnt) for emp,cnt in empresa_aulas_recentes.items() if emp in empresas_ativas_set],
        key=lambda x:-x[1]
    )[:15]

    charts_data = {
        'meses': meses_sorted,
        'evolucao_total':  evolucao_total,
        'evolucao_ativos': evolucao_ativos,
        'grupos_total':    grupos_total,
        'grupos_ativos':   grupos_ativos,
        'ranking':         ranking,
        'retencao':        retencao,
    }

    # ── Companies ──
    co_map = defaultdict(lambda: {'total':0,'active_m':0,'offensive':0,'green':0,'yellow':0,'red':0,'black':0,'never':0})
    for u in users_list:
        c = u['company']
        co_map[c]['total'] += 1
        if u['active_this_month']: co_map[c]['active_m'] += 1
        co_map[c][u['flag']] += 1
        if u['never_consumed']: co_map[c]['never'] += 1

    company_list = []
    for emp in sorted(co_map.keys()):
        _, info = resolve(emp)
        company_list.append({'empresa':emp,'csm':info.get('csm',''),'co_status':info.get('status',''),**co_map[emp]})

    empresas_com_usuarios_lower = {c['empresa'].lower() for c in company_list}
    for emp in sorted(ativas_raw):
        if emp.lower() not in empresas_com_usuarios_lower:
            info = clientes_raw[emp]
            company_list.append({'empresa':emp,'csm':info.get('csm',''),'co_status':'Ativo',
                                  'total':0,'active_m':0,'offensive':0,'green':0,'yellow':0,'red':0,'black':0,'never':0})
    company_list.sort(key=lambda x: x['empresa'])

    not_found_list = [
        {'empresa':emp,'co_status':d['co_status'],'total':d['total'],'teve_consumo':d['teve_consumo']}
        for emp,d in sorted(not_found_set.items(),key=lambda x:-x[1]['total'])
        if d['co_status'] not in ('Churn','Inativo')
    ]
    never_list = [u for u in users_list if u['never_consumed']]

    total  = len(users_list)
    active = sum(1 for u in users_list if u['active_this_month'])
    print(f"  {total:,} usuários de empresas ativas | {active:,} ativos este mês")
    print(f"  {len(company_list)} empresas | {len(orphan_users)} órfãos | {len(not_found_list)} não cadastradas")

    return users_list, company_list, never_list, not_found_list, orphan_users, charts_data

# ─────────────────────────────────────────
def gerar_html(users_list, company_list, never_list, not_found_list, orphan_users, charts_data):
    agora = datetime.now().strftime('%d/%m/%Y')
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, OUTPUT_HTML)
    print(f"\nGerando HTML...")

    U  = json.dumps(users_list,    ensure_ascii=False, separators=(',',':'))
    C  = json.dumps(company_list,  ensure_ascii=False, separators=(',',':'))
    NV = json.dumps(never_list,    ensure_ascii=False, separators=(',',':'))
    NF = json.dumps(not_found_list,ensure_ascii=False, separators=(',',':'))
    OR = json.dumps(orphan_users,  ensure_ascii=False, separators=(',',':'))
    CH = json.dumps(charts_data,   ensure_ascii=False, separators=(',',':'))

    CSS = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_css.txt')).read()
    BODY = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_body.txt')).read()
    JS_LOGIC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'template_js.txt')).read()

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PipeLovers - Engajamento</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>
{BODY}
<script>
var U={U};
var C={C};
var NV={NV};
var NF={NF};
var OR={OR};
var CHARTS={CH};
var UPD="{agora}";
{JS_LOGIC}
</script>
</body>
</html>'''

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  {OUTPUT_HTML} gerado ({os.path.getsize(caminho)//1024} KB)")
    return caminho

if __name__ == '__main__':
    users_list, company_list, never_list, not_found_list, orphan_users, charts_data = processar()
    caminho = gerar_html(users_list, company_list, never_list, not_found_list, orphan_users, charts_data)
    print(f"\nPronto! Dashboard gerado: {os.path.basename(caminho)}")
