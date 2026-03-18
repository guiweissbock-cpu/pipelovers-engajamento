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

    import base64 as _b64
    CSS      = _b64.b64decode("Cjpyb290ey0tbmF2eTojMGYyOTUyOy0tbWlkOiMyNTYzYjA7LS1za3k6IzNiODJmNjstLXNreS1sOiNlZmY2ZmY7LS1za3ktcDojZjhmYWZmOy0tZzUwOiNmOWZhZmI7LS1nMTAwOiNmMWY1Zjk7LS1nMjAwOiNlMmU4ZjA7LS1nNDAwOiM5NGEzYjg7LS1nNTAwOiM2NDc0OGI7LS1nNjAwOiM0NzU1Njk7LS1nNzAwOiMzMzQxNTU7LS1nODAwOiMxZTI5M2I7LS1ncmVlbjojMDU5NjY5Oy0tZ2w6I2VjZmRmNTstLWdiOiM2ZWU3Yjc7LS15ZWw6I2Q5NzcwNjstLXlsOiNmZmZiZWI7LS15YjojZmNkMzRkOy0tcmVkOiNkYzI2MjY7LS1ybDojZmVmMmYyOy0tcmI6I2ZjYTVhNTstLWJsazojMzM0MTU1Oy0tYmtsOiNmOGZhZmM7LS1ia2I6Izk0YTNiODstLW9yYTojZWE1ODBjOy0tb2w6I2ZmZjdlZDstLW9iOiNmZGJhNzQ7LS1wdXI6IzdjM2FlZDstLXBsOiNmNWYzZmY7LS1wYjojYzRiNWZkOy0tcjoxMnB4Oy0tc2g6MCAxcHggM3B4IHJnYmEoMTUsNDEsODIsLjA3KSwwIDFweCAycHggcmdiYSgxNSw0MSw4MiwuMDQpO30KKntib3gtc2l6aW5nOmJvcmRlci1ib3g7bWFyZ2luOjA7cGFkZGluZzowO30KYm9keXtmb250LWZhbWlseToiUGx1cyBKYWthcnRhIFNhbnMiLHNhbnMtc2VyaWY7YmFja2dyb3VuZDp2YXIoLS1nNTApO2NvbG9yOnZhcigtLWc4MDApO21pbi1oZWlnaHQ6MTAwdmg7Zm9udC1zaXplOjE0cHg7fQouaGRye2JhY2tncm91bmQ6dmFyKC0tbmF2eSk7aGVpZ2h0OjU2cHg7cGFkZGluZzowIDI0cHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2Vlbjtwb3NpdGlvbjpzdGlja3k7dG9wOjA7ei1pbmRleDo0MDA7Ym94LXNoYWRvdzowIDJweCAxMHB4IHJnYmEoMTUsNDEsODIsLjIpO30KLmJyYW5ke2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjEwcHg7fS5iaWNve3dpZHRoOjMwcHg7aGVpZ2h0OjMwcHg7YmFja2dyb3VuZDp2YXIoLS1za3kpO2JvcmRlci1yYWRpdXM6N3B4O2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7anVzdGlmeS1jb250ZW50OmNlbnRlcjtmb250LXNpemU6MTJweDtmb250LXdlaWdodDo4MDA7Y29sb3I6I2ZmZjt9LmJuYW1le2ZvbnQtc2l6ZToxNnB4O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjojZmZmO30uYnRhZ3tmb250LXNpemU6MTFweDtjb2xvcjpyZ2JhKDI1NSwyNTUsMjU1LC40KTttYXJnaW4tdG9wOjFweDt9LnVwZHtmb250LXNpemU6MTFweDtjb2xvcjpyZ2JhKDI1NSwyNTUsMjU1LC4zNSk7fQoubmF2e2JhY2tncm91bmQ6I2ZmZjtib3JkZXItYm90dG9tOjFweCBzb2xpZCB2YXIoLS1nMjAwKTtwYWRkaW5nOjAgMjRweDtkaXNwbGF5OmZsZXg7cG9zaXRpb246c3RpY2t5O3RvcDo1NnB4O3otaW5kZXg6MzAwO2JveC1zaGFkb3c6dmFyKC0tc2gpO292ZXJmbG93LXg6YXV0bzt9Ci5udGFie3BhZGRpbmc6MTNweCAxNnB4O2ZvbnQtc2l6ZToxM3B4O2ZvbnQtd2VpZ2h0OjYwMDtjb2xvcjp2YXIoLS1nNTAwKTtjdXJzb3I6cG9pbnRlcjtib3JkZXItYm90dG9tOjJweCBzb2xpZCB0cmFuc3BhcmVudDt0cmFuc2l0aW9uOmFsbCAuMTVzO3doaXRlLXNwYWNlOm5vd3JhcDt9Lm50YWI6aG92ZXJ7Y29sb3I6dmFyKC0tbWlkKTt9Lm50YWIub257Y29sb3I6dmFyKC0tbWlkKTtib3JkZXItYm90dG9tLWNvbG9yOnZhcigtLXNreSk7fQouZmJhcntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgdmFyKC0tZzIwMCk7cGFkZGluZzoxMHB4IDI0cHg7ZGlzcGxheTpmbGV4O2dhcDoxMHB4O2FsaWduLWl0ZW1zOmZsZXgtZW5kO2ZsZXgtd3JhcDp3cmFwO30KLmZne2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjNweDt9LmZse2ZvbnQtc2l6ZToxMHB4O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjp2YXIoLS1nNDAwKTt0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7bGV0dGVyLXNwYWNpbmc6LjVweDt9CnNlbGVjdCxpbnB1dFt0eXBlPXRleHRde2JhY2tncm91bmQ6dmFyKC0tZzUwKTtib3JkZXI6MS41cHggc29saWQgdmFyKC0tZzIwMCk7Y29sb3I6dmFyKC0tZzgwMCk7cGFkZGluZzo2cHggMTBweDtib3JkZXItcmFkaXVzOjdweDtmb250LXNpemU6MTJweDtmb250LWZhbWlseTppbmhlcml0O291dGxpbmU6bm9uZTttaW4td2lkdGg6MTQwcHg7dHJhbnNpdGlvbjpib3JkZXItY29sb3IgLjE1czt9CnNlbGVjdDpmb2N1cyxpbnB1dDpmb2N1c3tib3JkZXItY29sb3I6dmFyKC0tc2t5KTtiYWNrZ3JvdW5kOiNmZmY7fQouYnRuZntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2NvbG9yOnZhcigtLWc2MDApO3BhZGRpbmc6NnB4IDEycHg7Ym9yZGVyLXJhZGl1czo3cHg7Zm9udC1zaXplOjEycHg7Zm9udC13ZWlnaHQ6NjAwO2N1cnNvcjpwb2ludGVyO2ZvbnQtZmFtaWx5OmluaGVyaXQ7dHJhbnNpdGlvbjphbGwgLjE1czthbGlnbi1zZWxmOmZsZXgtZW5kO30uYnRuZjpob3Zlcntib3JkZXItY29sb3I6dmFyKC0tc2t5KTtjb2xvcjp2YXIoLS1taWQpO30KLmN0YWd7Zm9udC1zaXplOjEycHg7Zm9udC13ZWlnaHQ6NjAwO2NvbG9yOnZhcigtLW1pZCk7YmFja2dyb3VuZDp2YXIoLS1za3ktbCk7Ym9yZGVyOjFweCBzb2xpZCAjYmZkYmZlO3BhZGRpbmc6NHB4IDEwcHg7Ym9yZGVyLXJhZGl1czoyMHB4O2FsaWduLXNlbGY6ZmxleC1lbmQ7fQoucGd7ZGlzcGxheTpub25lO3BhZGRpbmc6MjBweCAyNHB4O30ucGcub257ZGlzcGxheTpibG9jazt9Ci5rcm93e2Rpc3BsYXk6Z3JpZDtnYXA6MTJweDttYXJnaW4tYm90dG9tOjIwcHg7fS5rNntncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDYsMWZyKTt9Lmsze2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMywxZnIpO21heC13aWR0aDo1MjBweDt9Lmsye2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMiwxZnIpO21heC13aWR0aDozNjBweDt9Ci5rcGl7YmFja2dyb3VuZDojZmZmO2JvcmRlcjoxLjVweCBzb2xpZCB2YXIoLS1nMjAwKTtib3JkZXItcmFkaXVzOnZhcigtLXIpO3BhZGRpbmc6MTRweCAxNnB4O2JveC1zaGFkb3c6dmFyKC0tc2gpO30ua3BpLmNsa3tjdXJzb3I6cG9pbnRlcjt0cmFuc2l0aW9uOmFsbCAuMTVzO30ua3BpLmNsazpob3Zlcntib3JkZXItY29sb3I6dmFyKC0tc2t5KTtib3gtc2hhZG93OjAgNHB4IDE2cHggcmdiYSgxNSw0MSw4MiwuMSk7fS5rcGkuc2Vse2JvcmRlci1jb2xvcjp2YXIoLS1za3kpO2JveC1zaGFkb3c6MCAwIDAgM3B4IHJnYmEoNTksMTMwLDI0NiwuMTIpO30KLmtsYmx7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzouNXB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi1ib3R0b206NnB4O30ua3ZhbHtmb250LXNpemU6MjRweDtmb250LXdlaWdodDo4MDA7bGluZS1oZWlnaHQ6MTtsZXR0ZXItc3BhY2luZzotLjVweDt9LmtzdWJ7Zm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7bWFyZ2luLXRvcDozcHg7fQouYy1ie2NvbG9yOnZhcigtLW1pZCk7fS5jLWd7Y29sb3I6dmFyKC0tZ3JlZW4pO30uYy15e2NvbG9yOnZhcigtLXllbCk7fS5jLXJ7Y29sb3I6dmFyKC0tcmVkKTt9LmMta3tjb2xvcjp2YXIoLS1ibGspO30uYy1ve2NvbG9yOnZhcigtLW9yYSk7fS5jLXB7Y29sb3I6dmFyKC0tcHVyKTt9Ci5zZWN7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzouOHB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi1ib3R0b206MTBweDtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDo4cHg7fS5zZWM6OmFmdGVye2NvbnRlbnQ6IiI7ZmxleDoxO2hlaWdodDoxcHg7YmFja2dyb3VuZDp2YXIoLS1nMjAwKTt9Ci50d3JhcHtiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7b3ZlcmZsb3c6aGlkZGVuO2JveC1zaGFkb3c6dmFyKC0tc2gpO21hcmdpbi1ib3R0b206MjBweDt9Ci50aGRye3BhZGRpbmc6MTJweCAxNnB4O2JvcmRlci1ib3R0b206MXB4IHNvbGlkIHZhcigtLWcxMDApO2Rpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjthbGlnbi1pdGVtczpjZW50ZXI7fS50dGx7Zm9udC1zaXplOjEzcHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLWc3MDApO30udGNudHtmb250LXNpemU6MTJweDtjb2xvcjp2YXIoLS1nNDAwKTt9Ci50c2Nye292ZXJmbG93LXg6YXV0bzttYXgtaGVpZ2h0OjUyMHB4O292ZXJmbG93LXk6YXV0bzt9CnRhYmxle3dpZHRoOjEwMCU7Ym9yZGVyLWNvbGxhcHNlOmNvbGxhcHNlO310aHtwYWRkaW5nOjlweCAxMnB4O3RleHQtYWxpZ246bGVmdDtmb250LXNpemU6MTBweDtmb250LXdlaWdodDo3MDA7dGV4dC10cmFuc2Zvcm06dXBwZXJjYXNlO2xldHRlci1zcGFjaW5nOi41cHg7Y29sb3I6dmFyKC0tZzQwMCk7YmFja2dyb3VuZDp2YXIoLS1nNTApO2JvcmRlci1ib3R0b206MXB4IHNvbGlkIHZhcigtLWcyMDApO3doaXRlLXNwYWNlOm5vd3JhcDtwb3NpdGlvbjpzdGlja3k7dG9wOjA7ei1pbmRleDoxO30KdGR7cGFkZGluZzoxMHB4IDEycHg7Zm9udC1zaXplOjEycHg7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgdmFyKC0tZzEwMCk7dmVydGljYWwtYWxpZ246bWlkZGxlO310cjpsYXN0LWNoaWxkIHRke2JvcmRlci1ib3R0b206bm9uZTt9dHI6aG92ZXIgdGR7YmFja2dyb3VuZDp2YXIoLS1za3ktcCk7fQoucGlsbHtkaXNwbGF5OmlubGluZS1mbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6NHB4O3BhZGRpbmc6MnB4IDhweDtib3JkZXItcmFkaXVzOjIwcHg7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3doaXRlLXNwYWNlOm5vd3JhcDt9Ci5wLW97YmFja2dyb3VuZDp2YXIoLS1vbCk7Y29sb3I6dmFyKC0tb3JhKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLW9iKTt9LnAtZ3tiYWNrZ3JvdW5kOnZhcigtLWdsKTtjb2xvcjp2YXIoLS1ncmVlbik7Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1nYik7fS5wLXl7YmFja2dyb3VuZDp2YXIoLS15bCk7Y29sb3I6dmFyKC0teWVsKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLXliKTt9LnAtcntiYWNrZ3JvdW5kOnZhcigtLXJsKTtjb2xvcjp2YXIoLS1yZWQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tcmIpO30ucC1re2JhY2tncm91bmQ6dmFyKC0tYmtsKTtjb2xvcjp2YXIoLS1ibGspO2JvcmRlcjoxcHggc29saWQgdmFyKC0tYmtiKTt9LnAtcHtiYWNrZ3JvdW5kOnZhcigtLXBsKTtjb2xvcjp2YXIoLS1wdXIpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tcGIpO30ucC1ncntiYWNrZ3JvdW5kOnZhcigtLWcxMDApO2NvbG9yOnZhcigtLWc1MDApO2JvcmRlcjoxcHggc29saWQgdmFyKC0tZzIwMCk7fQouY29ncmlke2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDQsMWZyKTtnYXA6MTJweDttYXJnaW4tYm90dG9tOjIwcHg7fQouY29jYXJke2JhY2tncm91bmQ6I2ZmZjtib3JkZXI6MS41cHggc29saWQgdmFyKC0tZzIwMCk7Ym9yZGVyLXJhZGl1czp2YXIoLS1yKTtwYWRkaW5nOjE0cHggMTZweDtib3gtc2hhZG93OnZhcigtLXNoKTtjdXJzb3I6cG9pbnRlcjt0cmFuc2l0aW9uOmFsbCAuMTVzO30uY29jYXJkOmhvdmVye2JvcmRlci1jb2xvcjp2YXIoLS1za3kpO2JveC1zaGFkb3c6MCA0cHggMTRweCByZ2JhKDE1LDQxLDgyLC4xKTt9LmNvY2FyZC5zZWx7Ym9yZGVyLWNvbG9yOnZhcigtLXNreSk7Ym94LXNoYWRvdzowIDAgMCAzcHggcmdiYSg1OSwxMzAsMjQ2LC4xMik7fQouY28tdG9we2Rpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjthbGlnbi1pdGVtczpmbGV4LXN0YXJ0O21hcmdpbi1ib3R0b206NnB4O30uY28tbmFtZXtmb250LXNpemU6MTNweDtmb250LXdlaWdodDo3MDA7Y29sb3I6dmFyKC0tbmF2eSk7bGluZS1oZWlnaHQ6MS4yO30uY28tY3Nte2ZvbnQtc2l6ZToxMHB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi10b3A6MnB4O30KLmNvLWJhcntoZWlnaHQ6NHB4O2JhY2tncm91bmQ6dmFyKC0tZzEwMCk7Ym9yZGVyLXJhZGl1czoycHg7b3ZlcmZsb3c6aGlkZGVuO21hcmdpbjo4cHggMCA2cHg7fS5jby1iZntoZWlnaHQ6MTAwJTtib3JkZXItcmFkaXVzOjJweDt9Ci5jby1zdGF0c3tkaXNwbGF5OmZsZXg7Z2FwOjVweDtmbGV4LXdyYXA6d3JhcDt9LmNvc3tkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDozcHg7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NjAwO30KLmRvdHt3aWR0aDo3cHg7aGVpZ2h0OjdweDtib3JkZXItcmFkaXVzOjUwJTtmbGV4LXNocmluazowO30uZC1ve2JhY2tncm91bmQ6dmFyKC0tb3JhKTt9LmQtZ3tiYWNrZ3JvdW5kOnZhcigtLWdyZWVuKTt9LmQteXtiYWNrZ3JvdW5kOnZhcigtLXllbCk7fS5kLXJ7YmFja2dyb3VuZDp2YXIoLS1yZWQpO30uZC1re2JhY2tncm91bmQ6dmFyKC0tYmxrKTt9Ci5kZXR7YmFja2dyb3VuZDojZmZmO2JvcmRlcjoxLjVweCBzb2xpZCB2YXIoLS1za3kpO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7cGFkZGluZzoxNnB4IDIwcHg7bWFyZ2luLWJvdHRvbToyMHB4O2JveC1zaGFkb3c6MCAwIDAgM3B4IHJnYmEoNTksMTMwLDI0NiwuMDgpO30KLmRldC10dGx7Zm9udC1zaXplOjE0cHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLW5hdnkpO21hcmdpbi1ib3R0b206MTJweDtkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47YWxpZ24taXRlbXM6Y2VudGVyO30KLmNsc3tjdXJzb3I6cG9pbnRlcjtjb2xvcjp2YXIoLS1nNDAwKTtmb250LXNpemU6MThweDtsaW5lLWhlaWdodDoxO30uY2xzOmhvdmVye2NvbG9yOnZhcigtLWc3MDApO30KLmlib3h7Ym9yZGVyLXJhZGl1czp2YXIoLS1yKTtwYWRkaW5nOjEycHggMTZweDttYXJnaW4tYm90dG9tOjE2cHg7Zm9udC1zaXplOjEzcHg7Zm9udC13ZWlnaHQ6NTAwO30KLmlib3gtcHtiYWNrZ3JvdW5kOnZhcigtLXBsKTtib3JkZXI6MS41cHggc29saWQgdmFyKC0tcGIpO2NvbG9yOnZhcigtLXB1cik7fS5pYm94LXl7YmFja2dyb3VuZDp2YXIoLS15bCk7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLXliKTtjb2xvcjp2YXIoLS15ZWwpO30KLmNrLWdyb3Vwe2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjRweDtwYWRkaW5nOjRweCAwO30KLmNrLWxibHtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDo2cHg7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tZzYwMCk7Y3Vyc29yOnBvaW50ZXI7d2hpdGUtc3BhY2U6bm93cmFwO30KLmNrLWxibCBpbnB1dFt0eXBlPWNoZWNrYm94XXt3aWR0aDoxNHB4O2hlaWdodDoxNHB4O2FjY2VudC1jb2xvcjp2YXIoLS1za3kpO2N1cnNvcjpwb2ludGVyO2ZsZXgtc2hyaW5rOjA7fQouY2stbGJsOmhvdmVye2NvbG9yOnZhcigtLW1pZCk7fQouY2hhcnQtc2VjdGlvbntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7cGFkZGluZzoxOHB4IDIycHg7bWFyZ2luOjAgMjRweCAyMHB4O2JveC1zaGFkb3c6dmFyKC0tc2gpO30KLmNoYXJ0LXRpdGxle2ZvbnQtc2l6ZToxMXB4O2ZvbnQtd2VpZ2h0OjcwMDt0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7bGV0dGVyLXNwYWNpbmc6LjdweDtjb2xvcjp2YXIoLS1nNDAwKTttYXJnaW4tYm90dG9tOjE0cHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2Vlbjt9Ci5jaGFydC1jYW52YXMtd3JhcHtwb3NpdGlvbjpyZWxhdGl2ZTtoZWlnaHQ6MTgwcHg7fQoucmFuay1saXN0e2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjZweDt9Ci5yYW5rLXJvd3tkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDoxMHB4O2ZvbnQtc2l6ZToxMnB4O30KLnJhbmstbnVte3dpZHRoOjE4cHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLWc0MDApO3RleHQtYWxpZ246cmlnaHQ7ZmxleC1zaHJpbms6MDt9Ci5yYW5rLW5hbWV7ZmxleDoxO2ZvbnQtd2VpZ2h0OjYwMDtjb2xvcjp2YXIoLS1nNzAwKTtvdmVyZmxvdzpoaWRkZW47dGV4dC1vdmVyZmxvdzplbGxpcHNpczt3aGl0ZS1zcGFjZTpub3dyYXA7fQoucmFuay1iYXItd3JhcHt3aWR0aDoxMjBweDtoZWlnaHQ6NnB4O2JhY2tncm91bmQ6dmFyKC0tZzEwMCk7Ym9yZGVyLXJhZGl1czozcHg7b3ZlcmZsb3c6aGlkZGVuO2ZsZXgtc2hyaW5rOjA7fQoucmFuay1iYXItZmlsbHtoZWlnaHQ6MTAwJTtib3JkZXItcmFkaXVzOjNweDtiYWNrZ3JvdW5kOnZhcigtLXNreSk7fQoucmFuay12YWx7d2lkdGg6NDBweDt0ZXh0LWFsaWduOnJpZ2h0O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjp2YXIoLS1taWQpO2ZsZXgtc2hyaW5rOjA7fQouY2hhcnRzLWdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczoxZnIgMWZyO2dhcDoxNnB4O3BhZGRpbmc6MCAyNHB4IDIwcHg7fQouY2hhcnRzLWdyaWQtM3tkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOjJmciAxZnI7Z2FwOjE2cHg7cGFkZGluZzowIDI0cHggMjBweDt9Ci5yZXQtZ3JpZHtkaXNwbGF5OmZsZXg7Z2FwOjEwcHg7ZmxleC13cmFwOndyYXA7fQoucmV0LWNhcmR7ZmxleDoxO21pbi13aWR0aDo4MHB4O2JhY2tncm91bmQ6dmFyKC0tZzUwKTtib3JkZXItcmFkaXVzOjhweDtwYWRkaW5nOjEwcHggMTJweDt0ZXh0LWFsaWduOmNlbnRlcjt9Ci5yZXQtcGN0e2ZvbnQtc2l6ZToyMnB4O2ZvbnQtd2VpZ2h0OjgwMDtjb2xvcjp2YXIoLS1taWQpO30KLnJldC1tZXN7Zm9udC1zaXplOjEwcHg7Y29sb3I6dmFyKC0tZzQwMCk7bWFyZ2luLXRvcDoycHg7fQoucmV0LXN1Yntmb250LXNpemU6MTBweDtjb2xvcjp2YXIoLS1nNTAwKTttYXJnaW4tdG9wOjFweDt9Cjo6LXdlYmtpdC1zY3JvbGxiYXJ7d2lkdGg6NXB4O2hlaWdodDo1cHg7fTo6LXdlYmtpdC1zY3JvbGxiYXItdHJhY2t7YmFja2dyb3VuZDp0cmFuc3BhcmVudDt9Ojotd2Via2l0LXNjcm9sbGJhci10aHVtYntiYWNrZ3JvdW5kOnZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6M3B4O30K").decode('utf-8')
    BODY     = _b64.b64decode("CjxkaXYgY2xhc3M9ImhkciI+CiAgPGRpdiBjbGFzcz0iYnJhbmQiPjxkaXYgY2xhc3M9ImJpY28iPlBMPC9kaXY+PGRpdj48ZGl2IGNsYXNzPSJibmFtZSI+UGlwZUxvdmVyczwvZGl2PjxkaXYgY2xhc3M9ImJ0YWciPkRhc2hib2FyZCBkZSBFbmdhamFtZW50bzwvZGl2PjwvZGl2PjwvZGl2PgogIDxzcGFuIGNsYXNzPSJ1cGQiIGlkPSJ1cGQtbGJsIj48L3NwYW4+CjwvZGl2Pgo8ZGl2IGNsYXNzPSJuYXYiPgogIDxkaXYgY2xhc3M9Im50YWIgb24iIG9uY2xpY2s9ImdvVGFiKCdvdicsdGhpcykiPiYjMTI4MjAyOyBPdmVydmlldzwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCdlbScsdGhpcykiPiYjMTI3OTcwOyBFbXByZXNhczwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCd1cycsdGhpcykiPiYjMTI4MTAwOyBVc3UmYWFjdXRlO3Jpb3M8L2Rpdj4KICA8ZGl2IGNsYXNzPSJudGFiIiAgICBvbmNsaWNrPSJnb1RhYignbmEnLHRoaXMpIj4mIzk4ODg7JiM2NTAzOTsgTnVuY2EgQXNzaXN0aXJhbTwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCduZicsdGhpcykiPiYjMTAwNjc7IEVtcHJlc2FzIHMvIGNhZGFzdHJvPC9kaXY+CiAgPGRpdiBjbGFzcz0ibnRhYiIgICAgb25jbGljaz0iZ29UYWIoJ29yJyx0aGlzKSI+JiMxMjgxMDA7IFVzdSZhYWN1dGU7cmlvcyBzLyBlbXByZXNhPC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy1vdiIgY2xhc3M9InBnIG9uIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+RW1wcmVzYTwvZGl2PjxzZWxlY3QgaWQ9Im92LWNvIj48b3B0aW9uIHZhbHVlPSIiPlRvZGFzPC9vcHRpb24+PC9zZWxlY3Q+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkNTTTwvZGl2PjxzZWxlY3QgaWQ9Im92LWNzbSI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPgogICAgICA8ZGl2IGNsYXNzPSJmbCI+Q3JpYSZjY2VkaWw7JmF0aWxkZTtvIGRvIHVzdSZhYWN1dGU7cmlvPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9ImNrLWdyb3VwIj4KICAgICAgICA8bGFiZWwgY2xhc3M9ImNrLWxibCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBjbGFzcz0ib3YtY3IiIHZhbHVlPSJsdDMiPiBNZW5vcyBkZSAzIG1lc2VzPC9sYWJlbD4KICAgICAgICA8bGFiZWwgY2xhc3M9ImNrLWxibCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBjbGFzcz0ib3YtY3IiIHZhbHVlPSIzdG82Ij4gMyBhIDYgbWVzZXM8L2xhYmVsPgogICAgICAgIDxsYWJlbCBjbGFzcz0iY2stbGJsIj48aW5wdXQgdHlwZT0iY2hlY2tib3giIGNsYXNzPSJvdi1jciIgdmFsdWU9Imd0NiI+IE1haXMgZGUgNiBtZXNlczwvbGFiZWw+CiAgICAgICAgPGxhYmVsIGNsYXNzPSJjay1sYmwiPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgY2xhc3M9Im92LWNyIiB2YWx1ZT0ibm9kYXRlIj4gU2VtIGRhdGE8L2xhYmVsPgogICAgICA8L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPgogICAgICA8ZGl2IGNsYXNzPSJmbCI+R3J1cG8gLyBQbGFubzwvZGl2PgogICAgICA8c2VsZWN0IGlkPSJvdi1ncnVwbyI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PgogICAgPC9kaXY+CiAgICA8YnV0dG9uIGNsYXNzPSJidG5mIiBpZD0ib3YtcnN0Ij5MaW1wYXI8L2J1dHRvbj4KICA8L2Rpdj4KICA8ZGl2IGlkPSJvdi1ib2R5Ij48L2Rpdj4KPC9kaXY+Cgo8ZGl2IGlkPSJvdi1jaGFydHMiIHN0eWxlPSJkaXNwbGF5Om5vbmU7Ij4KICA8ZGl2IGNsYXNzPSJjaGFydHMtZ3JpZC0zIj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MDsiPgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10aXRsZSI+VXN1w6FyaW9zIMO6bmljb3MgcG9yIG3DqnMgPHNwYW4gaWQ9ImdydXBvLXNlbC1sYmwiIHN0eWxlPSJmb250LXNpemU6MTBweDtjb2xvcjp2YXIoLS1za3kpOyI+PC9zcGFuPjwvZGl2PgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC1jYW52YXMtd3JhcCI+PGNhbnZhcyBpZD0iY2hhcnQtbWVuc2FsIj48L2NhbnZhcz48L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iY2hhcnQtc2VjdGlvbiIgc3R5bGU9Im1hcmdpbjowOyI+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXRpdGxlIj5SZXRlbsOnw6NvIG3DqnMgYSBtw6pzPC9kaXY+CiAgICAgIDxkaXYgaWQ9InJldC1ib2R5Ij48L2Rpdj4KICAgIDwvZGl2PgogIDwvZGl2PgogIDxkaXYgY2xhc3M9ImNoYXJ0cy1ncmlkIj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MDsiPgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10aXRsZSI+RXZvbHXDp8OjbyBwb3IgZ3J1cG88L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0iY2hhcnQtY2FudmFzLXdyYXAiPjxjYW52YXMgaWQ9ImNoYXJ0LWdydXBvcyI+PC9jYW52YXM+PC9kaXY+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MDsiPgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10aXRsZSI+VG9wIGVtcHJlc2FzICjDumx0aW1vcyAzIG1lc2VzKSA8c3BhbiBzdHlsZT0iZm9udC1zaXplOjEwcHg7Y29sb3I6dmFyKC0tZzQwMCk7Zm9udC13ZWlnaHQ6NDAwOyI+cG9yIG7CuiBkZSBhdWxhczwvc3Bhbj48L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0icmFuay1saXN0IiBpZD0icmFuay1ib2R5Ij48L2Rpdj4KICAgIDwvZGl2PgogIDwvZGl2Pgo8L2Rpdj4KPGRpdiBpZD0icGctZW0iIGNsYXNzPSJwZyI+CiAgPGRpdiBjbGFzcz0iZmJhciI+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkJ1c2NhcjwvZGl2PjxpbnB1dCB0eXBlPSJ0ZXh0IiBpZD0iZW0tcSIgcGxhY2Vob2xkZXI9Ik5vbWUgZGEgZW1wcmVzYS4uLiI+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkNTTTwvZGl2PjxzZWxlY3QgaWQ9ImVtLWNzbSI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9ImVtLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0iZW0tY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0iZW0tYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy11cyIgY2xhc3M9InBnIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+QnVzY2FyPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJ1cy1xIiBwbGFjZWhvbGRlcj0iTm9tZSBvdSBlLW1haWwuLi4iPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5FbXByZXNhPC9kaXY+PHNlbGVjdCBpZD0idXMtY28iPjxvcHRpb24gdmFsdWU9IiI+VG9kYXM8L29wdGlvbj48L3NlbGVjdD48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+Q1NNPC9kaXY+PHNlbGVjdCBpZD0idXMtY3NtIj48b3B0aW9uIHZhbHVlPSIiPlRvZG9zPC9vcHRpb24+PC9zZWxlY3Q+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkZsYWc8L2Rpdj4KICAgICAgPHNlbGVjdCBpZD0idXMtZmwiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+VG9kYXM8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJvZmZlbnNpdmUiPiYjMTI4MjkzOyBPZmVuc2l2YTwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9ImdyZWVuIj4mIzEyODk5NDsgR3JlZW48L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJ5ZWxsb3ciPiYjMTI4OTkzOyBZZWxsb3c8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJyZWQiPiYjMTI4MzA4OyBSZWQ8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJibGFjayI+JiM5ODk5OyBCbGFjazwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5DcmlhJmNjZWRpbDsmYXRpbGRlO288L2Rpdj4KICAgICAgPHNlbGVjdCBpZD0idXMtY3IiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+UXVhbHF1ZXI8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJsdDMiPk1lbm9zIGRlIDMgbWVzZXM8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSIzdG82Ij4zIGEgNiBtZXNlczwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9Imd0NiI+TWFpcyBkZSA2IG1lc2VzPC9vcHRpb24+CiAgICAgIDwvc2VsZWN0PgogICAgPC9kaXY+CiAgICA8YnV0dG9uIGNsYXNzPSJidG5mIiBpZD0idXMtcnN0Ij5MaW1wYXI8L2J1dHRvbj4KICAgIDxkaXYgY2xhc3M9ImN0YWciIGlkPSJ1cy1jdGFnIj48L2Rpdj4KICA8L2Rpdj4KICA8ZGl2IGlkPSJ1cy1ib2R5IiBzdHlsZT0icGFkZGluZzoyMHB4IDI0cHg7Ij48L2Rpdj4KPC9kaXY+CjxkaXYgaWQ9InBnLW5hIiBjbGFzcz0icGciPgogIDxkaXYgY2xhc3M9ImZiYXIiPgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5CdXNjYXI8L2Rpdj48aW5wdXQgdHlwZT0idGV4dCIgaWQ9Im5hLXEiIHBsYWNlaG9sZGVyPSJOb21lIG91IGUtbWFpbC4uLiI+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkVtcHJlc2E8L2Rpdj48c2VsZWN0IGlkPSJuYS1jbyI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rhczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5DU008L2Rpdj48c2VsZWN0IGlkPSJuYS1jc20iPjxvcHRpb24gdmFsdWU9IiI+VG9kb3M8L29wdGlvbj48L3NlbGVjdD48L2Rpdj4KICAgIDxidXR0b24gY2xhc3M9ImJ0bmYiIGlkPSJuYS1yc3QiPkxpbXBhcjwvYnV0dG9uPgogICAgPGRpdiBjbGFzcz0iY3RhZyIgaWQ9Im5hLWN0YWciPjwvZGl2PgogIDwvZGl2PgogIDxkaXYgaWQ9Im5hLWJvZHkiIHN0eWxlPSJwYWRkaW5nOjIwcHggMjRweDsiPjwvZGl2Pgo8L2Rpdj4KPGRpdiBpZD0icGctbmYiIGNsYXNzPSJwZyI+CiAgPGRpdiBjbGFzcz0iZmJhciI+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkJ1c2NhciBlbXByZXNhPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJuZi1xIiBwbGFjZWhvbGRlcj0iTm9tZSBkYSBlbXByZXNhLi4uIj48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+Q29uc3VtaXUgYXVsYXM/PC9kaXY+CiAgICAgIDxzZWxlY3QgaWQ9Im5mLWNvbnMiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+VG9kb3M8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJzaW0iPlNpbTwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9Im5hbyI+TiZhdGlsZGU7bzwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9Im5mLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0ibmYtY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0ibmYtYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy1vciIgY2xhc3M9InBnIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+QnVzY2FyPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJvci1xIiBwbGFjZWhvbGRlcj0iTm9tZSwgZS1tYWlsIG91IGVtcHJlc2EuLi4iPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5TdGF0dXMgZW1wcmVzYTwvZGl2PgogICAgICA8c2VsZWN0IGlkPSJvci1zdCI+CiAgICAgICAgPG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9IkNodXJuIj5DaHVybjwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9IkluYXRpdm8iPkluYXRpdm88L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJOJmF0aWxkZTtvIGNhZGFzdHJhZGEiPk4mYXRpbGRlO28gY2FkYXN0cmFkYTwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9Im9yLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0ib3ItY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0ib3ItYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo=").decode('utf-8')
    JS_LOGIC = _b64.b64decode("ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVwZC1sYmwiKS50ZXh0Q29udGVudD0iQXR1YWxpemFkbyBlbSAiK1VQRDsKZnVuY3Rpb24gZXNjKHMpe3JldHVybiBTdHJpbmcoc3x8IiIpLnJlcGxhY2UoLyYvZywiJmFtcDsiKS5yZXBsYWNlKC88L2csIiZsdDsiKS5yZXBsYWNlKC8+L2csIiZndDsiKS5yZXBsYWNlKC8iL2csIiZxdW90OyIpO30KZnVuY3Rpb24gcGN0KGEsYil7cmV0dXJuIGI+MD9NYXRoLnJvdW5kKGEvYioxMDApOjA7fQpmdW5jdGlvbiBtU2luY2UoZHMpe2lmKCFkcylyZXR1cm4gOTk5O3ZhciBkPW5ldyBEYXRlKGRzKSxuPW5ldyBEYXRlKCk7cmV0dXJuKG4uZ2V0RnVsbFllYXIoKS1kLmdldEZ1bGxZZWFyKCkpKjEyKyhuLmdldE1vbnRoKCktZC5nZXRNb250aCgpKTt9CmZ1bmN0aW9uIGZQaWxsKGYpewogIGlmKGY9PT0ib2ZmZW5zaXZlIilyZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1vIj4mIzEyODI5MzsgT2ZlbnNpdmE8L3NwYW4+JzsKICBpZihmPT09ImdyZWVuIikgICAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtZyI+JiMxMjg5OTQ7IEdyZWVuPC9zcGFuPic7CiAgaWYoZj09PSJ5ZWxsb3ciKSAgIHJldHVybic8c3BhbiBjbGFzcz0icGlsbCBwLXkiPiYjMTI4OTkzOyBZZWxsb3c8L3NwYW4+JzsKICBpZihmPT09InJlZCIpICAgICAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtciI+JiMxMjgzMDg7IFJlZDwvc3Bhbj4nOwogIHJldHVybic8c3BhbiBjbGFzcz0icGlsbCBwLWsiPiYjOTg5OTsgQmxhY2s8L3NwYW4+JzsKfQpmdW5jdGlvbiBzdFBpbGwocyl7CiAgaWYocz09PSJDaHVybiIpICByZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1yIj5DaHVybjwvc3Bhbj4nOwogIGlmKHM9PT0iSW5hdGl2byIpcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtayI+SW5hdGl2bzwvc3Bhbj4nOwogIGlmKHM9PT0iQXRpdm8iKSAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtZyI+QXRpdm88L3NwYW4+JzsKICByZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1wIj5OXHhFM28gY2FkYXN0cmFkYTwvc3Bhbj4nOwp9CmZ1bmN0aW9uIGdvVGFiKG4sZWwpewogIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5wZyIpLmZvckVhY2goZnVuY3Rpb24ocCl7cC5jbGFzc0xpc3QucmVtb3ZlKCJvbiIpO30pOwogIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5udGFiIikuZm9yRWFjaChmdW5jdGlvbih0KXt0LmNsYXNzTGlzdC5yZW1vdmUoIm9uIik7fSk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInBnLSIrbikuY2xhc3NMaXN0LmFkZCgib24iKTtlbC5jbGFzc0xpc3QuYWRkKCJvbiIpOwp9CmZ1bmN0aW9uIHBvcChpZCx2YWxzKXt2YXIgcz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7dmFscy5mb3JFYWNoKGZ1bmN0aW9uKHYpe3ZhciBvPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoIm9wdGlvbiIpO28udmFsdWU9djtvLnRleHRDb250ZW50PXY7cy5hcHBlbmRDaGlsZChvKTt9KTt9CnZhciBhY29zPVsuLi5uZXcgU2V0KFUubWFwKGZ1bmN0aW9uKHUpe3JldHVybiB1LmNvbXBhbnk7fSkpXS5zb3J0KCk7CnZhciBhY3Ntcz1bLi4ubmV3IFNldChVLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jc207fSkuZmlsdGVyKEJvb2xlYW4pKV0uc29ydCgpOwpwb3AoIm92LWNvIixhY29zKTtwb3AoIm92LWNzbSIsYWNzbXMpO3BvcCgiZW0tY3NtIixhY3Ntcyk7CnBvcCgidXMtY28iLGFjb3MpO3BvcCgidXMtY3NtIixhY3Ntcyk7CnBvcCgibmEtY28iLFsuLi5uZXcgU2V0KE5WLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jb21wYW55O30pKV0uc29ydCgpKTsKcG9wKCJuYS1jc20iLFsuLi5uZXcgU2V0KE5WLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jc207fSkuZmlsdGVyKEJvb2xlYW4pKV0uc29ydCgpKTsKdmFyIG92Rj1udWxsOwpmdW5jdGlvbiBydW5PdigpewogIHZhciBjbz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY28iKS52YWx1ZSxjc209ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWNzbSIpLnZhbHVlOwogIHZhciBjckNoZWNrZWQ9Wy4uLmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5vdi1jcjpjaGVja2VkIildLm1hcChmdW5jdGlvbihjKXtyZXR1cm4gYy52YWx1ZTt9KTsKICB2YXIgZmQ9VS5maWx0ZXIoZnVuY3Rpb24odSl7CiAgICBpZihjbyYmdS5jb21wYW55IT09Y28pcmV0dXJuIGZhbHNlOwogICAgaWYoY3NtJiZ1LmNzbSE9PWNzbSlyZXR1cm4gZmFsc2U7CiAgICBpZihjckNoZWNrZWQubGVuZ3RoPjApewogICAgICB2YXIgbm9EYXRlPSF1LmNyZWF0ZWRfYXQ7CiAgICAgIHZhciBtPW5vRGF0ZT8tMTptU2luY2UodS5jcmVhdGVkX2F0KTsKICAgICAgdmFyIGx0Mz0hbm9EYXRlJiZtPDMsaXMzdG82PSFub0RhdGUmJm0+PTMmJm08PTYsZ3Q2PSFub0RhdGUmJm0+NjsKICAgICAgdmFyIG9rPShjckNoZWNrZWQuaW5kZXhPZigibHQzIik+PTAmJmx0Myl8fChjckNoZWNrZWQuaW5kZXhPZigiM3RvNiIpPj0wJiZpczN0bzYpfHwKICAgICAgICAgICAgIChjckNoZWNrZWQuaW5kZXhPZigiZ3Q2Iik+PTAmJmd0Nil8fChjckNoZWNrZWQuaW5kZXhPZigibm9kYXRlIik+PTAmJm5vRGF0ZSk7CiAgICAgIGlmKCFvaylyZXR1cm4gZmFsc2U7CiAgICB9CiAgICByZXR1cm4gdHJ1ZTsKICB9KTsKICB2YXIgdG90PWZkLmxlbmd0aCxhTT1mZC5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuYWN0aXZlX3RoaXNfbW9udGg7fSkubGVuZ3RoOwogIHZhciBvZmY9ZmQuZmlsdGVyKGZ1bmN0aW9uKHUpe3JldHVybiB1LmZsYWc9PT0ib2ZmZW5zaXZlIjt9KTsKICB2YXIgeWVsPWZkLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5mbGFnPT09InllbGxvdyI7fSk7CiAgdmFyIHJlZD1mZC5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuZmxhZz09PSJyZWQiO30pOwogIHZhciBibGs9ZmQuZmlsdGVyKGZ1bmN0aW9uKHUpe3JldHVybiB1LmZsYWc9PT0iYmxhY2siO30pOwogIHZhciBrcGlzPVsKICAgIHtsYmw6IlRvdGFsIFVzdVx4RTFyaW9zIiwgICAgdmFsOnRvdCwgICAgICAgc3ViOiJlbXByZXNhcyBhdGl2YXMiLCAgICAgICAgICAgICAgY2xzOiJjLWIiLGdycDpudWxsfSwKICAgIHtsYmw6IkF0aXZvcyBlc3RlIG1ceEVBcyIsICAgdmFsOmFNLCAgICAgICAgc3ViOnBjdChhTSx0b3QpKyIlIGRvIHRvdGFsIiwgICAgICAgY2xzOiJjLWciLGdycDoiYWN0aXZlIn0sCiAgICB7bGJsOiImIzEyODI5MzsgT2ZlbnNpdmEiLCAgIHZhbDpvZmYubGVuZ3RoLHN1YjoiYXRpdm9zIG5vcyAyIFx4RkFsdGltb3MgbWVzZXMiLGNsczoiYy1vIixncnA6Im9mZmVuc2l2ZSJ9LAogICAge2xibDoiJiMxMjg5OTM7IFllbGxvdyIsICAgICB2YWw6eWVsLmxlbmd0aCxzdWI6ImluYXRpdm9zIDMwLTYwIGRpYXMiLCAgICAgICAgICBjbHM6ImMteSIsZ3JwOiJ5ZWxsb3cifSwKICAgIHtsYmw6IiYjMTI4MzA4OyBSZWQiLCAgICAgICAgdmFsOnJlZC5sZW5ndGgsc3ViOiJpbmF0aXZvcyA2MC05MCBkaWFzIiwgICAgICAgICAgY2xzOiJjLXIiLGdycDoicmVkIn0sCiAgICB7bGJsOiImIzk4OTk7IEJsYWNrIiwgICAgICAgIHZhbDpibGsubGVuZ3RoLHN1YjoiaW5hdGl2b3MgOTArIGRpYXMiLCAgICAgICAgICAgIGNsczoiYy1rIixncnA6ImJsYWNrIn0sCiAgXTsKICB2YXIga2g9JzxkaXYgY2xhc3M9Imtyb3cgazYiPic7CiAga3Bpcy5mb3JFYWNoKGZ1bmN0aW9uKGspewogICAgdmFyIGlzU2VsPShvdkY9PT1rLmdycCYmay5ncnAhPT1udWxsKT8iIHNlbCI6IiIsaXNDbGs9ay5ncnA/IiBjbGsiOiIiOwogICAga2grPSc8ZGl2IGNsYXNzPSJrcGknK2lzQ2xrK2lzU2VsKyciJysoay5ncnA/JyBvbmNsaWNrPSJ0b2dPdihcJycray5ncnArJ1wnKSInOicnKSsnPicrCiAgICAgICc8ZGl2IGNsYXNzPSJrbGJsIj4nK2subGJsKyc8L2Rpdj48ZGl2IGNsYXNzPSJrdmFsICcray5jbHMrJyI+JytrLnZhbCsnPC9kaXY+PGRpdiBjbGFzcz0ia3N1YiI+JytrLnN1YisnPC9kaXY+PC9kaXY+JzsKICB9KTsKICBraCs9JzwvZGl2Pic7CiAgdmFyIGRoPScnOwogIGlmKG92Ril7CiAgICB2YXIgc3ViOwogICAgaWYob3ZGPT09ImFjdGl2ZSIpc3ViPWZkLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5hY3RpdmVfdGhpc19tb250aDt9KTsKICAgIGVsc2UgaWYob3ZGPT09Im9mZmVuc2l2ZSIpc3ViPW9mZjsKICAgIGVsc2Ugc3ViPWZkLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5mbGFnPT09b3ZGO30pOwogICAgdmFyIHNlZW49e307c3ViPXN1Yi5maWx0ZXIoZnVuY3Rpb24odSl7aWYoc2Vlblt1LmVtYWlsXSlyZXR1cm4gZmFsc2U7c2Vlblt1LmVtYWlsXT0xO3JldHVybiB0cnVlO30pOwogICAgdmFyIGxibE1hcD17ImFjdGl2ZSI6IkF0aXZvcyBlc3RlIG1ceGVhcyIsIm9mZmVuc2l2ZSI6IkVtIE9mZW5zaXZhICgyIFx4RkFsdGltb3MgbWVzZXMpIiwieWVsbG93IjoiWWVsbG93IEZsYWciLCJyZWQiOiJSZWQgRmxhZyIsImJsYWNrIjoiQmxhY2sgRmxhZyJ9OwogICAgdmFyIHJvd3M9c3ViLnNsaWNlKDAsMzAwKS5tYXAoZnVuY3Rpb24odSl7CiAgICAgIHJldHVybiAnPHRyPjx0ZD48ZGl2IHN0eWxlPSJmb250LXdlaWdodDo2MDA7Ij4nK2VzYyh1Lm5hbWUpKyc8L2Rpdj48ZGl2IHN0eWxlPSJmb250LXNpemU6MTFweDtjb2xvcjp2YXIoLS1nNDAwKTsiPicrZXNjKHUuZW1haWwpKyc8L2Rpdj48L3RkPicrCiAgICAgICAgJzx0ZD4nK2VzYyh1LmNvbXBhbnkpKyc8L3RkPjx0ZD4nK2VzYyh1LmNzbXx8Ilx1MjAxNCIpKyc8L3RkPjx0ZD4nK2ZQaWxsKHUuZmxhZykrJzwvdGQ+JysKICAgICAgICAnPHRkPicrZXNjKHUubGFzdF9jb25zdW1lZHx8Ilx1MjAxNCIpKyc8L3RkPjx0ZD4nK3UudG90YWxfY29uc3VtZWQrJzwvdGQ+PC90cj4nOwogICAgfSkuam9pbignJyk7CiAgICBkaD0nPGRpdiBjbGFzcz0iZGV0Ij48ZGl2IGNsYXNzPSJkZXQtdHRsIj48c3Bhbj4nK2xibE1hcFtvdkZdKycgXHUyMDE0ICcrc3ViLmxlbmd0aCsnIHVzdVx4RTFyaW9zPC9zcGFuPicrCiAgICAgICc8c3BhbiBjbGFzcz0iY2xzIiBvbmNsaWNrPSJvdkY9bnVsbDtydW5PdigpIj4mIzEwMDA1Ozwvc3Bhbj48L2Rpdj4nKwogICAgICAnPGRpdiBjbGFzcz0idHNjciI+PHRhYmxlPjx0aGVhZD48dHI+PHRoPlVzdVx4RTFyaW88L3RoPjx0aD5FbXByZXNhPC90aD48dGg+Q1NNPC90aD48dGg+RmxhZzwvdGg+PHRoPlx4REFsdGltbyBjb25zdW1vPC90aD48dGg+VG90YWwgYXVsYXM8L3RoPjwvdHI+PC90aGVhZD4nKwogICAgICAnPHRib2R5Picrcm93cysnPC90Ym9keT48L3RhYmxlPjwvZGl2PicrCiAgICAgIChzdWIubGVuZ3RoPjMwMD8nPGRpdiBzdHlsZT0icGFkZGluZzo4cHg7Zm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij5Nb3N0cmFuZG8gMzAwIGRlICcrc3ViLmxlbmd0aCsnPC9kaXY+JzonJykrCiAgICAnPC9kaXY+JzsKICB9CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWJvZHkiKS5pbm5lckhUTUw9JzxkaXYgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+JytraCtkaCsnPC9kaXY+JzsKfQpmdW5jdGlvbiB0b2dPdihnKXtvdkY9KG92Rj09PWcpP251bGw6ZztydW5PdigpO30KZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWNvIikuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5Pdik7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1jc20iKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk92KTsKZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLm92LWNyIikuZm9yRWFjaChmdW5jdGlvbihjKXtjLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIscnVuT3YpO30pOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtZ3J1cG8iKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk92KTsKCi8vIFBvcHVsYXRlIGdydXBvIGRyb3Bkb3duCnZhciBncnVwb3M9Wy4uLm5ldyBTZXQoT2JqZWN0LmtleXMoQ0hBUlRTLmdydXBvc19hdGl2b3MpKV0uc29ydCgpOwp2YXIgZ3JTZWw9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWdydXBvIik7CmdydXBvcy5mb3JFYWNoKGZ1bmN0aW9uKGcpe3ZhciBvPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoIm9wdGlvbiIpO28udmFsdWU9ZztvLnRleHRDb250ZW50PWc7Z3JTZWwuYXBwZW5kQ2hpbGQobyk7fSk7CgovLyBJbml0IGNoYXJ0cwp2YXIgY2hhcnRNZW5zYWw9bnVsbCxjaGFydEdydXBvcz1udWxsOwpmdW5jdGlvbiBpbml0Q2hhcnRzKCl7CiAgdmFyIG1lc2VzPUNIQVJUUy5tZXNlcy5tYXAoZnVuY3Rpb24obSl7cmV0dXJuIG0ucmVwbGFjZSgvXlxkezR9LS8sJycpO30pOwogIHZhciBDT0xPUl9MSU5FPScjM2I4MmY2JzsKICB2YXIgQ09MT1JTPVsnIzNiODJmNicsJyMwNTk2NjknLCcjZDk3NzA2JywnI2RjMjYyNicsJyM3YzNhZWQnLCcjZWE1ODBjJ107CgogIC8vIENoYXJ0IG1lbnNhbCDigJQgdG90YWwgdnMgYXRpdm9zCiAgdmFyIGN0eDE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNoYXJ0LW1lbnNhbCIpLmdldENvbnRleHQoIjJkIik7CiAgY2hhcnRNZW5zYWw9bmV3IENoYXJ0KGN0eDEsewogICAgdHlwZToibGluZSIsCiAgICBkYXRhOnsKICAgICAgbGFiZWxzOm1lc2VzLAogICAgICBkYXRhc2V0czpbCiAgICAgICAgewogICAgICAgICAgbGFiZWw6IlRvdGFsIGhpc3TDs3JpY28iLAogICAgICAgICAgZGF0YTpDSEFSVFMuZXZvbHVjYW9fdG90YWwsCiAgICAgICAgICBib3JkZXJDb2xvcjoiIzk0YTNiOCIsYmFja2dyb3VuZENvbG9yOiJyZ2JhKDE0OCwxNjMsMTg0LC4wNikiLAogICAgICAgICAgYm9yZGVyV2lkdGg6Mixwb2ludFJhZGl1czoyLHRlbnNpb246LjM1LGZpbGw6dHJ1ZSwKICAgICAgICAgIGJvcmRlckRhc2g6WzQsM10KICAgICAgICB9LAogICAgICAgIHsKICAgICAgICAgIGxhYmVsOiJFbXByZXNhcyBhdGl2YXMgaG9qZSIsCiAgICAgICAgICBkYXRhOkNIQVJUUy5ldm9sdWNhb19hdGl2b3MsCiAgICAgICAgICBib3JkZXJDb2xvcjpDT0xPUl9MSU5FLGJhY2tncm91bmRDb2xvcjoicmdiYSg1OSwxMzAsMjQ2LC4wOCkiLAogICAgICAgICAgYm9yZGVyV2lkdGg6Mi41LHBvaW50UmFkaXVzOjMscG9pbnRCYWNrZ3JvdW5kQ29sb3I6Q09MT1JfTElORSx0ZW5zaW9uOi4zNSxmaWxsOnRydWUKICAgICAgICB9CiAgICAgIF0KICAgIH0sCiAgICBvcHRpb25zOntyZXNwb25zaXZlOnRydWUsbWFpbnRhaW5Bc3BlY3RSYXRpbzpmYWxzZSwKICAgICAgcGx1Z2luczp7CiAgICAgICAgbGVnZW5kOntkaXNwbGF5OnRydWUscG9zaXRpb246ImJvdHRvbSIsbGFiZWxzOntmb250OntzaXplOjEwfSxib3hXaWR0aDoxMixwYWRkaW5nOjh9fSwKICAgICAgICB0b29sdGlwOnttb2RlOiJpbmRleCIsaW50ZXJzZWN0OmZhbHNlfQogICAgICB9LAogICAgICBzY2FsZXM6e3g6e2dyaWQ6e2Rpc3BsYXk6ZmFsc2V9LHRpY2tzOntmb250OntzaXplOjEwfX19LAogICAgICAgICAgICAgIHk6e2dyaWQ6e2NvbG9yOiJyZ2JhKDAsMCwwLC4wNCkifSx0aWNrczp7Zm9udDp7c2l6ZToxMH19fX19CiAgfSk7CgogIC8vIENoYXJ0IGdydXBvcyDigJQgYXRpdm9zIChzw7NsaWRvKSB2cyB0b3RhbCAodHJhY2VqYWRvKQogIHZhciBjdHgyPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjaGFydC1ncnVwb3MiKS5nZXRDb250ZXh0KCIyZCIpOwogIHZhciBncnVwb3NLZXlzPU9iamVjdC5rZXlzKENIQVJUUy5ncnVwb3NfYXRpdm9zKTsKICB2YXIgZHNHcnVwb3M9W107CiAgZ3J1cG9zS2V5cy5mb3JFYWNoKGZ1bmN0aW9uKGcsaSl7CiAgICB2YXIgY29yPUNPTE9SU1tpJUNPTE9SUy5sZW5ndGhdOwogICAgLy8gTGluaGEgYXRpdm9zIChzw7NsaWRhKQogICAgZHNHcnVwb3MucHVzaCh7CiAgICAgIGxhYmVsOmcsZGF0YTpDSEFSVFMuZ3J1cG9zX2F0aXZvc1tnXSwKICAgICAgYm9yZGVyQ29sb3I6Y29yLGJhY2tncm91bmRDb2xvcjoidHJhbnNwYXJlbnQiLAogICAgICBib3JkZXJXaWR0aDoyLjUscG9pbnRSYWRpdXM6Mix0ZW5zaW9uOi4zNQogICAgfSk7CiAgICAvLyBMaW5oYSB0b3RhbCAodHJhY2VqYWRhLCBtYWlzIGZpbmEpCiAgICBkc0dydXBvcy5wdXNoKHsKICAgICAgbGFiZWw6ZysiICh0b3RhbCkiLGRhdGE6Q0hBUlRTLmdydXBvc190b3RhbFtnXSwKICAgICAgYm9yZGVyQ29sb3I6Y29yLGJhY2tncm91bmRDb2xvcjoidHJhbnNwYXJlbnQiLAogICAgICBib3JkZXJXaWR0aDoxLjUscG9pbnRSYWRpdXM6MCx0ZW5zaW9uOi4zNSwKICAgICAgYm9yZGVyRGFzaDpbNCwzXSwKICAgICAgbGVnZW5kOntkaXNwbGF5OmZhbHNlfQogICAgfSk7CiAgfSk7CiAgY2hhcnRHcnVwb3M9bmV3IENoYXJ0KGN0eDIsewogICAgdHlwZToibGluZSIsCiAgICBkYXRhOntsYWJlbHM6bWVzZXMsZGF0YXNldHM6ZHNHcnVwb3N9LAogICAgb3B0aW9uczp7cmVzcG9uc2l2ZTp0cnVlLG1haW50YWluQXNwZWN0UmF0aW86ZmFsc2UsCiAgICAgIHBsdWdpbnM6ewogICAgICAgIGxlZ2VuZDp7CiAgICAgICAgICBwb3NpdGlvbjoiYm90dG9tIiwKICAgICAgICAgIGxhYmVsczp7CiAgICAgICAgICAgIGZvbnQ6e3NpemU6MTB9LGJveFdpZHRoOjEyLAogICAgICAgICAgICBmaWx0ZXI6ZnVuY3Rpb24oaXRlbSl7cmV0dXJuIGl0ZW0udGV4dC5pbmRleE9mKCIodG90YWwpIik8MDt9CiAgICAgICAgICB9CiAgICAgICAgfSwKICAgICAgICB0b29sdGlwOnsKICAgICAgICAgIG1vZGU6ImluZGV4IixpbnRlcnNlY3Q6ZmFsc2UsCiAgICAgICAgICBmaWx0ZXI6ZnVuY3Rpb24oaXRlbSl7cmV0dXJuIGl0ZW0uZGF0YXNldC5sYWJlbC5pbmRleE9mKCIodG90YWwpIik8MDt9CiAgICAgICAgfQogICAgICB9LAogICAgICBzY2FsZXM6e3g6e2dyaWQ6e2Rpc3BsYXk6ZmFsc2V9LHRpY2tzOntmb250OntzaXplOjEwfX19LAogICAgICAgICAgICAgIHk6e2dyaWQ6e2NvbG9yOiJyZ2JhKDAsMCwwLC4wNCkifSx0aWNrczp7Zm9udDp7c2l6ZToxMH19fX19CiAgfSk7CgogIC8vIFJldGVudGlvbgogIHZhciByZXRIdG1sPSI8ZGl2IGNsYXNzPVwicmV0LWdyaWRcIj4iOwogIENIQVJUUy5yZXRlbmNhby5zbGljZSgtNikuZm9yRWFjaChmdW5jdGlvbihyKXsKICAgIHZhciBjb3I9ci50YXhhPj03MD8idmFyKC0tZ3JlZW4pIjpyLnRheGE+PTUwPyJ2YXIoLS15ZWwpIjoidmFyKC0tcmVkKSI7CiAgICByZXRIdG1sKz0iPGRpdiBjbGFzcz1cInJldC1jYXJkXCI+PGRpdiBjbGFzcz1cInJldC1wY3RcIiBzdHlsZT1cImNvbG9yOiIrY29yKyJcIj4iK3IudGF4YSsiJTwvZGl2PiIrCiAgICAgICI8ZGl2IGNsYXNzPVwicmV0LW1lc1wiPiIrci5tZXMucmVwbGFjZSgvXlxkezR9LS8sIiIpKyI8L2Rpdj4iKwogICAgICAiPGRpdiBjbGFzcz1cInJldC1zdWJcIj4iK3IucmV0aWRvcysiLyIrci5iYXNlKyI8L2Rpdj48L2Rpdj4iOwogIH0pOwogIHJldEh0bWwrPSI8L2Rpdj4iOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJyZXQtYm9keSIpLmlubmVySFRNTD1yZXRIdG1sOwoKICAvLyBSYW5raW5nCiAgdmFyIG1heEF1bGFzPUNIQVJUUy5yYW5raW5nWzBdWzFdOwogIHZhciByYW5rSHRtbD0iIjsKICBDSEFSVFMucmFua2luZy5zbGljZSgwLDEyKS5mb3JFYWNoKGZ1bmN0aW9uKHIsaSl7CiAgICB2YXIgdz1NYXRoLnJvdW5kKHJbMV0vbWF4QXVsYXMqMTAwKTsKICAgIHJhbmtIdG1sKz0iPGRpdiBjbGFzcz1cInJhbmstcm93XCI+PHNwYW4gY2xhc3M9XCJyYW5rLW51bVwiPiIrKGkrMSkrIjwvc3Bhbj4iKwogICAgICAiPHNwYW4gY2xhc3M9XCJyYW5rLW5hbWVcIj4iK3JbMF0rIjwvc3Bhbj4iKwogICAgICAiPGRpdiBjbGFzcz1cInJhbmstYmFyLXdyYXBcIj48ZGl2IGNsYXNzPVwicmFuay1iYXItZmlsbFwiIHN0eWxlPVwid2lkdGg6Iit3KyIlXCI+PC9kaXY+PC9kaXY+IisKICAgICAgIjxzcGFuIGNsYXNzPVwicmFuay12YWxcIj4iK3JbMV0rIjwvc3Bhbj48L2Rpdj4iOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJyYW5rLWJvZHkiKS5pbm5lckhUTUw9cmFua0h0bWw7CgogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1jaGFydHMiKS5zdHlsZS5kaXNwbGF5PSJibG9jayI7Cn0KCmZ1bmN0aW9uIHVwZGF0ZUNoYXJ0TWVuc2FsKGdydXBvKXsKICBpZighY2hhcnRNZW5zYWwpcmV0dXJuOwogIGlmKCFncnVwbyl7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzBdLmRhdGE9Q0hBUlRTLmV2b2x1Y2FvX3RvdGFsOwogICAgY2hhcnRNZW5zYWwuZGF0YS5kYXRhc2V0c1swXS5sYWJlbD0iVG90YWwgaGlzdMOzcmljbyI7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzFdLmRhdGE9Q0hBUlRTLmV2b2x1Y2FvX2F0aXZvczsKICAgIGNoYXJ0TWVuc2FsLmRhdGEuZGF0YXNldHNbMV0ubGFiZWw9IkVtcHJlc2FzIGF0aXZhcyBob2plIjsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJncnVwby1zZWwtbGJsIikudGV4dENvbnRlbnQ9IiI7CiAgfWVsc2V7CiAgICB2YXIgdG90PUNIQVJUUy5ncnVwb3NfdG90YWxbZ3J1cG9dfHxbXTsKICAgIHZhciBhdHY9Q0hBUlRTLmdydXBvc19hdGl2b3NbZ3J1cG9dfHxbXTsKICAgIGNoYXJ0TWVuc2FsLmRhdGEuZGF0YXNldHNbMF0uZGF0YT10b3Q7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzBdLmxhYmVsPWdydXBvKyIgKHRvdGFsKSI7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzFdLmRhdGE9YXR2OwogICAgY2hhcnRNZW5zYWwuZGF0YS5kYXRhc2V0c1sxXS5sYWJlbD1ncnVwbysiIChhdGl2YXMpIjsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJncnVwby1zZWwtbGJsIikudGV4dENvbnRlbnQ9IuKAlCAiK2dydXBvOwogIH0KICBjaGFydE1lbnNhbC51cGRhdGUoKTsKfQoKLy8gSG9vayBncnVwbyBmaWx0ZXIgaW50byBjaGFydApkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtZ3J1cG8iKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLGZ1bmN0aW9uKCl7CiAgdXBkYXRlQ2hhcnRNZW5zYWwodGhpcy52YWx1ZSk7Cn0pOwoKc2V0VGltZW91dChpbml0Q2hhcnRzLDEwMCk7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY28iKS52YWx1ZT0iIjsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY3NtIikudmFsdWU9IiI7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWdydXBvIikudmFsdWU9IiI7CiAgZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLm92LWNyIikuZm9yRWFjaChmdW5jdGlvbihjKXtjLmNoZWNrZWQ9ZmFsc2U7fSk7CiAgdXBkYXRlQ2hhcnRNZW5zYWwoIiIpOwogIG92Rj1udWxsO3J1bk92KCk7Cn0pOwp2YXIgc2VsQ289bnVsbDsKZnVuY3Rpb24gcnVuRW0oKXsKICB2YXIgcT1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tcSIpLnZhbHVlLnRvTG93ZXJDYXNlKCksY3NtPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJlbS1jc20iKS52YWx1ZTsKICB2YXIgZmQ9Qy5maWx0ZXIoZnVuY3Rpb24oYyl7aWYocSYmYy5lbXByZXNhLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwKXJldHVybiBmYWxzZTtpZihjc20mJmMuY3NtIT09Y3NtKXJldHVybiBmYWxzZTtyZXR1cm4gdHJ1ZTt9KTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tY3RhZyIpLnRleHRDb250ZW50PWZkLmxlbmd0aCsiIGVtcHJlc2FzIjsKICB2YXIgY2FyZHM9ZmQubWFwKGZ1bmN0aW9uKGNvLGlkeCl7CiAgICB2YXIgcD1wY3QoY28uYWN0aXZlX20sY28udG90YWwpOwogICAgdmFyIGZjPXA+PTcwPyJ2YXIoLS1ncmVlbikiOnA+PTQwPyJ2YXIoLS15ZWwpIjoidmFyKC0tcmVkKSI7CiAgICB2YXIgcGMyPXA+PTcwPyJwLWciOnA+PTQwPyJwLXkiOiJwLXIiOwogICAgdmFyIGlzU2VsPShzZWxDbz09PWlkeCk/IiBzZWwiOiIiOwogICAgcmV0dXJuICc8ZGl2IGNsYXNzPSJjb2NhcmQnK2lzU2VsKyciIGRhdGEtZW1wPSInK2VzYyhjby5lbXByZXNhKSsnIiBkYXRhLWlkeD0iJytpZHgrJyI+JysKICAgICAgJzxkaXYgY2xhc3M9ImNvLXRvcCI+PGRpdj48ZGl2IGNsYXNzPSJjby1uYW1lIj4nK2VzYyhjby5lbXByZXNhKSsnPC9kaXY+PGRpdiBjbGFzcz0iY28tY3NtIj4nK2VzYyhjby5jc218fCJTZW0gQ1NNIikrJzwvZGl2PjwvZGl2PicrCiAgICAgICc8c3BhbiBjbGFzcz0icGlsbCAnK3BjMisnIj4nK3ArJyU8L3NwYW4+PC9kaXY+JysKICAgICAgJzxkaXYgY2xhc3M9ImNvLWJhciI+PGRpdiBjbGFzcz0iY28tYmYiIHN0eWxlPSJ3aWR0aDonK3ArJyU7YmFja2dyb3VuZDonK2ZjKyciPjwvZGl2PjwvZGl2PicrCiAgICAgICc8ZGl2IGNsYXNzPSJjby1zdGF0cyI+JysKICAgICAgICAnPHNwYW4gY2xhc3M9ImNvcyI+PHNwYW4gY2xhc3M9ImRvdCBkLW8iPjwvc3Bhbj4nK2NvLm9mZmVuc2l2ZSsnPC9zcGFuPicrCiAgICAgICAgJzxzcGFuIGNsYXNzPSJjb3MiPjxzcGFuIGNsYXNzPSJkb3QgZC1nIj48L3NwYW4+Jytjby5ncmVlbisnPC9zcGFuPicrCiAgICAgICAgJzxzcGFuIGNsYXNzPSJjb3MiPjxzcGFuIGNsYXNzPSJkb3QgZC15Ij48L3NwYW4+Jytjby55ZWxsb3crJzwvc3Bhbj4nKwogICAgICAgICc8c3BhbiBjbGFzcz0iY29zIj48c3BhbiBjbGFzcz0iZG90IGQtciI+PC9zcGFuPicrY28ucmVkKyc8L3NwYW4+JysKICAgICAgICAnPHNwYW4gY2xhc3M9ImNvcyI+PHNwYW4gY2xhc3M9ImRvdCBkLWsiPjwvc3Bhbj4nK2NvLmJsYWNrKyc8L3NwYW4+JysKICAgICAgICAnPHNwYW4gc3R5bGU9ImZvbnQtc2l6ZToxMHB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi1sZWZ0OmF1dG87Ij4nK2NvLnRvdGFsKycgdXN1XHhFMXJpb3M8L3NwYW4+JysKICAgICAgJzwvZGl2PjwvZGl2Pic7CiAgfSkuam9pbignJyk7CiAgdmFyIGRldD0nJzsKICBpZihzZWxDbyE9PW51bGwmJnNlbENvPGZkLmxlbmd0aCl7CiAgICB2YXIgc2VsRW1wcmVzYT1mZFtzZWxDb10uZW1wcmVzYTsKICAgIHZhciBjdT1VLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5jb21wYW55PT09c2VsRW1wcmVzYXx8dS5jb21wYW55LnRvTG93ZXJDYXNlKCk9PT1zZWxFbXByZXNhLnRvTG93ZXJDYXNlKCk7fSk7CiAgICB2YXIgcm93cz1jdS5tYXAoZnVuY3Rpb24odSl7CiAgICAgIHJldHVybiAnPHRyPjx0ZD48ZGl2IHN0eWxlPSJmb250LXdlaWdodDo2MDA7Ij4nK2VzYyh1Lm5hbWUpKyc8L2Rpdj48ZGl2IHN0eWxlPSJmb250LXNpemU6MTFweDtjb2xvcjp2YXIoLS1nNDAwKTsiPicrZXNjKHUuZW1haWwpKyc8L2Rpdj48L3RkPicrCiAgICAgICAgJzx0ZD4nK2ZQaWxsKHUuZmxhZykrJzwvdGQ+PHRkPicrKHUuZGF5c19pbmFjdGl2ZT49OTAwMD8iXHUyMDE0Ijp1LmRheXNfaW5hY3RpdmUrImQiKSsnPC90ZD4nKwogICAgICAgICc8dGQ+Jytlc2ModS5sYXN0X2NvbnN1bWVkfHwiXHUyMDE0IikrJzwvdGQ+PHRkPicrdS50b3RhbF9jb25zdW1lZCsnPC90ZD48dGQ+Jytlc2ModS5jcmVhdGVkX2F0fHwiXHUyMDE0IikrJzwvdGQ+PC90cj4nOwogICAgfSkuam9pbignJyk7CiAgICBkZXQ9JzxkaXYgY2xhc3M9ImRldCI+PGRpdiBjbGFzcz0iZGV0LXR0bCI+PHNwYW4+Jytlc2Moc2VsRW1wcmVzYSkrJyBcdTIwMTQgJytjdS5sZW5ndGgrJyB1c3VceEUxcmlvczwvc3Bhbj4nKwogICAgICAnPHNwYW4gY2xhc3M9ImNscyIgb25jbGljaz0ic2VsQ289bnVsbDtydW5FbSgpIj4mIzEwMDA1Ozwvc3Bhbj48L2Rpdj4nKwogICAgICAnPGRpdiBjbGFzcz0idHNjciI+PHRhYmxlPjx0aGVhZD48dHI+PHRoPlVzdVx4RTFyaW88L3RoPjx0aD5GbGFnPC90aD48dGg+SW5hdGl2byBoXHhFMTwvdGg+PHRoPlx4REFsdGltbyBjb25zdW1vPC90aD48dGg+VG90YWwgYXVsYXM8L3RoPjx0aD5DcmlhZG8gZW08L3RoPjwvdHI+PC90aGVhZD4nKwogICAgICAnPHRib2R5Picrcm93cysnPC90Ym9keT48L3RhYmxlPjwvZGl2PjwvZGl2Pic7CiAgfQogICAgdmFyIF9lbWI9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLWJvZHkiKTsKICBfZW1iLmlubmVySFRNTD0nPGRpdiBjbGFzcz0ic2VjIj4nK2ZkLmxlbmd0aCsnIEVtcHJlc2FzPC9kaXY+JytkZXQrJzxkaXYgY2xhc3M9ImNvZ3JpZCIgaWQ9ImNvZ3JpZCI+JytjYXJkcysnPC9kaXY+JzsKICB2YXIgX2NnPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjb2dyaWQiKTsKICBpZihfY2cpe19jZy5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oZXYpewogICAgdmFyIGNhcmQ9ZXYudGFyZ2V0LmNsb3Nlc3Q/ZXYudGFyZ2V0LmNsb3Nlc3QoIi5jb2NhcmQiKTpudWxsOwogICAgaWYoIWNhcmQpcmV0dXJuOwogICAgdmFyIGk9cGFyc2VJbnQoY2FyZC5nZXRBdHRyaWJ1dGUoImRhdGEtaWR4IiksMTApOwogICAgc2VsQ289KHNlbENvPT09aSk/bnVsbDppOwogICAgcnVuRW0oKTsKICB9KTt9Cn0KZnVuY3Rpb24gcGlja0NvKGkpe3NlbENvPShzZWxDbz09PWkpP251bGw6aTtydW5FbSgpO30KZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLXEiKS5hZGRFdmVudExpc3RlbmVyKCJpbnB1dCIscnVuRW0pOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tY3NtIikuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5FbSk7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJlbS1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tcSIpLnZhbHVlPSIiO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJlbS1jc20iKS52YWx1ZT0iIjtzZWxDbz1udWxsO3J1bkVtKCk7fSk7CmZ1bmN0aW9uIHJ1blVzKCl7CiAgdmFyIHE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLXEiKS52YWx1ZS50b0xvd2VyQ2FzZSgpOwogIHZhciBjbz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtY28iKS52YWx1ZSxjc209ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLWNzbSIpLnZhbHVlOwogIHZhciBmbD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtZmwiKS52YWx1ZSxjcj1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtY3IiKS52YWx1ZTsKICB2YXIgZmQ9VS5maWx0ZXIoZnVuY3Rpb24odSl7CiAgICBpZihxJiZ1Lm5hbWUudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDAmJnUuZW1haWwudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDApcmV0dXJuIGZhbHNlOwogICAgaWYoY28mJnUuY29tcGFueSE9PWNvKXJldHVybiBmYWxzZTtpZihjc20mJnUuY3NtIT09Y3NtKXJldHVybiBmYWxzZTsKICAgIGlmKGZsJiZ1LmZsYWchPT1mbClyZXR1cm4gZmFsc2U7CiAgICBpZihjcil7dmFyIG09bVNpbmNlKHUuY3JlYXRlZF9hdCk7aWYoY3I9PT0ibHQzIiYmbT49MylyZXR1cm4gZmFsc2U7aWYoY3I9PT0iM3RvNiImJihtPDN8fG0+NikpcmV0dXJuIGZhbHNlO2lmKGNyPT09Imd0NiImJm08PTYpcmV0dXJuIGZhbHNlO30KICAgIHJldHVybiB0cnVlOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1jdGFnIikudGV4dENvbnRlbnQ9ZmQubGVuZ3RoKyIgdXN1XHhFMXJpb3MiOwogIHZhciByb3dzPWZkLnNsaWNlKDAsNTAwKS5tYXAoZnVuY3Rpb24odSl7CiAgICByZXR1cm4gJzx0cj48dGQ+PGRpdiBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2ModS5uYW1lKSsnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij4nK2VzYyh1LmVtYWlsKSsnPC9kaXY+PC90ZD4nKwogICAgICAnPHRkPicrZXNjKHUuY29tcGFueSkrJzwvdGQ+PHRkPicrZXNjKHUuY3NtfHwiXHUyMDE0IikrJzwvdGQ+PHRkPicrZlBpbGwodS5mbGFnKSsnPC90ZD4nKwogICAgICAnPHRkPicrKHUuZGF5c19pbmFjdGl2ZT49OTAwMD8iXHUyMDE0Ijp1LmRheXNfaW5hY3RpdmUrIiBkaWFzIikrJzwvdGQ+JysKICAgICAgJzx0ZD4nK2VzYyh1Lmxhc3RfY29uc3VtZWR8fCJcdTIwMTQiKSsnPC90ZD48dGQ+Jyt1LnRvdGFsX2NvbnN1bWVkKyc8L3RkPjx0ZD4nK2VzYyh1LmNyZWF0ZWRfYXR8fCJcdTIwMTQiKSsnPC90ZD48L3RyPic7CiAgfSkuam9pbignJyk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLWJvZHkiKS5pbm5lckhUTUw9CiAgICAnPGRpdiBjbGFzcz0idHdyYXAiPjxkaXYgY2xhc3M9InRoZHIiPjxkaXYgY2xhc3M9InR0bCI+TGlzdGEgZGUgVXN1XHhFMXJpb3M8L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9InRjbnQiPicrKGZkLmxlbmd0aD41MDA/IjUwMCBkZSAiK2ZkLmxlbmd0aCsiIFx1MjAxNCBmaWx0cmUgcGFyYSB2ZXIgbWFpcyI6ZmQubGVuZ3RoKyIgdXN1XHhFMXJpb3MiKSsnPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0c2NyIj48dGFibGU+PHRoZWFkPjx0cj48dGg+VXN1XHhFMXJpbzwvdGg+PHRoPkVtcHJlc2E8L3RoPjx0aD5DU008L3RoPjx0aD5GbGFnPC90aD48dGg+SW5hdGl2byBoXHhFMTwvdGg+PHRoPlx4REFsdGltbyBjb25zdW1vPC90aD48dGg+VG90YWwgYXVsYXM8L3RoPjx0aD5DcmlhZG8gZW08L3RoPjwvdHI+PC90aGVhZD4nKwogICAgJzx0Ym9keT4nK3Jvd3MrJzwvdGJvZHk+PC90YWJsZT48L2Rpdj48L2Rpdj4nOwp9CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1xIikuYWRkRXZlbnRMaXN0ZW5lcigiaW5wdXQiLHJ1blVzKTsKWyJ1cy1jbyIsInVzLWNzbSIsInVzLWZsIiwidXMtY3IiXS5mb3JFYWNoKGZ1bmN0aW9uKGlkKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5Vcyk7fSk7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtcSIpLnZhbHVlPSIiO1sidXMtY28iLCJ1cy1jc20iLCJ1cy1mbCIsInVzLWNyIl0uZm9yRWFjaChmdW5jdGlvbihpZCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpLnZhbHVlPSIiO30pO3J1blVzKCk7fSk7CmZ1bmN0aW9uIHJ1bk5hKCl7CiAgdmFyIHE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5hLXEiKS52YWx1ZS50b0xvd2VyQ2FzZSgpOwogIHZhciBjbz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmEtY28iKS52YWx1ZSxjc209ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5hLWNzbSIpLnZhbHVlOwogIHZhciBmZD1OVi5maWx0ZXIoZnVuY3Rpb24odSl7CiAgICBpZihxJiZ1Lm5hbWUudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDAmJnUuZW1haWwudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDApcmV0dXJuIGZhbHNlOwogICAgaWYoY28mJnUuY29tcGFueSE9PWNvKXJldHVybiBmYWxzZTtpZihjc20mJnUuY3NtIT09Y3NtKXJldHVybiBmYWxzZTtyZXR1cm4gdHJ1ZTsKICB9KTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmEtY3RhZyIpLnRleHRDb250ZW50PWZkLmxlbmd0aCsiIHVzdVx4RTFyaW9zIjsKICB2YXIga3Bpcz0nPGRpdiBjbGFzcz0ia3JvdyBrMyIgc3R5bGU9Im1hcmdpbi1ib3R0b206MTZweDsiPicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5OdW5jYSBhc3Npc3RpcmFtPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLXkiPicrZmQubGVuZ3RoKyc8L2Rpdj48ZGl2IGNsYXNzPSJrc3ViIj51c3VceEUxcmlvcyBjYWRhc3RyYWRvczwvZGl2PjwvZGl2PicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5FbXByZXNhcyBhZmV0YWRhczwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1iIj4nK1suLi5uZXcgU2V0KGZkLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jb21wYW55O30pKV0ubGVuZ3RoKyc8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+Q1NNcyBlbnZvbHZpZG9zPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLWsiPicrWy4uLm5ldyBTZXQoZmQubWFwKGZ1bmN0aW9uKHUpe3JldHVybiB1LmNzbTt9KS5maWx0ZXIoQm9vbGVhbikpXS5sZW5ndGgrJzwvZGl2PjwvZGl2PicrCiAgJzwvZGl2Pic7CiAgdmFyIHJvd3M9ZmQuc2xpY2UoMCw1MDApLm1hcChmdW5jdGlvbih1KXsKICAgIHJldHVybiAnPHRyPjx0ZD48ZGl2IHN0eWxlPSJmb250LXdlaWdodDo2MDA7Ij4nK2VzYyh1Lm5hbWUpKyc8L2Rpdj48ZGl2IHN0eWxlPSJmb250LXNpemU6MTFweDtjb2xvcjp2YXIoLS1nNDAwKTsiPicrZXNjKHUuZW1haWwpKyc8L2Rpdj48L3RkPicrCiAgICAgICc8dGQ+Jytlc2ModS5jb21wYW55KSsnPC90ZD48dGQ+Jytlc2ModS5jc218fCJcdTIwMTQiKSsnPC90ZD48dGQ+Jytlc2ModS5jcmVhdGVkX2F0fHwiXHUyMDE0IikrJzwvdGQ+PC90cj4nOwogIH0pLmpvaW4oJycpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1ib2R5IikuaW5uZXJIVE1MPWtwaXMrCiAgICAnPGRpdiBjbGFzcz0idHdyYXAiPjxkaXYgY2xhc3M9InRoZHIiPjxkaXYgY2xhc3M9InR0bCI+Q2FkYXN0cmFkb3MgcXVlIG51bmNhIGFzc2lzdGlyYW08L2Rpdj48ZGl2IGNsYXNzPSJ0Y250Ij4nK2ZkLmxlbmd0aCsnIHVzdVx4RTFyaW9zPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0c2NyIj48dGFibGU+PHRoZWFkPjx0cj48dGg+VXN1XHhFMXJpbzwvdGg+PHRoPkVtcHJlc2E8L3RoPjx0aD5DU008L3RoPjx0aD5DcmlhZG8gZW08L3RoPjwvdHI+PC90aGVhZD4nKwogICAgJzx0Ym9keT4nK3Jvd3MrJzwvdGJvZHk+PC90YWJsZT48L2Rpdj48L2Rpdj4nOwp9CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1xIikuYWRkRXZlbnRMaXN0ZW5lcigiaW5wdXQiLHJ1bk5hKTsKWyJuYS1jbyIsIm5hLWNzbSJdLmZvckVhY2goZnVuY3Rpb24oaWQpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKGlkKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk5hKTt9KTsKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5hLXJzdCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIixmdW5jdGlvbigpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1xIikudmFsdWU9IiI7WyJuYS1jbyIsIm5hLWNzbSJdLmZvckVhY2goZnVuY3Rpb24oaWQpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKGlkKS52YWx1ZT0iIjt9KTtydW5OYSgpO30pOwpmdW5jdGlvbiBydW5OZigpewogIHZhciBxPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1xIikudmFsdWUudG9Mb3dlckNhc2UoKTsKICB2YXIgY29ucz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtY29ucyIpLnZhbHVlOwogIHZhciBmZD1ORi5maWx0ZXIoZnVuY3Rpb24oYyl7CiAgICBpZihxJiZjLmVtcHJlc2EudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDApcmV0dXJuIGZhbHNlOwogICAgaWYoY29ucz09PSJzaW0iJiYhYy50ZXZlX2NvbnN1bW8pcmV0dXJuIGZhbHNlOwogICAgaWYoY29ucz09PSJuYW8iJiZjLnRldmVfY29uc3VtbylyZXR1cm4gZmFsc2U7CiAgICByZXR1cm4gdHJ1ZTsKICB9KTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtY3RhZyIpLnRleHRDb250ZW50PWZkLmxlbmd0aCsiIGVtcHJlc2FzIjsKICB2YXIga3Bpcz0nPGRpdiBjbGFzcz0ia3JvdyBrMyIgc3R5bGU9Im1hcmdpbi1ib3R0b206MTZweDsiPicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5Ub3RhbCBlbXByZXNhczwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1wIj4nK2ZkLmxlbmd0aCsnPC9kaXY+PGRpdiBjbGFzcz0ia3N1YiI+blx4RTNvIGVuY29udHJhZGFzIGNvbW8gYXRpdmFzPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJrcGkiPjxkaXYgY2xhc3M9ImtsYmwiPkNvbSBjb25zdW1vIGRlIGF1bGFzPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLW8iPicrZmQuZmlsdGVyKGZ1bmN0aW9uKGMpe3JldHVybiBjLnRldmVfY29uc3Vtbzt9KS5sZW5ndGgrJzwvZGl2PjwvZGl2PicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5Vc3VceEUxcmlvcyBuZXN0YXMgZW1wcmVzYXM8L2Rpdj48ZGl2IGNsYXNzPSJrdmFsIGMtYiI+JytmZC5yZWR1Y2UoZnVuY3Rpb24oYSxjKXtyZXR1cm4gYStjLnRvdGFsO30sMCkrJzwvZGl2PjwvZGl2PicrCiAgJzwvZGl2Pic7CiAgdmFyIHJvd3M9ZmQubWFwKGZ1bmN0aW9uKGMpewogICAgcmV0dXJuICc8dHI+PHRkIHN0eWxlPSJmb250LXdlaWdodDo2MDA7Ij4nK2VzYyhjLmVtcHJlc2EpKyc8L3RkPicrCiAgICAgICc8dGQgc3R5bGU9ImZvbnQtd2VpZ2h0OjcwMDt0ZXh0LWFsaWduOmNlbnRlcjsiPicrYy50b3RhbCsnPC90ZD4nKwogICAgICAnPHRkPicrKGMudGV2ZV9jb25zdW1vPyc8c3BhbiBjbGFzcz0icGlsbCBwLWciPiYjMTAwMDM7IFNpbTwvc3Bhbj4nOic8c3BhbiBjbGFzcz0icGlsbCBwLWdyIj5OXHhFM288L3NwYW4+JykrJzwvdGQ+PC90cj4nOwogIH0pLmpvaW4oJycpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1ib2R5IikuaW5uZXJIVE1MPWtwaXMrCiAgICAnPGRpdiBjbGFzcz0iaWJveCBpYm94LXAiPiYjMTAwNjc7IEVtcHJlc2FzIGNvbSB1c3VceEUxcmlvcyBjYWRhc3RyYWRvcyBxdWUgblx4RTNvIGVzdFx4RTNvIG5hIGJhc2UgZGUgY2xpZW50ZXMgY29tbyA8c3Ryb25nPkF0aXZhczwvc3Ryb25nPi4gTWFwZWllIGUgY2FkYXN0cmUgYXMgcXVlIGZvcmVtIGNsaWVudGVzIGF0aXZvcy48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9InR3cmFwIj48ZGl2IGNsYXNzPSJ0aGRyIj48ZGl2IGNsYXNzPSJ0dGwiPkVtcHJlc2FzIG5ceEUzbyBtYXBlYWRhczwvZGl2PjxkaXYgY2xhc3M9InRjbnQiPicrZmQubGVuZ3RoKycgZW1wcmVzYXM8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9InRzY3IiPjx0YWJsZT48dGhlYWQ+PHRyPjx0aD5FbXByZXNhPC90aD48dGg+VXN1XHhFMXJpb3M8L3RoPjx0aD5Db25zdW1pdSBhdWxhcz88L3RoPjwvdHI+PC90aGVhZD4nKwogICAgJzx0Ym9keT4nK3Jvd3MrJzwvdGJvZHk+PC90YWJsZT48L2Rpdj48L2Rpdj4nOwp9CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1xIikuYWRkRXZlbnRMaXN0ZW5lcigiaW5wdXQiLHJ1bk5mKTsKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5mLWNvbnMiKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk5mKTsKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5mLXJzdCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIixmdW5jdGlvbigpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1xIikudmFsdWU9IiI7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5mLWNvbnMiKS52YWx1ZT0iIjtydW5OZigpO30pOwpmdW5jdGlvbiBydW5PcigpewogIHZhciBxPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvci1xIikudmFsdWUudG9Mb3dlckNhc2UoKSxzdD1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3Itc3QiKS52YWx1ZTsKICB2YXIgc2l4QWdvPW5ldyBEYXRlKCk7c2l4QWdvLnNldE1vbnRoKHNpeEFnby5nZXRNb250aCgpLTYpOwogIHZhciBmZD1PUi5maWx0ZXIoZnVuY3Rpb24odSl7CiAgICBpZih1LmNvX3N0YXR1cz09PSJDaHVybiIpe3ZhciByZWNlbnQ9dS5sYXN0X2NvbnN1bWVkJiZuZXcgRGF0ZSh1Lmxhc3RfY29uc3VtZWQpPj1zaXhBZ287aWYoIXJlY2VudClyZXR1cm4gZmFsc2U7fQogICAgaWYocSYmdS5uYW1lLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwJiZ1LmVtYWlsLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwJiZ1LmNvbXBhbnkudG9Mb3dlckNhc2UoKS5pbmRleE9mKHEpPDApcmV0dXJuIGZhbHNlOwogICAgaWYoc3QmJnUuY29fc3RhdHVzIT09c3QpcmV0dXJuIGZhbHNlO3JldHVybiB0cnVlOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvci1jdGFnIikudGV4dENvbnRlbnQ9ZmQubGVuZ3RoKyIgdXN1XHhFMXJpb3MiOwogIHZhciBrcGlzPSc8ZGl2IGNsYXNzPSJrcm93IGsyIiBzdHlsZT0ibWFyZ2luLWJvdHRvbToxNnB4OyI+JysKICAgICc8ZGl2IGNsYXNzPSJrcGkiPjxkaXYgY2xhc3M9ImtsYmwiPlVzdVx4RTFyaW9zIGZvcmEgZG8gZGFzaGJvYXJkPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLXAiPicrZmQubGVuZ3RoKyc8L2Rpdj48ZGl2IGNsYXNzPSJrc3ViIj5lbXByZXNhIG5ceEUzbyBlc3RceEUxIGF0aXZhIG5hIGJhc2U8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+RW1wcmVzYXMgZGlzdGludGFzPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLWIiPicrWy4uLm5ldyBTZXQoZmQubWFwKGZ1bmN0aW9uKHUpe3JldHVybiB1LmNvbXBhbnk7fSkpXS5sZW5ndGgrJzwvZGl2PjwvZGl2PicrCiAgJzwvZGl2Pic7CiAgdmFyIHJvd3M9ZmQuc2xpY2UoMCw1MDApLm1hcChmdW5jdGlvbih1KXsKICAgIHJldHVybiAnPHRyPjx0ZD48ZGl2IHN0eWxlPSJmb250LXdlaWdodDo2MDA7Ij4nK2VzYyh1Lm5hbWUpKyc8L2Rpdj48ZGl2IHN0eWxlPSJmb250LXNpemU6MTFweDtjb2xvcjp2YXIoLS1nNDAwKTsiPicrZXNjKHUuZW1haWwpKyc8L2Rpdj48L3RkPicrCiAgICAgICc8dGQ+Jytlc2ModS5jb21wYW55KSsnPC90ZD48dGQ+JytzdFBpbGwodS5jb19zdGF0dXMpKyc8L3RkPicrCiAgICAgICc8dGQ+JysodS50b3RhbF9jb25zdW1lZD4wPyc8c3BhbiBjbGFzcz0icGlsbCBwLWciPiYjMTAwMDM7IFNpbSAoJyt1LnRvdGFsX2NvbnN1bWVkKycpPC9zcGFuPic6JzxzcGFuIGNsYXNzPSJwaWxsIHAtZ3IiPk5ceEUzbzwvc3Bhbj4nKSsnPC90ZD48L3RyPic7CiAgfSkuam9pbignJyk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLWJvZHkiKS5pbm5lckhUTUw9a3BpcysKICAgICc8ZGl2IGNsYXNzPSJpYm94IGlib3gteSI+JiM5ODg4OyYjNjUwMzk7IFVzdVx4RTFyaW9zIHF1ZSBjb25zdW1pcmFtIGF1bGFzIG5vcyBceEZBbHRpbW9zIDMgbWVzZXMgbWFzIGN1amEgZW1wcmVzYSBuXHhFM28gZXN0XHhFMSBhdGl2YSBuYSBiYXNlLiBDb3JyaWphIG8gc3RhdHVzIG91IGFkaWNpb25lIHVtIGFsaWFzIG5vIHNjcmlwdC48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9InR3cmFwIj48ZGl2IGNsYXNzPSJ0aGRyIj48ZGl2IGNsYXNzPSJ0dGwiPlVzdVx4RTFyaW9zIGZvcmEgZG8gZGFzaGJvYXJkIHByaW5jaXBhbDwvZGl2PjxkaXYgY2xhc3M9InRjbnQiPicrKGZkLmxlbmd0aD41MDA/IjUwMCBkZSAiK2ZkLmxlbmd0aDpmZC5sZW5ndGgrIiB1c3VceEUxcmlvcyIpKyc8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9InRzY3IiPjx0YWJsZT48dGhlYWQ+PHRyPjx0aD5Vc3VceEUxcmlvPC90aD48dGg+RW1wcmVzYTwvdGg+PHRoPlN0YXR1cyBlbXByZXNhPC90aD48dGg+Q29uc3VtaXUgYXVsYXM/PC90aD48L3RyPjwvdGhlYWQ+JysKICAgICc8dGJvZHk+Jytyb3dzKyc8L3Rib2R5PjwvdGFibGU+PC9kaXY+PC9kaXY+JzsKfQpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3ItcSIpLmFkZEV2ZW50TGlzdGVuZXIoImlucHV0IixydW5Pcik7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvci1zdCIpLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIscnVuT3IpOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3ItcnN0IikuYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLGZ1bmN0aW9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLXEiKS52YWx1ZT0iIjtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3Itc3QiKS52YWx1ZT0iIjtydW5PcigpO30pOwpydW5PdigpO3J1bkVtKCk7cnVuVXMoKTtydW5OYSgpO3J1bk5mKCk7cnVuT3IoKTsK").decode('utf-8')

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
