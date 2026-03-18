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
    CSS      = _b64.b64decode("Cjpyb290ey0tbmF2eTojMGYyOTUyOy0tbWlkOiMyNTYzYjA7LS1za3k6IzNiODJmNjstLXNreS1sOiNlZmY2ZmY7LS1za3ktcDojZjhmYWZmOy0tZzUwOiNmOWZhZmI7LS1nMTAwOiNmMWY1Zjk7LS1nMjAwOiNlMmU4ZjA7LS1nNDAwOiM5NGEzYjg7LS1nNTAwOiM2NDc0OGI7LS1nNjAwOiM0NzU1Njk7LS1nNzAwOiMzMzQxNTU7LS1nODAwOiMxZTI5M2I7LS1ncmVlbjojMDU5NjY5Oy0tZ2w6I2VjZmRmNTstLWdiOiM2ZWU3Yjc7LS15ZWw6I2Q5NzcwNjstLXlsOiNmZmZiZWI7LS15YjojZmNkMzRkOy0tcmVkOiNkYzI2MjY7LS1ybDojZmVmMmYyOy0tcmI6I2ZjYTVhNTstLWJsazojMzM0MTU1Oy0tYmtsOiNmOGZhZmM7LS1ia2I6Izk0YTNiODstLW9yYTojZWE1ODBjOy0tb2w6I2ZmZjdlZDstLW9iOiNmZGJhNzQ7LS1wdXI6IzdjM2FlZDstLXBsOiNmNWYzZmY7LS1wYjojYzRiNWZkOy0tcjoxMnB4Oy0tc2g6MCAxcHggM3B4IHJnYmEoMTUsNDEsODIsLjA3KSwwIDFweCAycHggcmdiYSgxNSw0MSw4MiwuMDQpO30KKntib3gtc2l6aW5nOmJvcmRlci1ib3g7bWFyZ2luOjA7cGFkZGluZzowO30KYm9keXtmb250LWZhbWlseToiUGx1cyBKYWthcnRhIFNhbnMiLHNhbnMtc2VyaWY7YmFja2dyb3VuZDp2YXIoLS1nNTApO2NvbG9yOnZhcigtLWc4MDApO21pbi1oZWlnaHQ6MTAwdmg7Zm9udC1zaXplOjE0cHg7fQouaGRye2JhY2tncm91bmQ6dmFyKC0tbmF2eSk7aGVpZ2h0OjU2cHg7cGFkZGluZzowIDI0cHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2Vlbjtwb3NpdGlvbjpzdGlja3k7dG9wOjA7ei1pbmRleDo0MDA7Ym94LXNoYWRvdzowIDJweCAxMHB4IHJnYmEoMTUsNDEsODIsLjIpO30KLmJyYW5ke2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7Z2FwOjEwcHg7fS5iaWNve3dpZHRoOjMwcHg7aGVpZ2h0OjMwcHg7YmFja2dyb3VuZDp2YXIoLS1za3kpO2JvcmRlci1yYWRpdXM6N3B4O2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7anVzdGlmeS1jb250ZW50OmNlbnRlcjtmb250LXNpemU6MTJweDtmb250LXdlaWdodDo4MDA7Y29sb3I6I2ZmZjt9LmJuYW1le2ZvbnQtc2l6ZToxNnB4O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjojZmZmO30uYnRhZ3tmb250LXNpemU6MTFweDtjb2xvcjpyZ2JhKDI1NSwyNTUsMjU1LC40KTttYXJnaW4tdG9wOjFweDt9LnVwZHtmb250LXNpemU6MTFweDtjb2xvcjpyZ2JhKDI1NSwyNTUsMjU1LC4zNSk7fQoubmF2e2JhY2tncm91bmQ6I2ZmZjtib3JkZXItYm90dG9tOjFweCBzb2xpZCB2YXIoLS1nMjAwKTtwYWRkaW5nOjAgMjRweDtkaXNwbGF5OmZsZXg7cG9zaXRpb246c3RpY2t5O3RvcDo1NnB4O3otaW5kZXg6MzAwO2JveC1zaGFkb3c6dmFyKC0tc2gpO292ZXJmbG93LXg6YXV0bzt9Ci5udGFie3BhZGRpbmc6MTNweCAxNnB4O2ZvbnQtc2l6ZToxM3B4O2ZvbnQtd2VpZ2h0OjYwMDtjb2xvcjp2YXIoLS1nNTAwKTtjdXJzb3I6cG9pbnRlcjtib3JkZXItYm90dG9tOjJweCBzb2xpZCB0cmFuc3BhcmVudDt0cmFuc2l0aW9uOmFsbCAuMTVzO3doaXRlLXNwYWNlOm5vd3JhcDt9Lm50YWI6aG92ZXJ7Y29sb3I6dmFyKC0tbWlkKTt9Lm50YWIub257Y29sb3I6dmFyKC0tbWlkKTtib3JkZXItYm90dG9tLWNvbG9yOnZhcigtLXNreSk7fQouZmJhcntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgdmFyKC0tZzIwMCk7cGFkZGluZzoxMHB4IDI0cHg7ZGlzcGxheTpmbGV4O2dhcDoxMHB4O2FsaWduLWl0ZW1zOmZsZXgtZW5kO2ZsZXgtd3JhcDp3cmFwO30KLmZne2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjNweDt9LmZse2ZvbnQtc2l6ZToxMHB4O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjp2YXIoLS1nNDAwKTt0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7bGV0dGVyLXNwYWNpbmc6LjVweDt9CnNlbGVjdCxpbnB1dFt0eXBlPXRleHRde2JhY2tncm91bmQ6dmFyKC0tZzUwKTtib3JkZXI6MS41cHggc29saWQgdmFyKC0tZzIwMCk7Y29sb3I6dmFyKC0tZzgwMCk7cGFkZGluZzo2cHggMTBweDtib3JkZXItcmFkaXVzOjdweDtmb250LXNpemU6MTJweDtmb250LWZhbWlseTppbmhlcml0O291dGxpbmU6bm9uZTttaW4td2lkdGg6MTQwcHg7dHJhbnNpdGlvbjpib3JkZXItY29sb3IgLjE1czt9CnNlbGVjdDpmb2N1cyxpbnB1dDpmb2N1c3tib3JkZXItY29sb3I6dmFyKC0tc2t5KTtiYWNrZ3JvdW5kOiNmZmY7fQouYnRuZntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2NvbG9yOnZhcigtLWc2MDApO3BhZGRpbmc6NnB4IDEycHg7Ym9yZGVyLXJhZGl1czo3cHg7Zm9udC1zaXplOjEycHg7Zm9udC13ZWlnaHQ6NjAwO2N1cnNvcjpwb2ludGVyO2ZvbnQtZmFtaWx5OmluaGVyaXQ7dHJhbnNpdGlvbjphbGwgLjE1czthbGlnbi1zZWxmOmZsZXgtZW5kO30uYnRuZjpob3Zlcntib3JkZXItY29sb3I6dmFyKC0tc2t5KTtjb2xvcjp2YXIoLS1taWQpO30KLmN0YWd7Zm9udC1zaXplOjEycHg7Zm9udC13ZWlnaHQ6NjAwO2NvbG9yOnZhcigtLW1pZCk7YmFja2dyb3VuZDp2YXIoLS1za3ktbCk7Ym9yZGVyOjFweCBzb2xpZCAjYmZkYmZlO3BhZGRpbmc6NHB4IDEwcHg7Ym9yZGVyLXJhZGl1czoyMHB4O2FsaWduLXNlbGY6ZmxleC1lbmQ7fQoucGd7ZGlzcGxheTpub25lO3BhZGRpbmc6MjBweCAyNHB4O30ucGcub257ZGlzcGxheTpibG9jazt9Ci5rcm93e2Rpc3BsYXk6Z3JpZDtnYXA6MTJweDttYXJnaW4tYm90dG9tOjIwcHg7fS5rNntncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDYsMWZyKTt9Lmsze2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMywxZnIpO21heC13aWR0aDo1MjBweDt9Lmsye2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMiwxZnIpO21heC13aWR0aDozNjBweDt9Ci5rcGl7YmFja2dyb3VuZDojZmZmO2JvcmRlcjoxLjVweCBzb2xpZCB2YXIoLS1nMjAwKTtib3JkZXItcmFkaXVzOnZhcigtLXIpO3BhZGRpbmc6MTRweCAxNnB4O2JveC1zaGFkb3c6dmFyKC0tc2gpO30ua3BpLmNsa3tjdXJzb3I6cG9pbnRlcjt0cmFuc2l0aW9uOmFsbCAuMTVzO30ua3BpLmNsazpob3Zlcntib3JkZXItY29sb3I6dmFyKC0tc2t5KTtib3gtc2hhZG93OjAgNHB4IDE2cHggcmdiYSgxNSw0MSw4MiwuMSk7fS5rcGkuc2Vse2JvcmRlci1jb2xvcjp2YXIoLS1za3kpO2JveC1zaGFkb3c6MCAwIDAgM3B4IHJnYmEoNTksMTMwLDI0NiwuMTIpO30KLmtsYmx7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzouNXB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi1ib3R0b206NnB4O30ua3ZhbHtmb250LXNpemU6MjRweDtmb250LXdlaWdodDo4MDA7bGluZS1oZWlnaHQ6MTtsZXR0ZXItc3BhY2luZzotLjVweDt9LmtzdWJ7Zm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7bWFyZ2luLXRvcDozcHg7fQouYy1ie2NvbG9yOnZhcigtLW1pZCk7fS5jLWd7Y29sb3I6dmFyKC0tZ3JlZW4pO30uYy15e2NvbG9yOnZhcigtLXllbCk7fS5jLXJ7Y29sb3I6dmFyKC0tcmVkKTt9LmMta3tjb2xvcjp2YXIoLS1ibGspO30uYy1ve2NvbG9yOnZhcigtLW9yYSk7fS5jLXB7Y29sb3I6dmFyKC0tcHVyKTt9Ci5zZWN7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3RleHQtdHJhbnNmb3JtOnVwcGVyY2FzZTtsZXR0ZXItc3BhY2luZzouOHB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi1ib3R0b206MTBweDtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDo4cHg7fS5zZWM6OmFmdGVye2NvbnRlbnQ6IiI7ZmxleDoxO2hlaWdodDoxcHg7YmFja2dyb3VuZDp2YXIoLS1nMjAwKTt9Ci50d3JhcHtiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7b3ZlcmZsb3c6aGlkZGVuO2JveC1zaGFkb3c6dmFyKC0tc2gpO21hcmdpbi1ib3R0b206MjBweDt9Ci50aGRye3BhZGRpbmc6MTJweCAxNnB4O2JvcmRlci1ib3R0b206MXB4IHNvbGlkIHZhcigtLWcxMDApO2Rpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjthbGlnbi1pdGVtczpjZW50ZXI7fS50dGx7Zm9udC1zaXplOjEzcHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLWc3MDApO30udGNudHtmb250LXNpemU6MTJweDtjb2xvcjp2YXIoLS1nNDAwKTt9Ci50c2Nye292ZXJmbG93LXg6YXV0bzttYXgtaGVpZ2h0OjUyMHB4O292ZXJmbG93LXk6YXV0bzt9CnRhYmxle3dpZHRoOjEwMCU7Ym9yZGVyLWNvbGxhcHNlOmNvbGxhcHNlO310aHtwYWRkaW5nOjlweCAxMnB4O3RleHQtYWxpZ246bGVmdDtmb250LXNpemU6MTBweDtmb250LXdlaWdodDo3MDA7dGV4dC10cmFuc2Zvcm06dXBwZXJjYXNlO2xldHRlci1zcGFjaW5nOi41cHg7Y29sb3I6dmFyKC0tZzQwMCk7YmFja2dyb3VuZDp2YXIoLS1nNTApO2JvcmRlci1ib3R0b206MXB4IHNvbGlkIHZhcigtLWcyMDApO3doaXRlLXNwYWNlOm5vd3JhcDtwb3NpdGlvbjpzdGlja3k7dG9wOjA7ei1pbmRleDoxO30KdGR7cGFkZGluZzoxMHB4IDEycHg7Zm9udC1zaXplOjEycHg7Ym9yZGVyLWJvdHRvbToxcHggc29saWQgdmFyKC0tZzEwMCk7dmVydGljYWwtYWxpZ246bWlkZGxlO310cjpsYXN0LWNoaWxkIHRke2JvcmRlci1ib3R0b206bm9uZTt9dHI6aG92ZXIgdGR7YmFja2dyb3VuZDp2YXIoLS1za3ktcCk7fQoucGlsbHtkaXNwbGF5OmlubGluZS1mbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtnYXA6NHB4O3BhZGRpbmc6MnB4IDhweDtib3JkZXItcmFkaXVzOjIwcHg7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NzAwO3doaXRlLXNwYWNlOm5vd3JhcDt9Ci5wLW97YmFja2dyb3VuZDp2YXIoLS1vbCk7Y29sb3I6dmFyKC0tb3JhKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLW9iKTt9LnAtZ3tiYWNrZ3JvdW5kOnZhcigtLWdsKTtjb2xvcjp2YXIoLS1ncmVlbik7Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1nYik7fS5wLXl7YmFja2dyb3VuZDp2YXIoLS15bCk7Y29sb3I6dmFyKC0teWVsKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLXliKTt9LnAtcntiYWNrZ3JvdW5kOnZhcigtLXJsKTtjb2xvcjp2YXIoLS1yZWQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tcmIpO30ucC1re2JhY2tncm91bmQ6dmFyKC0tYmtsKTtjb2xvcjp2YXIoLS1ibGspO2JvcmRlcjoxcHggc29saWQgdmFyKC0tYmtiKTt9LnAtcHtiYWNrZ3JvdW5kOnZhcigtLXBsKTtjb2xvcjp2YXIoLS1wdXIpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tcGIpO30ucC1ncntiYWNrZ3JvdW5kOnZhcigtLWcxMDApO2NvbG9yOnZhcigtLWc1MDApO2JvcmRlcjoxcHggc29saWQgdmFyKC0tZzIwMCk7fQouY29ncmlke2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDQsMWZyKTtnYXA6MTJweDttYXJnaW4tYm90dG9tOjIwcHg7fQouY29jYXJke2JhY2tncm91bmQ6I2ZmZjtib3JkZXI6MS41cHggc29saWQgdmFyKC0tZzIwMCk7Ym9yZGVyLXJhZGl1czp2YXIoLS1yKTtwYWRkaW5nOjE0cHggMTZweDtib3gtc2hhZG93OnZhcigtLXNoKTtjdXJzb3I6cG9pbnRlcjt0cmFuc2l0aW9uOmFsbCAuMTVzO30uY29jYXJkOmhvdmVye2JvcmRlci1jb2xvcjp2YXIoLS1za3kpO2JveC1zaGFkb3c6MCA0cHggMTRweCByZ2JhKDE1LDQxLDgyLC4xKTt9LmNvY2FyZC5zZWx7Ym9yZGVyLWNvbG9yOnZhcigtLXNreSk7Ym94LXNoYWRvdzowIDAgMCAzcHggcmdiYSg1OSwxMzAsMjQ2LC4xMik7fQouY28tdG9we2Rpc3BsYXk6ZmxleDtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjthbGlnbi1pdGVtczpmbGV4LXN0YXJ0O21hcmdpbi1ib3R0b206NnB4O30uY28tbmFtZXtmb250LXNpemU6MTNweDtmb250LXdlaWdodDo3MDA7Y29sb3I6dmFyKC0tbmF2eSk7bGluZS1oZWlnaHQ6MS4yO30uY28tY3Nte2ZvbnQtc2l6ZToxMHB4O2NvbG9yOnZhcigtLWc0MDApO21hcmdpbi10b3A6MnB4O30KLmNvLWJhcntoZWlnaHQ6NHB4O2JhY2tncm91bmQ6dmFyKC0tZzEwMCk7Ym9yZGVyLXJhZGl1czoycHg7b3ZlcmZsb3c6aGlkZGVuO21hcmdpbjo4cHggMCA2cHg7fS5jby1iZntoZWlnaHQ6MTAwJTtib3JkZXItcmFkaXVzOjJweDt9Ci5jby1zdGF0c3tkaXNwbGF5OmZsZXg7Z2FwOjVweDtmbGV4LXdyYXA6d3JhcDt9LmNvc3tkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDozcHg7Zm9udC1zaXplOjEwcHg7Zm9udC13ZWlnaHQ6NjAwO30KLmRvdHt3aWR0aDo3cHg7aGVpZ2h0OjdweDtib3JkZXItcmFkaXVzOjUwJTtmbGV4LXNocmluazowO30uZC1ve2JhY2tncm91bmQ6dmFyKC0tb3JhKTt9LmQtZ3tiYWNrZ3JvdW5kOnZhcigtLWdyZWVuKTt9LmQteXtiYWNrZ3JvdW5kOnZhcigtLXllbCk7fS5kLXJ7YmFja2dyb3VuZDp2YXIoLS1yZWQpO30uZC1re2JhY2tncm91bmQ6dmFyKC0tYmxrKTt9Ci5kZXR7YmFja2dyb3VuZDojZmZmO2JvcmRlcjoxLjVweCBzb2xpZCB2YXIoLS1za3kpO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7cGFkZGluZzoxNnB4IDIwcHg7bWFyZ2luLWJvdHRvbToyMHB4O2JveC1zaGFkb3c6MCAwIDAgM3B4IHJnYmEoNTksMTMwLDI0NiwuMDgpO30KLmRldC10dGx7Zm9udC1zaXplOjE0cHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLW5hdnkpO21hcmdpbi1ib3R0b206MTJweDtkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47YWxpZ24taXRlbXM6Y2VudGVyO30KLmNsc3tjdXJzb3I6cG9pbnRlcjtjb2xvcjp2YXIoLS1nNDAwKTtmb250LXNpemU6MThweDtsaW5lLWhlaWdodDoxO30uY2xzOmhvdmVye2NvbG9yOnZhcigtLWc3MDApO30KLmlib3h7Ym9yZGVyLXJhZGl1czp2YXIoLS1yKTtwYWRkaW5nOjEycHggMTZweDttYXJnaW4tYm90dG9tOjE2cHg7Zm9udC1zaXplOjEzcHg7Zm9udC13ZWlnaHQ6NTAwO30KLmlib3gtcHtiYWNrZ3JvdW5kOnZhcigtLXBsKTtib3JkZXI6MS41cHggc29saWQgdmFyKC0tcGIpO2NvbG9yOnZhcigtLXB1cik7fS5pYm94LXl7YmFja2dyb3VuZDp2YXIoLS15bCk7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLXliKTtjb2xvcjp2YXIoLS15ZWwpO30KLmNrLWdyb3Vwe2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjRweDtwYWRkaW5nOjRweCAwO30KLmNrLWxibHtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDo2cHg7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tZzYwMCk7Y3Vyc29yOnBvaW50ZXI7d2hpdGUtc3BhY2U6bm93cmFwO30KLmNrLWxibCBpbnB1dFt0eXBlPWNoZWNrYm94XXt3aWR0aDoxNHB4O2hlaWdodDoxNHB4O2FjY2VudC1jb2xvcjp2YXIoLS1za3kpO2N1cnNvcjpwb2ludGVyO2ZsZXgtc2hyaW5rOjA7fQouY2stbGJsOmhvdmVye2NvbG9yOnZhcigtLW1pZCk7fQouY2hhcnQtc2VjdGlvbntiYWNrZ3JvdW5kOiNmZmY7Ym9yZGVyOjEuNXB4IHNvbGlkIHZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6dmFyKC0tcik7cGFkZGluZzoxOHB4IDIycHg7bWFyZ2luOjAgMjRweCAyMHB4O2JveC1zaGFkb3c6dmFyKC0tc2gpO30KLmNoYXJ0LXRpdGxle2ZvbnQtc2l6ZToxMXB4O2ZvbnQtd2VpZ2h0OjcwMDt0ZXh0LXRyYW5zZm9ybTp1cHBlcmNhc2U7bGV0dGVyLXNwYWNpbmc6LjdweDtjb2xvcjp2YXIoLS1nNDAwKTttYXJnaW4tYm90dG9tOjE0cHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2Vlbjt9Ci5jaGFydC1jYW52YXMtd3JhcHtwb3NpdGlvbjpyZWxhdGl2ZTtoZWlnaHQ6MTgwcHg7fQoucmFuay1saXN0e2Rpc3BsYXk6ZmxleDtmbGV4LWRpcmVjdGlvbjpjb2x1bW47Z2FwOjZweDt9Ci5yYW5rLXJvd3tkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2dhcDoxMHB4O2ZvbnQtc2l6ZToxMnB4O30KLnJhbmstbnVte3dpZHRoOjE4cHg7Zm9udC13ZWlnaHQ6NzAwO2NvbG9yOnZhcigtLWc0MDApO3RleHQtYWxpZ246cmlnaHQ7ZmxleC1zaHJpbms6MDt9Ci5yYW5rLW5hbWV7ZmxleDoxO2ZvbnQtd2VpZ2h0OjYwMDtjb2xvcjp2YXIoLS1nNzAwKTtvdmVyZmxvdzpoaWRkZW47dGV4dC1vdmVyZmxvdzplbGxpcHNpczt3aGl0ZS1zcGFjZTpub3dyYXA7fQoucmFuay1iYXItd3JhcHt3aWR0aDoxMjBweDtoZWlnaHQ6NnB4O2JhY2tncm91bmQ6dmFyKC0tZzEwMCk7Ym9yZGVyLXJhZGl1czozcHg7b3ZlcmZsb3c6aGlkZGVuO2ZsZXgtc2hyaW5rOjA7fQoucmFuay1iYXItZmlsbHtoZWlnaHQ6MTAwJTtib3JkZXItcmFkaXVzOjNweDtiYWNrZ3JvdW5kOnZhcigtLXNreSk7fQoucmFuay12YWx7d2lkdGg6NDBweDt0ZXh0LWFsaWduOnJpZ2h0O2ZvbnQtd2VpZ2h0OjcwMDtjb2xvcjp2YXIoLS1taWQpO2ZsZXgtc2hyaW5rOjA7fQouY2hhcnRzLWdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczoxZnIgMWZyO2dhcDoxNnB4O3BhZGRpbmc6MCAyNHB4IDIwcHg7fS5jaGFydHMtZ3JpZC0xe2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6MWZyO2dhcDoxNnB4O3BhZGRpbmc6MCAyNHB4IDIwcHg7fQouY2hhcnRzLWdyaWQtM3tkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOjJmciAxZnI7Z2FwOjE2cHg7cGFkZGluZzowIDI0cHggMjBweDt9Ci5yZXQtZ3JpZHtkaXNwbGF5OmZsZXg7Z2FwOjEwcHg7ZmxleC13cmFwOndyYXA7fQoucmV0LWNhcmR7ZmxleDoxO21pbi13aWR0aDo4MHB4O2JhY2tncm91bmQ6dmFyKC0tZzUwKTtib3JkZXItcmFkaXVzOjhweDtwYWRkaW5nOjEwcHggMTJweDt0ZXh0LWFsaWduOmNlbnRlcjt9Ci5yZXQtcGN0e2ZvbnQtc2l6ZToyMnB4O2ZvbnQtd2VpZ2h0OjgwMDtjb2xvcjp2YXIoLS1taWQpO30KLnJldC1tZXN7Zm9udC1zaXplOjEwcHg7Y29sb3I6dmFyKC0tZzQwMCk7bWFyZ2luLXRvcDoycHg7fQoucmV0LXN1Yntmb250LXNpemU6MTBweDtjb2xvcjp2YXIoLS1nNTAwKTttYXJnaW4tdG9wOjFweDt9Cjo6LXdlYmtpdC1zY3JvbGxiYXJ7d2lkdGg6NXB4O2hlaWdodDo1cHg7fTo6LXdlYmtpdC1zY3JvbGxiYXItdHJhY2t7YmFja2dyb3VuZDp0cmFuc3BhcmVudDt9Ojotd2Via2l0LXNjcm9sbGJhci10aHVtYntiYWNrZ3JvdW5kOnZhcigtLWcyMDApO2JvcmRlci1yYWRpdXM6M3B4O30K").decode('utf-8')
    BODY     = _b64.b64decode("CjxkaXYgY2xhc3M9ImhkciI+CiAgPGRpdiBjbGFzcz0iYnJhbmQiPjxkaXYgY2xhc3M9ImJpY28iPlBMPC9kaXY+PGRpdj48ZGl2IGNsYXNzPSJibmFtZSI+UGlwZUxvdmVyczwvZGl2PjxkaXYgY2xhc3M9ImJ0YWciPkRhc2hib2FyZCBkZSBFbmdhamFtZW50bzwvZGl2PjwvZGl2PjwvZGl2PgogIDxzcGFuIGNsYXNzPSJ1cGQiIGlkPSJ1cGQtbGJsIj48L3NwYW4+CjwvZGl2Pgo8ZGl2IGNsYXNzPSJuYXYiPgogIDxkaXYgY2xhc3M9Im50YWIgb24iIG9uY2xpY2s9ImdvVGFiKCdvdicsdGhpcykiPiYjMTI4MjAyOyBPdmVydmlldzwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCdlbScsdGhpcykiPiYjMTI3OTcwOyBFbXByZXNhczwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCd1cycsdGhpcykiPiYjMTI4MTAwOyBVc3UmYWFjdXRlO3Jpb3M8L2Rpdj4KICA8ZGl2IGNsYXNzPSJudGFiIiAgICBvbmNsaWNrPSJnb1RhYignbmEnLHRoaXMpIj4mIzk4ODg7JiM2NTAzOTsgTnVuY2EgQXNzaXN0aXJhbTwvZGl2PgogIDxkaXYgY2xhc3M9Im50YWIiICAgIG9uY2xpY2s9ImdvVGFiKCduZicsdGhpcykiPiYjMTAwNjc7IEVtcHJlc2FzIHMvIGNhZGFzdHJvPC9kaXY+CiAgPGRpdiBjbGFzcz0ibnRhYiIgICAgb25jbGljaz0iZ29UYWIoJ29yJyx0aGlzKSI+JiMxMjgxMDA7IFVzdSZhYWN1dGU7cmlvcyBzLyBlbXByZXNhPC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy1vdiIgY2xhc3M9InBnIG9uIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+RW1wcmVzYTwvZGl2PjxzZWxlY3QgaWQ9Im92LWNvIj48b3B0aW9uIHZhbHVlPSIiPlRvZGFzPC9vcHRpb24+PC9zZWxlY3Q+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkNTTTwvZGl2PjxzZWxlY3QgaWQ9Im92LWNzbSI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPgogICAgICA8ZGl2IGNsYXNzPSJmbCI+Q3JpYSZjY2VkaWw7JmF0aWxkZTtvIGRvIHVzdSZhYWN1dGU7cmlvPC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9ImNrLWdyb3VwIj4KICAgICAgICA8bGFiZWwgY2xhc3M9ImNrLWxibCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBjbGFzcz0ib3YtY3IiIHZhbHVlPSJsdDMiPiBNZW5vcyBkZSAzIG1lc2VzPC9sYWJlbD4KICAgICAgICA8bGFiZWwgY2xhc3M9ImNrLWxibCI+PGlucHV0IHR5cGU9ImNoZWNrYm94IiBjbGFzcz0ib3YtY3IiIHZhbHVlPSIzdG82Ij4gMyBhIDYgbWVzZXM8L2xhYmVsPgogICAgICAgIDxsYWJlbCBjbGFzcz0iY2stbGJsIj48aW5wdXQgdHlwZT0iY2hlY2tib3giIGNsYXNzPSJvdi1jciIgdmFsdWU9Imd0NiI+IE1haXMgZGUgNiBtZXNlczwvbGFiZWw+CiAgICAgICAgPGxhYmVsIGNsYXNzPSJjay1sYmwiPjxpbnB1dCB0eXBlPSJjaGVja2JveCIgY2xhc3M9Im92LWNyIiB2YWx1ZT0ibm9kYXRlIj4gU2VtIGRhdGE8L2xhYmVsPgogICAgICA8L2Rpdj4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPgogICAgICA8ZGl2IGNsYXNzPSJmbCI+R3J1cG8gLyBQbGFubzwvZGl2PgogICAgICA8c2VsZWN0IGlkPSJvdi1ncnVwbyI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PgogICAgPC9kaXY+CiAgICA8YnV0dG9uIGNsYXNzPSJidG5mIiBpZD0ib3YtcnN0Ij5MaW1wYXI8L2J1dHRvbj4KICA8L2Rpdj4KICA8ZGl2IGlkPSJvdi1ib2R5Ij48L2Rpdj4KPC9kaXY+Cgo8ZGl2IGlkPSJvdi1jaGFydHMiPgogIDxkaXYgY2xhc3M9ImNoYXJ0cy1ncmlkLTEiPgogICAgPGRpdiBjbGFzcz0iY2hhcnQtc2VjdGlvbiIgc3R5bGU9Im1hcmdpbjowOyI+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXRpdGxlIj5Vc3XDoXJpb3Mgw7puaWNvcyBwb3IgbcOqcyA8c3BhbiBpZD0iZ3J1cG8tc2VsLWxibCIgc3R5bGU9ImZvbnQtc2l6ZToxMHB4O2NvbG9yOnZhcigtLXNreSk7Ij48L3NwYW4+PC9kaXY+CiAgICAgIDxkaXYgY2xhc3M9ImNoYXJ0LWNhbnZhcy13cmFwIj48Y2FudmFzIGlkPSJjaGFydC1tZW5zYWwiPjwvY2FudmFzPjwvZGl2PgogICAgPC9kaXY+CgogIDwvZGl2PgogIDxkaXYgY2xhc3M9ImNoYXJ0cy1ncmlkIj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MDsiPgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10aXRsZSI+RXZvbHXDp8OjbyBwb3IgZ3J1cG88L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0iY2hhcnQtY2FudmFzLXdyYXAiPjxjYW52YXMgaWQ9ImNoYXJ0LWdydXBvcyI+PC9jYW52YXM+PC9kaXY+CiAgICA8L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImNoYXJ0LXNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MDsiPgogICAgICA8ZGl2IGNsYXNzPSJjaGFydC10aXRsZSI+VG9wIGVtcHJlc2FzICjDumx0aW1vcyAzIG1lc2VzKSA8c3BhbiBzdHlsZT0iZm9udC1zaXplOjEwcHg7Y29sb3I6dmFyKC0tZzQwMCk7Zm9udC13ZWlnaHQ6NDAwOyI+cG9yIG7CuiBkZSBhdWxhczwvc3Bhbj48L2Rpdj4KICAgICAgPGRpdiBjbGFzcz0icmFuay1saXN0IiBpZD0icmFuay1ib2R5Ij48L2Rpdj4KICAgIDwvZGl2PgogIDwvZGl2Pgo8L2Rpdj4KPGRpdiBpZD0icGctZW0iIGNsYXNzPSJwZyI+CiAgPGRpdiBjbGFzcz0iZmJhciI+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkJ1c2NhcjwvZGl2PjxpbnB1dCB0eXBlPSJ0ZXh0IiBpZD0iZW0tcSIgcGxhY2Vob2xkZXI9Ik5vbWUgZGEgZW1wcmVzYS4uLiI+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkNTTTwvZGl2PjxzZWxlY3QgaWQ9ImVtLWNzbSI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9ImVtLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0iZW0tY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0iZW0tYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy11cyIgY2xhc3M9InBnIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+QnVzY2FyPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJ1cy1xIiBwbGFjZWhvbGRlcj0iTm9tZSBvdSBlLW1haWwuLi4iPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5FbXByZXNhPC9kaXY+PHNlbGVjdCBpZD0idXMtY28iPjxvcHRpb24gdmFsdWU9IiI+VG9kYXM8L29wdGlvbj48L3NlbGVjdD48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+Q1NNPC9kaXY+PHNlbGVjdCBpZD0idXMtY3NtIj48b3B0aW9uIHZhbHVlPSIiPlRvZG9zPC9vcHRpb24+PC9zZWxlY3Q+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkZsYWc8L2Rpdj4KICAgICAgPHNlbGVjdCBpZD0idXMtZmwiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+VG9kYXM8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJvZmZlbnNpdmUiPiYjMTI4MjkzOyBPZmVuc2l2YTwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9ImdyZWVuIj4mIzEyODk5NDsgR3JlZW48L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJ5ZWxsb3ciPiYjMTI4OTkzOyBZZWxsb3c8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJyZWQiPiYjMTI4MzA4OyBSZWQ8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJibGFjayI+JiM5ODk5OyBCbGFjazwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5DcmlhJmNjZWRpbDsmYXRpbGRlO288L2Rpdj4KICAgICAgPHNlbGVjdCBpZD0idXMtY3IiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+UXVhbHF1ZXI8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJsdDMiPk1lbm9zIGRlIDMgbWVzZXM8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSIzdG82Ij4zIGEgNiBtZXNlczwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9Imd0NiI+TWFpcyBkZSA2IG1lc2VzPC9vcHRpb24+CiAgICAgIDwvc2VsZWN0PgogICAgPC9kaXY+CiAgICA8YnV0dG9uIGNsYXNzPSJidG5mIiBpZD0idXMtcnN0Ij5MaW1wYXI8L2J1dHRvbj4KICAgIDxkaXYgY2xhc3M9ImN0YWciIGlkPSJ1cy1jdGFnIj48L2Rpdj4KICA8L2Rpdj4KICA8ZGl2IGlkPSJ1cy1ib2R5IiBzdHlsZT0icGFkZGluZzoyMHB4IDI0cHg7Ij48L2Rpdj4KPC9kaXY+CjxkaXYgaWQ9InBnLW5hIiBjbGFzcz0icGciPgogIDxkaXYgY2xhc3M9ImZiYXIiPgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5CdXNjYXI8L2Rpdj48aW5wdXQgdHlwZT0idGV4dCIgaWQ9Im5hLXEiIHBsYWNlaG9sZGVyPSJOb21lIG91IGUtbWFpbC4uLiI+PC9kaXY+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkVtcHJlc2E8L2Rpdj48c2VsZWN0IGlkPSJuYS1jbyI+PG9wdGlvbiB2YWx1ZT0iIj5Ub2Rhczwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5DU008L2Rpdj48c2VsZWN0IGlkPSJuYS1jc20iPjxvcHRpb24gdmFsdWU9IiI+VG9kb3M8L29wdGlvbj48L3NlbGVjdD48L2Rpdj4KICAgIDxidXR0b24gY2xhc3M9ImJ0bmYiIGlkPSJuYS1yc3QiPkxpbXBhcjwvYnV0dG9uPgogICAgPGRpdiBjbGFzcz0iY3RhZyIgaWQ9Im5hLWN0YWciPjwvZGl2PgogIDwvZGl2PgogIDxkaXYgaWQ9Im5hLWJvZHkiIHN0eWxlPSJwYWRkaW5nOjIwcHggMjRweDsiPjwvZGl2Pgo8L2Rpdj4KPGRpdiBpZD0icGctbmYiIGNsYXNzPSJwZyI+CiAgPGRpdiBjbGFzcz0iZmJhciI+CiAgICA8ZGl2IGNsYXNzPSJmZyI+PGRpdiBjbGFzcz0iZmwiPkJ1c2NhciBlbXByZXNhPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJuZi1xIiBwbGFjZWhvbGRlcj0iTm9tZSBkYSBlbXByZXNhLi4uIj48L2Rpdj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+Q29uc3VtaXUgYXVsYXM/PC9kaXY+CiAgICAgIDxzZWxlY3QgaWQ9Im5mLWNvbnMiPgogICAgICAgIDxvcHRpb24gdmFsdWU9IiI+VG9kb3M8L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJzaW0iPlNpbTwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9Im5hbyI+TiZhdGlsZGU7bzwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9Im5mLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0ibmYtY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0ibmYtYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo8ZGl2IGlkPSJwZy1vciIgY2xhc3M9InBnIj4KICA8ZGl2IGNsYXNzPSJmYmFyIj4KICAgIDxkaXYgY2xhc3M9ImZnIj48ZGl2IGNsYXNzPSJmbCI+QnVzY2FyPC9kaXY+PGlucHV0IHR5cGU9InRleHQiIGlkPSJvci1xIiBwbGFjZWhvbGRlcj0iTm9tZSwgZS1tYWlsIG91IGVtcHJlc2EuLi4iPjwvZGl2PgogICAgPGRpdiBjbGFzcz0iZmciPjxkaXYgY2xhc3M9ImZsIj5TdGF0dXMgZW1wcmVzYTwvZGl2PgogICAgICA8c2VsZWN0IGlkPSJvci1zdCI+CiAgICAgICAgPG9wdGlvbiB2YWx1ZT0iIj5Ub2Rvczwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9IkNodXJuIj5DaHVybjwvb3B0aW9uPgogICAgICAgIDxvcHRpb24gdmFsdWU9IkluYXRpdm8iPkluYXRpdm88L29wdGlvbj4KICAgICAgICA8b3B0aW9uIHZhbHVlPSJOJmF0aWxkZTtvIGNhZGFzdHJhZGEiPk4mYXRpbGRlO28gY2FkYXN0cmFkYTwvb3B0aW9uPgogICAgICA8L3NlbGVjdD4KICAgIDwvZGl2PgogICAgPGJ1dHRvbiBjbGFzcz0iYnRuZiIgaWQ9Im9yLXJzdCI+TGltcGFyPC9idXR0b24+CiAgICA8ZGl2IGNsYXNzPSJjdGFnIiBpZD0ib3ItY3RhZyI+PC9kaXY+CiAgPC9kaXY+CiAgPGRpdiBpZD0ib3ItYm9keSIgc3R5bGU9InBhZGRpbmc6MjBweCAyNHB4OyI+PC9kaXY+CjwvZGl2Pgo=").decode('utf-8')
    JS_LOGIC = _b64.b64decode("ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVwZC1sYmwiKS50ZXh0Q29udGVudD0iQXR1YWxpemFkbyBlbSAiK1VQRDsKZnVuY3Rpb24gZXNjKHMpe3JldHVybiBTdHJpbmcoc3x8IiIpLnJlcGxhY2UoLyYvZywiJmFtcDsiKS5yZXBsYWNlKC88L2csIiZsdDsiKS5yZXBsYWNlKC8+L2csIiZndDsiKS5yZXBsYWNlKC8iL2csIiZxdW90OyIpO30KZnVuY3Rpb24gcGN0KGEsYil7cmV0dXJuIGI+MD9NYXRoLnJvdW5kKGEvYioxMDApOjA7fQpmdW5jdGlvbiBtU2luY2UoZHMpe2lmKCFkcylyZXR1cm4gOTk5O3ZhciBkPW5ldyBEYXRlKGRzKSxuPW5ldyBEYXRlKCk7cmV0dXJuKG4uZ2V0RnVsbFllYXIoKS1kLmdldEZ1bGxZZWFyKCkpKjEyKyhuLmdldE1vbnRoKCktZC5nZXRNb250aCgpKTt9CmZ1bmN0aW9uIGZQaWxsKGYpewogIGlmKGY9PT0ib2ZmZW5zaXZlIilyZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1vIj4mIzEyODI5MzsgT2ZlbnNpdmE8L3NwYW4+JzsKICBpZihmPT09ImdyZWVuIikgICAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtZyI+JiMxMjg5OTQ7IEdyZWVuPC9zcGFuPic7CiAgaWYoZj09PSJ5ZWxsb3ciKSAgIHJldHVybic8c3BhbiBjbGFzcz0icGlsbCBwLXkiPiYjMTI4OTkzOyBZZWxsb3c8L3NwYW4+JzsKICBpZihmPT09InJlZCIpICAgICAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtciI+JiMxMjgzMDg7IFJlZDwvc3Bhbj4nOwogIHJldHVybic8c3BhbiBjbGFzcz0icGlsbCBwLWsiPiYjOTg5OTsgQmxhY2s8L3NwYW4+JzsKfQpmdW5jdGlvbiBzdFBpbGwocyl7CiAgaWYocz09PSJDaHVybiIpICByZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1yIj5DaHVybjwvc3Bhbj4nOwogIGlmKHM9PT0iSW5hdGl2byIpcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtayI+SW5hdGl2bzwvc3Bhbj4nOwogIGlmKHM9PT0iQXRpdm8iKSAgcmV0dXJuJzxzcGFuIGNsYXNzPSJwaWxsIHAtZyI+QXRpdm88L3NwYW4+JzsKICByZXR1cm4nPHNwYW4gY2xhc3M9InBpbGwgcC1wIj5OXHhFM28gY2FkYXN0cmFkYTwvc3Bhbj4nOwp9CmZ1bmN0aW9uIGdvVGFiKG4sZWwpewogIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5wZyIpLmZvckVhY2goZnVuY3Rpb24ocCl7cC5jbGFzc0xpc3QucmVtb3ZlKCJvbiIpO30pOwogIGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5udGFiIikuZm9yRWFjaChmdW5jdGlvbih0KXt0LmNsYXNzTGlzdC5yZW1vdmUoIm9uIik7fSk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInBnLSIrbikuY2xhc3NMaXN0LmFkZCgib24iKTtlbC5jbGFzc0xpc3QuYWRkKCJvbiIpOwp9CmZ1bmN0aW9uIHBvcChpZCx2YWxzKXt2YXIgcz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7dmFscy5mb3JFYWNoKGZ1bmN0aW9uKHYpe3ZhciBvPWRvY3VtZW50LmNyZWF0ZUVsZW1lbnQoIm9wdGlvbiIpO28udmFsdWU9djtvLnRleHRDb250ZW50PXY7cy5hcHBlbmRDaGlsZChvKTt9KTt9CnZhciBhY29zPVsuLi5uZXcgU2V0KFUubWFwKGZ1bmN0aW9uKHUpe3JldHVybiB1LmNvbXBhbnk7fSkpXS5zb3J0KCk7CnZhciBhY3Ntcz1bLi4ubmV3IFNldChVLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jc207fSkuZmlsdGVyKEJvb2xlYW4pKV0uc29ydCgpOwpwb3AoIm92LWNvIixhY29zKTtwb3AoIm92LWNzbSIsYWNzbXMpO3BvcCgiZW0tY3NtIixhY3Ntcyk7CnBvcCgidXMtY28iLGFjb3MpO3BvcCgidXMtY3NtIixhY3Ntcyk7CnBvcCgibmEtY28iLFsuLi5uZXcgU2V0KE5WLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jb21wYW55O30pKV0uc29ydCgpKTsKcG9wKCJuYS1jc20iLFsuLi5uZXcgU2V0KE5WLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jc207fSkuZmlsdGVyKEJvb2xlYW4pKV0uc29ydCgpKTsKdmFyIG92Rj1udWxsOwpmdW5jdGlvbiBydW5PdigpewogIHZhciBjbz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY28iKS52YWx1ZSxjc209ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm92LWNzbSIpLnZhbHVlOwogIHZhciBjckNoZWNrZWQ9Wy4uLmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5vdi1jcjpjaGVja2VkIildLm1hcChmdW5jdGlvbihjKXtyZXR1cm4gYy52YWx1ZTt9KTsKICB2YXIgZ3JDaGVja2VkPVsuLi5kb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCIub3YtZ3I6Y2hlY2tlZCIpXS5tYXAoZnVuY3Rpb24oYyl7cmV0dXJuIGMudmFsdWU7fSk7CiAgdmFyIGZkPVUuZmlsdGVyKGZ1bmN0aW9uKHUpewogICAgaWYoY28mJnUuY29tcGFueSE9PWNvKXJldHVybiBmYWxzZTsKICAgIGlmKGNzbSYmdS5jc20hPT1jc20pcmV0dXJuIGZhbHNlOwogICAgaWYoY3JDaGVja2VkLmxlbmd0aD4wKXsKICAgICAgdmFyIG5vRGF0ZT0hdS5jcmVhdGVkX2F0OwogICAgICB2YXIgbT1ub0RhdGU/LTE6bVNpbmNlKHUuY3JlYXRlZF9hdCk7CiAgICAgIHZhciBsdDM9IW5vRGF0ZSYmbTwzLGlzM3RvNj0hbm9EYXRlJiZtPj0zJiZtPD02LGd0Nj0hbm9EYXRlJiZtPjY7CiAgICAgIHZhciBvaz0oY3JDaGVja2VkLmluZGV4T2YoImx0MyIpPj0wJiZsdDMpfHwoY3JDaGVja2VkLmluZGV4T2YoIjN0bzYiKT49MCYmaXMzdG82KXx8CiAgICAgICAgICAgICAoY3JDaGVja2VkLmluZGV4T2YoImd0NiIpPj0wJiZndDYpfHwoY3JDaGVja2VkLmluZGV4T2YoIm5vZGF0ZSIpPj0wJiZub0RhdGUpOwogICAgICBpZighb2spcmV0dXJuIGZhbHNlOwogICAgfQogICAgcmV0dXJuIHRydWU7CiAgfSk7CiAgdmFyIHRvdD1mZC5sZW5ndGgsYU09ZmQuZmlsdGVyKGZ1bmN0aW9uKHUpe3JldHVybiB1LmFjdGl2ZV90aGlzX21vbnRoO30pLmxlbmd0aDsKICB2YXIgb2ZmPWZkLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5mbGFnPT09Im9mZmVuc2l2ZSI7fSk7CiAgdmFyIHllbD1mZC5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuZmxhZz09PSJ5ZWxsb3ciO30pOwogIHZhciByZWQ9ZmQuZmlsdGVyKGZ1bmN0aW9uKHUpe3JldHVybiB1LmZsYWc9PT0icmVkIjt9KTsKICB2YXIgYmxrPWZkLmZpbHRlcihmdW5jdGlvbih1KXtyZXR1cm4gdS5mbGFnPT09ImJsYWNrIjt9KTsKICB2YXIga3Bpcz1bCiAgICB7bGJsOiJUb3RhbCBVc3VceEUxcmlvcyIsICAgIHZhbDp0b3QsICAgICAgIHN1YjoiZW1wcmVzYXMgYXRpdmFzIiwgICAgICAgICAgICAgIGNsczoiYy1iIixncnA6bnVsbH0sCiAgICB7bGJsOiJBdGl2b3MgZXN0ZSBtXHhFQXMiLCAgIHZhbDphTSwgICAgICAgIHN1YjpwY3QoYU0sdG90KSsiJSBkbyB0b3RhbCIsICAgICAgIGNsczoiYy1nIixncnA6ImFjdGl2ZSJ9LAogICAge2xibDoiJiMxMjgyOTM7IE9mZW5zaXZhIiwgICB2YWw6b2ZmLmxlbmd0aCxzdWI6ImF0aXZvcyBub3MgMiBceEZBbHRpbW9zIG1lc2VzIixjbHM6ImMtbyIsZ3JwOiJvZmZlbnNpdmUifSwKICAgIHtsYmw6IiYjMTI4OTkzOyBZZWxsb3ciLCAgICAgdmFsOnllbC5sZW5ndGgsc3ViOiJpbmF0aXZvcyAzMC02MCBkaWFzIiwgICAgICAgICAgY2xzOiJjLXkiLGdycDoieWVsbG93In0sCiAgICB7bGJsOiImIzEyODMwODsgUmVkIiwgICAgICAgIHZhbDpyZWQubGVuZ3RoLHN1YjoiaW5hdGl2b3MgNjAtOTAgZGlhcyIsICAgICAgICAgIGNsczoiYy1yIixncnA6InJlZCJ9LAogICAge2xibDoiJiM5ODk5OyBCbGFjayIsICAgICAgICB2YWw6YmxrLmxlbmd0aCxzdWI6ImluYXRpdm9zIDkwKyBkaWFzIiwgICAgICAgICAgICBjbHM6ImMtayIsZ3JwOiJibGFjayJ9LAogIF07CiAgdmFyIGtoPSc8ZGl2IGNsYXNzPSJrcm93IGs2Ij4nOwogIGtwaXMuZm9yRWFjaChmdW5jdGlvbihrKXsKICAgIHZhciBpc1NlbD0ob3ZGPT09ay5ncnAmJmsuZ3JwIT09bnVsbCk/IiBzZWwiOiIiLGlzQ2xrPWsuZ3JwPyIgY2xrIjoiIjsKICAgIGtoKz0nPGRpdiBjbGFzcz0ia3BpJytpc0Nsaytpc1NlbCsnIicrKGsuZ3JwPycgb25jbGljaz0idG9nT3YoXCcnK2suZ3JwKydcJykiJzonJykrJz4nKwogICAgICAnPGRpdiBjbGFzcz0ia2xibCI+JytrLmxibCsnPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCAnK2suY2xzKyciPicray52YWwrJzwvZGl2PjxkaXYgY2xhc3M9ImtzdWIiPicray5zdWIrJzwvZGl2PjwvZGl2Pic7CiAgfSk7CiAga2grPSc8L2Rpdj4nOwogIHZhciBkaD0nJzsKICBpZihvdkYpewogICAgdmFyIHN1YjsKICAgIGlmKG92Rj09PSJhY3RpdmUiKXN1Yj1mZC5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuYWN0aXZlX3RoaXNfbW9udGg7fSk7CiAgICBlbHNlIGlmKG92Rj09PSJvZmZlbnNpdmUiKXN1Yj1vZmY7CiAgICBlbHNlIHN1Yj1mZC5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuZmxhZz09PW92Rjt9KTsKICAgIHZhciBzZWVuPXt9O3N1Yj1zdWIuZmlsdGVyKGZ1bmN0aW9uKHUpe2lmKHNlZW5bdS5lbWFpbF0pcmV0dXJuIGZhbHNlO3NlZW5bdS5lbWFpbF09MTtyZXR1cm4gdHJ1ZTt9KTsKICAgIHZhciBsYmxNYXA9eyJhY3RpdmUiOiJBdGl2b3MgZXN0ZSBtXHhlYXMiLCJvZmZlbnNpdmUiOiJFbSBPZmVuc2l2YSAoMiBceEZBbHRpbW9zIG1lc2VzKSIsInllbGxvdyI6IlllbGxvdyBGbGFnIiwicmVkIjoiUmVkIEZsYWciLCJibGFjayI6IkJsYWNrIEZsYWcifTsKICAgIHZhciByb3dzPXN1Yi5zbGljZSgwLDMwMCkubWFwKGZ1bmN0aW9uKHUpewogICAgICByZXR1cm4gJzx0cj48dGQ+PGRpdiBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2ModS5uYW1lKSsnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij4nK2VzYyh1LmVtYWlsKSsnPC9kaXY+PC90ZD4nKwogICAgICAgICc8dGQ+Jytlc2ModS5jb21wYW55KSsnPC90ZD48dGQ+Jytlc2ModS5jc218fCJcdTIwMTQiKSsnPC90ZD48dGQ+JytmUGlsbCh1LmZsYWcpKyc8L3RkPicrCiAgICAgICAgJzx0ZD4nK2VzYyh1Lmxhc3RfY29uc3VtZWR8fCJcdTIwMTQiKSsnPC90ZD48dGQ+Jyt1LnRvdGFsX2NvbnN1bWVkKyc8L3RkPjwvdHI+JzsKICAgIH0pLmpvaW4oJycpOwogICAgZGg9JzxkaXYgY2xhc3M9ImRldCI+PGRpdiBjbGFzcz0iZGV0LXR0bCI+PHNwYW4+JytsYmxNYXBbb3ZGXSsnIFx1MjAxNCAnK3N1Yi5sZW5ndGgrJyB1c3VceEUxcmlvczwvc3Bhbj4nKwogICAgICAnPHNwYW4gY2xhc3M9ImNscyIgb25jbGljaz0ib3ZGPW51bGw7cnVuT3YoKSI+JiMxMDAwNTs8L3NwYW4+PC9kaXY+JysKICAgICAgJzxkaXYgY2xhc3M9InRzY3IiPjx0YWJsZT48dGhlYWQ+PHRyPjx0aD5Vc3VceEUxcmlvPC90aD48dGg+RW1wcmVzYTwvdGg+PHRoPkNTTTwvdGg+PHRoPkZsYWc8L3RoPjx0aD5ceERBbHRpbW8gY29uc3VtbzwvdGg+PHRoPlRvdGFsIGF1bGFzPC90aD48L3RyPjwvdGhlYWQ+JysKICAgICAgJzx0Ym9keT4nK3Jvd3MrJzwvdGJvZHk+PC90YWJsZT48L2Rpdj4nKwogICAgICAoc3ViLmxlbmd0aD4zMDA/JzxkaXYgc3R5bGU9InBhZGRpbmc6OHB4O2ZvbnQtc2l6ZToxMXB4O2NvbG9yOnZhcigtLWc0MDApOyI+TW9zdHJhbmRvIDMwMCBkZSAnK3N1Yi5sZW5ndGgrJzwvZGl2Pic6JycpKwogICAgJzwvZGl2Pic7CiAgfQogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1ib2R5IikuaW5uZXJIVE1MPSc8ZGl2IHN0eWxlPSJwYWRkaW5nOjIwcHggMjRweDsiPicra2grZGgrJzwvZGl2Pic7Cn0KZnVuY3Rpb24gdG9nT3YoZyl7b3ZGPShvdkY9PT1nKT9udWxsOmc7cnVuT3YoKTt9CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1jbyIpLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIscnVuT3YpOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY3NtIikuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5Pdik7CmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoIi5vdi1jciIpLmZvckVhY2goZnVuY3Rpb24oYyl7Yy5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk92KTt9KTsKCgovLyBXaXJlIGdydXBvIGNoZWNrYm94ZXMKZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLm92LWdyIikuZm9yRWFjaChmdW5jdGlvbihjKXtjLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIsZnVuY3Rpb24oKXsKICB2YXIgY2hlY2tlZD1bLi4uZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLm92LWdyOmNoZWNrZWQiKV0ubWFwKGZ1bmN0aW9uKHgpe3JldHVybiB4LnZhbHVlO30pOwogIGlmKGNoZWNrZWQubGVuZ3RoPT09MSkgdXBkYXRlQ2hhcnRNZW5zYWwoY2hlY2tlZFswXSk7CiAgZWxzZSB1cGRhdGVDaGFydE1lbnNhbCgiIik7CiAgcnVuT3YoKTsKfSk7fSk7CgovLyBJbml0IGNoYXJ0cwp2YXIgY2hhcnRNZW5zYWw9bnVsbCxjaGFydEdydXBvcz1udWxsOwpmdW5jdGlvbiBpbml0Q2hhcnRzKCl7CiAgdmFyIG1lc2VzPUNIQVJUUy5tZXNlcy5tYXAoZnVuY3Rpb24obSl7dmFyIHA9bS5zcGxpdCgnLScpO3JldHVybiBwWzFdKycvJytwWzBdLnNsaWNlKDIpO30pOwogIHZhciBDT0xPUl9MSU5FPScjM2I4MmY2JzsKICB2YXIgQ09MT1JTPVsnIzNiODJmNicsJyMwNTk2NjknLCcjZDk3NzA2JywnI2RjMjYyNicsJyM3YzNhZWQnLCcjZWE1ODBjJ107CgogIC8vIENoYXJ0IG1lbnNhbCDigJQgdG90YWwgdnMgYXRpdm9zCiAgdmFyIGN0eDE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImNoYXJ0LW1lbnNhbCIpLmdldENvbnRleHQoIjJkIik7CiAgY2hhcnRNZW5zYWw9bmV3IENoYXJ0KGN0eDEsewogICAgdHlwZToibGluZSIsCiAgICBkYXRhOnsKICAgICAgbGFiZWxzOm1lc2VzLAogICAgICBkYXRhc2V0czpbCiAgICAgICAgewogICAgICAgICAgbGFiZWw6IlRvdGFsIGhpc3TDs3JpY28iLAogICAgICAgICAgZGF0YTpDSEFSVFMuZXZvbHVjYW9fdG90YWwsCiAgICAgICAgICBib3JkZXJDb2xvcjoiIzk0YTNiOCIsYmFja2dyb3VuZENvbG9yOiJyZ2JhKDE0OCwxNjMsMTg0LC4wNikiLAogICAgICAgICAgYm9yZGVyV2lkdGg6Mixwb2ludFJhZGl1czozLHRlbnNpb246LjM1LGZpbGw6dHJ1ZSwKICAgICAgICAgIGJvcmRlckRhc2g6WzQsM10sCiAgICAgICAgICBkYXRhbGFiZWxzOntkaXNwbGF5OmZhbHNlfQogICAgICAgIH0sCiAgICAgICAgewogICAgICAgICAgbGFiZWw6IkVtcHJlc2FzIGF0aXZhcyBob2plIiwKICAgICAgICAgIGRhdGE6Q0hBUlRTLmV2b2x1Y2FvX2F0aXZvcywKICAgICAgICAgIGJvcmRlckNvbG9yOkNPTE9SX0xJTkUsYmFja2dyb3VuZENvbG9yOiJyZ2JhKDU5LDEzMCwyNDYsLjA4KSIsCiAgICAgICAgICBib3JkZXJXaWR0aDoyLjUscG9pbnRSYWRpdXM6NCxwb2ludEJhY2tncm91bmRDb2xvcjpDT0xPUl9MSU5FLHRlbnNpb246LjM1LGZpbGw6dHJ1ZSwKICAgICAgICAgIGRhdGFsYWJlbHM6e2Rpc3BsYXk6ZmFsc2V9CiAgICAgICAgfQogICAgICBdCiAgICB9LAogICAgb3B0aW9uczp7cmVzcG9uc2l2ZTp0cnVlLG1haW50YWluQXNwZWN0UmF0aW86ZmFsc2UsCiAgICAgIHBsdWdpbnM6ewogICAgICAgIGxlZ2VuZDp7ZGlzcGxheTp0cnVlLHBvc2l0aW9uOiJib3R0b20iLGxhYmVsczp7Zm9udDp7c2l6ZToxMH0sYm94V2lkdGg6MTIscGFkZGluZzo4fX0sCiAgICAgICAgdG9vbHRpcDp7bW9kZToiaW5kZXgiLGludGVyc2VjdDpmYWxzZX0KICAgICAgfSwKICAgICAgc2NhbGVzOnsKICAgICAgICB4OntncmlkOntkaXNwbGF5OmZhbHNlfSx0aWNrczp7Zm9udDp7c2l6ZToxMH0sbWF4Um90YXRpb246MH19LAogICAgICAgIHk6e2dyaWQ6e2NvbG9yOiJyZ2JhKDAsMCwwLC4wNCkifSx0aWNrczp7Zm9udDp7c2l6ZToxMH19LAogICAgICAgICAgIGFmdGVyRml0OmZ1bmN0aW9uKHMpe3Mud2lkdGg9NDA7fX0KICAgICAgfQogICAgfQogIH0pOwoKICAvLyBDaGFydCBncnVwb3Mg4oCUIGF0aXZvcyBjb20gdG9nZ2xlIHBvciBsaW5oYQogIHZhciBjdHgyPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjaGFydC1ncnVwb3MiKS5nZXRDb250ZXh0KCIyZCIpOwogIHZhciBncnVwb3NLZXlzPU9iamVjdC5rZXlzKENIQVJUUy5ncnVwb3NfYXRpdm9zKTsKICB2YXIgZHNHcnVwb3M9Z3J1cG9zS2V5cy5tYXAoZnVuY3Rpb24oZyxpKXsKICAgIHZhciBjb3I9Q09MT1JTW2klQ09MT1JTLmxlbmd0aF07CiAgICByZXR1cm4ge2xhYmVsOmcsZGF0YTpDSEFSVFMuZ3J1cG9zX2F0aXZvc1tnXSwKICAgICAgYm9yZGVyQ29sb3I6Y29yLGJhY2tncm91bmRDb2xvcjoidHJhbnNwYXJlbnQiLAogICAgICBib3JkZXJXaWR0aDoyLjUscG9pbnRSYWRpdXM6Myx0ZW5zaW9uOi4zNSxoaWRkZW46ZmFsc2V9OwogIH0pOwogIGNoYXJ0R3J1cG9zPW5ldyBDaGFydChjdHgyLHsKICAgIHR5cGU6ImxpbmUiLAogICAgZGF0YTp7bGFiZWxzOm1lc2VzLGRhdGFzZXRzOmRzR3J1cG9zfSwKICAgIG9wdGlvbnM6e3Jlc3BvbnNpdmU6dHJ1ZSxtYWludGFpbkFzcGVjdFJhdGlvOmZhbHNlLAogICAgICBwbHVnaW5zOnsKICAgICAgICBsZWdlbmQ6ewogICAgICAgICAgcG9zaXRpb246ImJvdHRvbSIsCiAgICAgICAgICBsYWJlbHM6e2ZvbnQ6e3NpemU6MTB9LGJveFdpZHRoOjEyLHBhZGRpbmc6MTB9LAogICAgICAgICAgb25DbGljazpmdW5jdGlvbihlLGl0ZW0sbGVnZW5kKXsKICAgICAgICAgICAgdmFyIGlkeD1pdGVtLmRhdGFzZXRJbmRleDsKICAgICAgICAgICAgdmFyIG1ldGE9Y2hhcnRHcnVwb3MuZ2V0RGF0YXNldE1ldGEoaWR4KTsKICAgICAgICAgICAgbWV0YS5oaWRkZW49IW1ldGEuaGlkZGVuOwogICAgICAgICAgICBjaGFydEdydXBvcy51cGRhdGUoKTsKICAgICAgICAgIH0KICAgICAgICB9LAogICAgICAgIHRvb2x0aXA6e21vZGU6ImluZGV4IixpbnRlcnNlY3Q6ZmFsc2V9CiAgICAgIH0sCiAgICAgIHNjYWxlczp7CiAgICAgICAgeDp7Z3JpZDp7ZGlzcGxheTpmYWxzZX0sdGlja3M6e2ZvbnQ6e3NpemU6MTB9LG1heFJvdGF0aW9uOjB9fSwKICAgICAgICB5OntncmlkOntjb2xvcjoicmdiYSgwLDAsMCwuMDQpIn0sdGlja3M6e2ZvbnQ6e3NpemU6MTB9fSwKICAgICAgICAgICBhZnRlckZpdDpmdW5jdGlvbihzKXtzLndpZHRoPTQwO319CiAgICAgIH0KICAgIH0KICB9KTsKICAvLyBUb2dnbGUgYnV0dG9ucyByZW5kZXJlZCBiZWxvdyBjaGFydAogIHZhciB0b2dnbGVIdG1sPSc8ZGl2IHN0eWxlPSJkaXNwbGF5OmZsZXg7Z2FwOjZweDtmbGV4LXdyYXA6d3JhcDtwYWRkaW5nOjhweCAwIDA7Ij4nOwogIGdydXBvc0tleXMuZm9yRWFjaChmdW5jdGlvbihnLGkpewogICAgdmFyIGNvcj1DT0xPUlNbaSVDT0xPUlMubGVuZ3RoXTsKICAgIHRvZ2dsZUh0bWwrPSc8YnV0dG9uIG9uY2xpY2s9InRvZ2dsZUdydXBvKCcraSsnKSIgaWQ9ImJ0bi1nci0nK2krJyIgc3R5bGU9IicrCiAgICAgICdiYWNrZ3JvdW5kOicrY29yKyc7Y29sb3I6I2ZmZjtib3JkZXI6bm9uZTtwYWRkaW5nOjNweCAxMHB4O2JvcmRlci1yYWRpdXM6MjBweDsnKwogICAgICAnZm9udC1zaXplOjExcHg7Zm9udC13ZWlnaHQ6NjAwO2N1cnNvcjpwb2ludGVyO2ZvbnQtZmFtaWx5OmluaGVyaXQ7b3BhY2l0eToxOyI+JytnKyc8L2J1dHRvbj4nOwogIH0pOwogIHRvZ2dsZUh0bWwrPSc8L2Rpdj4nOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJjaGFydC1ncnVwb3MiKS5pbnNlcnRBZGphY2VudEhUTUwoJ2FmdGVyZW5kJyx0b2dnbGVIdG1sKTsKCiAgLy8gUmV0ZW7Dp8OjbyByZW1vdmlkYQoKICAvLyBSYW5raW5nCiAgdmFyIG1heEF1bGFzPUNIQVJUUy5yYW5raW5nWzBdWzFdOwogIHZhciByYW5rSHRtbD0iIjsKICBDSEFSVFMucmFua2luZy5zbGljZSgwLDEyKS5mb3JFYWNoKGZ1bmN0aW9uKHIsaSl7CiAgICB2YXIgdz1NYXRoLnJvdW5kKHJbMV0vbWF4QXVsYXMqMTAwKTsKICAgIHJhbmtIdG1sKz0iPGRpdiBjbGFzcz1cInJhbmstcm93XCI+PHNwYW4gY2xhc3M9XCJyYW5rLW51bVwiPiIrKGkrMSkrIjwvc3Bhbj4iKwogICAgICAiPHNwYW4gY2xhc3M9XCJyYW5rLW5hbWVcIj4iK3JbMF0rIjwvc3Bhbj4iKwogICAgICAiPGRpdiBjbGFzcz1cInJhbmstYmFyLXdyYXBcIj48ZGl2IGNsYXNzPVwicmFuay1iYXItZmlsbFwiIHN0eWxlPVwid2lkdGg6Iit3KyIlXCI+PC9kaXY+PC9kaXY+IisKICAgICAgIjxzcGFuIGNsYXNzPVwicmFuay12YWxcIj4iK3JbMV0rIjwvc3Bhbj48L2Rpdj4iOwogIH0pOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJyYW5rLWJvZHkiKS5pbm5lckhUTUw9cmFua0h0bWw7CgogIC8vIG92LWNoYXJ0cyB2aXNpYmlsaXR5IGNvbnRyb2xsZWQgYnkgcGFyZW50IHBnLW92Cn0KCmZ1bmN0aW9uIHRvZ2dsZUdydXBvKGlkeCl7CiAgaWYoIWNoYXJ0R3J1cG9zKXJldHVybjsKICB2YXIgbWV0YT1jaGFydEdydXBvcy5nZXREYXRhc2V0TWV0YShpZHgpOwogIG1ldGEuaGlkZGVuPSFtZXRhLmhpZGRlbjsKICBjaGFydEdydXBvcy51cGRhdGUoKTsKICB2YXIgYnRuPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJidG4tZ3ItIitpZHgpOwogIGlmKGJ0bilidG4uc3R5bGUub3BhY2l0eT1tZXRhLmhpZGRlbj8iMC4zNSI6IjEiOwp9CmZ1bmN0aW9uIHVwZGF0ZUNoYXJ0TWVuc2FsKGdydXBvKXsKICBpZighY2hhcnRNZW5zYWwpcmV0dXJuOwogIGlmKCFncnVwbyl7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzBdLmRhdGE9Q0hBUlRTLmV2b2x1Y2FvX3RvdGFsOwogICAgY2hhcnRNZW5zYWwuZGF0YS5kYXRhc2V0c1swXS5sYWJlbD0iVG90YWwgaGlzdMOzcmljbyI7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzFdLmRhdGE9Q0hBUlRTLmV2b2x1Y2FvX2F0aXZvczsKICAgIGNoYXJ0TWVuc2FsLmRhdGEuZGF0YXNldHNbMV0ubGFiZWw9IkVtcHJlc2FzIGF0aXZhcyBob2plIjsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJncnVwby1zZWwtbGJsIikudGV4dENvbnRlbnQ9IiI7CiAgfWVsc2V7CiAgICB2YXIgdG90PUNIQVJUUy5ncnVwb3NfdG90YWxbZ3J1cG9dfHxbXTsKICAgIHZhciBhdHY9Q0hBUlRTLmdydXBvc19hdGl2b3NbZ3J1cG9dfHxbXTsKICAgIGNoYXJ0TWVuc2FsLmRhdGEuZGF0YXNldHNbMF0uZGF0YT10b3Q7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzBdLmxhYmVsPWdydXBvKyIgKHRvdGFsKSI7CiAgICBjaGFydE1lbnNhbC5kYXRhLmRhdGFzZXRzWzFdLmRhdGE9YXR2OwogICAgY2hhcnRNZW5zYWwuZGF0YS5kYXRhc2V0c1sxXS5sYWJlbD1ncnVwbysiIChhdGl2YXMpIjsKICAgIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJncnVwby1zZWwtbGJsIikudGV4dENvbnRlbnQ9IuKAlCAiK2dydXBvOwogIH0KICBjaGFydE1lbnNhbC51cGRhdGUoKTsKfQoKLy8gSG9vayBncnVwbyBmaWx0ZXIgaW50byBjaGFydApkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtZ3J1cG8iKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLGZ1bmN0aW9uKCl7CiAgdXBkYXRlQ2hhcnRNZW5zYWwodGhpcy52YWx1ZSk7Cn0pOwoKc2V0VGltZW91dChpbml0Q2hhcnRzLDEwMCk7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvdi1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY28iKS52YWx1ZT0iIjsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3YtY3NtIikudmFsdWU9IiI7CiAgZG9jdW1lbnQucXVlcnlTZWxlY3RvckFsbCgiLm92LWNyLC5vdi1nciIpLmZvckVhY2goZnVuY3Rpb24oYyl7Yy5jaGVja2VkPWZhbHNlO30pOwogIHVwZGF0ZUNoYXJ0TWVuc2FsKCIiKTsKICBvdkY9bnVsbDtydW5PdigpOwp9KTsKdmFyIHNlbENvPW51bGw7CmZ1bmN0aW9uIHJ1bkVtKCl7CiAgdmFyIHE9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLXEiKS52YWx1ZS50b0xvd2VyQ2FzZSgpLGNzbT1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tY3NtIikudmFsdWU7CiAgdmFyIGZkPUMuZmlsdGVyKGZ1bmN0aW9uKGMpe2lmKHEmJmMuZW1wcmVzYS50b0xvd2VyQ2FzZSgpLmluZGV4T2YocSk8MClyZXR1cm4gZmFsc2U7aWYoY3NtJiZjLmNzbSE9PWNzbSlyZXR1cm4gZmFsc2U7cmV0dXJuIHRydWU7fSk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLWN0YWciKS50ZXh0Q29udGVudD1mZC5sZW5ndGgrIiBlbXByZXNhcyI7CiAgdmFyIGNhcmRzPWZkLm1hcChmdW5jdGlvbihjbyxpZHgpewogICAgdmFyIHA9cGN0KGNvLmFjdGl2ZV9tLGNvLnRvdGFsKTsKICAgIHZhciBmYz1wPj03MD8idmFyKC0tZ3JlZW4pIjpwPj00MD8idmFyKC0teWVsKSI6InZhcigtLXJlZCkiOwogICAgdmFyIHBjMj1wPj03MD8icC1nIjpwPj00MD8icC15IjoicC1yIjsKICAgIHZhciBpc1NlbD0oc2VsQ289PT1pZHgpPyIgc2VsIjoiIjsKICAgIHJldHVybiAnPGRpdiBjbGFzcz0iY29jYXJkJytpc1NlbCsnIiBkYXRhLWVtcD0iJytlc2MoY28uZW1wcmVzYSkrJyIgZGF0YS1pZHg9IicraWR4KyciPicrCiAgICAgICc8ZGl2IGNsYXNzPSJjby10b3AiPjxkaXY+PGRpdiBjbGFzcz0iY28tbmFtZSI+Jytlc2MoY28uZW1wcmVzYSkrJzwvZGl2PjxkaXYgY2xhc3M9ImNvLWNzbSI+Jytlc2MoY28uY3NtfHwiU2VtIENTTSIpKyc8L2Rpdj48L2Rpdj4nKwogICAgICAnPHNwYW4gY2xhc3M9InBpbGwgJytwYzIrJyI+JytwKyclPC9zcGFuPjwvZGl2PicrCiAgICAgICc8ZGl2IGNsYXNzPSJjby1iYXIiPjxkaXYgY2xhc3M9ImNvLWJmIiBzdHlsZT0id2lkdGg6JytwKyclO2JhY2tncm91bmQ6JytmYysnIj48L2Rpdj48L2Rpdj4nKwogICAgICAnPGRpdiBjbGFzcz0iY28tc3RhdHMiPicrCiAgICAgICAgJzxzcGFuIGNsYXNzPSJjb3MiPjxzcGFuIGNsYXNzPSJkb3QgZC1vIj48L3NwYW4+Jytjby5vZmZlbnNpdmUrJzwvc3Bhbj4nKwogICAgICAgICc8c3BhbiBjbGFzcz0iY29zIj48c3BhbiBjbGFzcz0iZG90IGQtZyI+PC9zcGFuPicrY28uZ3JlZW4rJzwvc3Bhbj4nKwogICAgICAgICc8c3BhbiBjbGFzcz0iY29zIj48c3BhbiBjbGFzcz0iZG90IGQteSI+PC9zcGFuPicrY28ueWVsbG93Kyc8L3NwYW4+JysKICAgICAgICAnPHNwYW4gY2xhc3M9ImNvcyI+PHNwYW4gY2xhc3M9ImRvdCBkLXIiPjwvc3Bhbj4nK2NvLnJlZCsnPC9zcGFuPicrCiAgICAgICAgJzxzcGFuIGNsYXNzPSJjb3MiPjxzcGFuIGNsYXNzPSJkb3QgZC1rIj48L3NwYW4+Jytjby5ibGFjaysnPC9zcGFuPicrCiAgICAgICAgJzxzcGFuIHN0eWxlPSJmb250LXNpemU6MTBweDtjb2xvcjp2YXIoLS1nNDAwKTttYXJnaW4tbGVmdDphdXRvOyI+Jytjby50b3RhbCsnIHVzdVx4RTFyaW9zPC9zcGFuPicrCiAgICAgICc8L2Rpdj48L2Rpdj4nOwogIH0pLmpvaW4oJycpOwogIHZhciBkZXQ9Jyc7CiAgaWYoc2VsQ28hPT1udWxsJiZzZWxDbzxmZC5sZW5ndGgpewogICAgdmFyIHNlbEVtcHJlc2E9ZmRbc2VsQ29dLmVtcHJlc2E7CiAgICB2YXIgY3U9VS5maWx0ZXIoZnVuY3Rpb24odSl7cmV0dXJuIHUuY29tcGFueT09PXNlbEVtcHJlc2F8fHUuY29tcGFueS50b0xvd2VyQ2FzZSgpPT09c2VsRW1wcmVzYS50b0xvd2VyQ2FzZSgpO30pOwogICAgdmFyIHJvd3M9Y3UubWFwKGZ1bmN0aW9uKHUpewogICAgICByZXR1cm4gJzx0cj48dGQ+PGRpdiBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2ModS5uYW1lKSsnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij4nK2VzYyh1LmVtYWlsKSsnPC9kaXY+PC90ZD4nKwogICAgICAgICc8dGQ+JytmUGlsbCh1LmZsYWcpKyc8L3RkPjx0ZD4nKyh1LmRheXNfaW5hY3RpdmU+PTkwMDA/Ilx1MjAxNCI6dS5kYXlzX2luYWN0aXZlKyJkIikrJzwvdGQ+JysKICAgICAgICAnPHRkPicrZXNjKHUubGFzdF9jb25zdW1lZHx8Ilx1MjAxNCIpKyc8L3RkPjx0ZD4nK3UudG90YWxfY29uc3VtZWQrJzwvdGQ+PHRkPicrZXNjKHUuY3JlYXRlZF9hdHx8Ilx1MjAxNCIpKyc8L3RkPjwvdHI+JzsKICAgIH0pLmpvaW4oJycpOwogICAgZGV0PSc8ZGl2IGNsYXNzPSJkZXQiPjxkaXYgY2xhc3M9ImRldC10dGwiPjxzcGFuPicrZXNjKHNlbEVtcHJlc2EpKycgXHUyMDE0ICcrY3UubGVuZ3RoKycgdXN1XHhFMXJpb3M8L3NwYW4+JysKICAgICAgJzxzcGFuIGNsYXNzPSJjbHMiIG9uY2xpY2s9InNlbENvPW51bGw7cnVuRW0oKSI+JiMxMDAwNTs8L3NwYW4+PC9kaXY+JysKICAgICAgJzxkaXYgY2xhc3M9InRzY3IiPjx0YWJsZT48dGhlYWQ+PHRyPjx0aD5Vc3VceEUxcmlvPC90aD48dGg+RmxhZzwvdGg+PHRoPkluYXRpdm8gaFx4RTE8L3RoPjx0aD5ceERBbHRpbW8gY29uc3VtbzwvdGg+PHRoPlRvdGFsIGF1bGFzPC90aD48dGg+Q3JpYWRvIGVtPC90aD48L3RyPjwvdGhlYWQ+JysKICAgICAgJzx0Ym9keT4nK3Jvd3MrJzwvdGJvZHk+PC90YWJsZT48L2Rpdj48L2Rpdj4nOwogIH0KICAgIHZhciBfZW1iPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJlbS1ib2R5Iik7CiAgX2VtYi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9InNlYyI+JytmZC5sZW5ndGgrJyBFbXByZXNhczwvZGl2PicrZGV0Kyc8ZGl2IGNsYXNzPSJjb2dyaWQiIGlkPSJjb2dyaWQiPicrY2FyZHMrJzwvZGl2Pic7CiAgdmFyIF9jZz1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiY29ncmlkIik7CiAgaWYoX2NnKXtfY2cuYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLGZ1bmN0aW9uKGV2KXsKICAgIHZhciBjYXJkPWV2LnRhcmdldC5jbG9zZXN0P2V2LnRhcmdldC5jbG9zZXN0KCIuY29jYXJkIik6bnVsbDsKICAgIGlmKCFjYXJkKXJldHVybjsKICAgIHZhciBpPXBhcnNlSW50KGNhcmQuZ2V0QXR0cmlidXRlKCJkYXRhLWlkeCIpLDEwKTsKICAgIHNlbENvPShzZWxDbz09PWkpP251bGw6aTsKICAgIHJ1bkVtKCk7CiAgfSk7fQp9CmZ1bmN0aW9uIHBpY2tDbyhpKXtzZWxDbz0oc2VsQ289PT1pKT9udWxsOmk7cnVuRW0oKTt9CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJlbS1xIikuYWRkRXZlbnRMaXN0ZW5lcigiaW5wdXQiLHJ1bkVtKTsKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLWNzbSIpLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIscnVuRW0pOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tcnN0IikuYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLGZ1bmN0aW9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoImVtLXEiKS52YWx1ZT0iIjtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgiZW0tY3NtIikudmFsdWU9IiI7c2VsQ289bnVsbDtydW5FbSgpO30pOwpmdW5jdGlvbiBydW5VcygpewogIHZhciBxPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1xIikudmFsdWUudG9Mb3dlckNhc2UoKTsKICB2YXIgY289ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLWNvIikudmFsdWUsY3NtPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1jc20iKS52YWx1ZTsKICB2YXIgZmw9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLWZsIikudmFsdWUsY3I9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLWNyIikudmFsdWU7CiAgdmFyIGZkPVUuZmlsdGVyKGZ1bmN0aW9uKHUpewogICAgaWYocSYmdS5uYW1lLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwJiZ1LmVtYWlsLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwKXJldHVybiBmYWxzZTsKICAgIGlmKGNvJiZ1LmNvbXBhbnkhPT1jbylyZXR1cm4gZmFsc2U7aWYoY3NtJiZ1LmNzbSE9PWNzbSlyZXR1cm4gZmFsc2U7CiAgICBpZihmbCYmdS5mbGFnIT09ZmwpcmV0dXJuIGZhbHNlOwogICAgaWYoY3Ipe3ZhciBtPW1TaW5jZSh1LmNyZWF0ZWRfYXQpO2lmKGNyPT09Imx0MyImJm0+PTMpcmV0dXJuIGZhbHNlO2lmKGNyPT09IjN0bzYiJiYobTwzfHxtPjYpKXJldHVybiBmYWxzZTtpZihjcj09PSJndDYiJiZtPD02KXJldHVybiBmYWxzZTt9CiAgICByZXR1cm4gdHJ1ZTsKICB9KTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtY3RhZyIpLnRleHRDb250ZW50PWZkLmxlbmd0aCsiIHVzdVx4RTFyaW9zIjsKICB2YXIgcm93cz1mZC5zbGljZSgwLDUwMCkubWFwKGZ1bmN0aW9uKHUpewogICAgcmV0dXJuICc8dHI+PHRkPjxkaXYgc3R5bGU9ImZvbnQtd2VpZ2h0OjYwMDsiPicrZXNjKHUubmFtZSkrJzwvZGl2PjxkaXYgc3R5bGU9ImZvbnQtc2l6ZToxMXB4O2NvbG9yOnZhcigtLWc0MDApOyI+Jytlc2ModS5lbWFpbCkrJzwvZGl2PjwvdGQ+JysKICAgICAgJzx0ZD4nK2VzYyh1LmNvbXBhbnkpKyc8L3RkPjx0ZD4nK2VzYyh1LmNzbXx8Ilx1MjAxNCIpKyc8L3RkPjx0ZD4nK2ZQaWxsKHUuZmxhZykrJzwvdGQ+JysKICAgICAgJzx0ZD4nKyh1LmRheXNfaW5hY3RpdmU+PTkwMDA/Ilx1MjAxNCI6dS5kYXlzX2luYWN0aXZlKyIgZGlhcyIpKyc8L3RkPicrCiAgICAgICc8dGQ+Jytlc2ModS5sYXN0X2NvbnN1bWVkfHwiXHUyMDE0IikrJzwvdGQ+PHRkPicrdS50b3RhbF9jb25zdW1lZCsnPC90ZD48dGQ+Jytlc2ModS5jcmVhdGVkX2F0fHwiXHUyMDE0IikrJzwvdGQ+PC90cj4nOwogIH0pLmpvaW4oJycpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJ1cy1ib2R5IikuaW5uZXJIVE1MPQogICAgJzxkaXYgY2xhc3M9InR3cmFwIj48ZGl2IGNsYXNzPSJ0aGRyIj48ZGl2IGNsYXNzPSJ0dGwiPkxpc3RhIGRlIFVzdVx4RTFyaW9zPC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0Y250Ij4nKyhmZC5sZW5ndGg+NTAwPyI1MDAgZGUgIitmZC5sZW5ndGgrIiBcdTIwMTQgZmlsdHJlIHBhcmEgdmVyIG1haXMiOmZkLmxlbmd0aCsiIHVzdVx4RTFyaW9zIikrJzwvZGl2PjwvZGl2PicrCiAgICAnPGRpdiBjbGFzcz0idHNjciI+PHRhYmxlPjx0aGVhZD48dHI+PHRoPlVzdVx4RTFyaW88L3RoPjx0aD5FbXByZXNhPC90aD48dGg+Q1NNPC90aD48dGg+RmxhZzwvdGg+PHRoPkluYXRpdm8gaFx4RTE8L3RoPjx0aD5ceERBbHRpbW8gY29uc3VtbzwvdGg+PHRoPlRvdGFsIGF1bGFzPC90aD48dGg+Q3JpYWRvIGVtPC90aD48L3RyPjwvdGhlYWQ+JysKICAgICc8dGJvZHk+Jytyb3dzKyc8L3Rib2R5PjwvdGFibGU+PC9kaXY+PC9kaXY+JzsKfQpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtcSIpLmFkZEV2ZW50TGlzdGVuZXIoImlucHV0IixydW5Vcyk7ClsidXMtY28iLCJ1cy1jc20iLCJ1cy1mbCIsInVzLWNyIl0uZm9yRWFjaChmdW5jdGlvbihpZCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpLmFkZEV2ZW50TGlzdGVuZXIoImNoYW5nZSIscnVuVXMpO30pOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgidXMtcnN0IikuYWRkRXZlbnRMaXN0ZW5lcigiY2xpY2siLGZ1bmN0aW9uKCl7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoInVzLXEiKS52YWx1ZT0iIjtbInVzLWNvIiwidXMtY3NtIiwidXMtZmwiLCJ1cy1jciJdLmZvckVhY2goZnVuY3Rpb24oaWQpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKGlkKS52YWx1ZT0iIjt9KTtydW5VcygpO30pOwpmdW5jdGlvbiBydW5OYSgpewogIHZhciBxPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1xIikudmFsdWUudG9Mb3dlckNhc2UoKTsKICB2YXIgY289ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5hLWNvIikudmFsdWUsY3NtPWRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1jc20iKS52YWx1ZTsKICB2YXIgZmQ9TlYuZmlsdGVyKGZ1bmN0aW9uKHUpewogICAgaWYocSYmdS5uYW1lLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwJiZ1LmVtYWlsLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwKXJldHVybiBmYWxzZTsKICAgIGlmKGNvJiZ1LmNvbXBhbnkhPT1jbylyZXR1cm4gZmFsc2U7aWYoY3NtJiZ1LmNzbSE9PWNzbSlyZXR1cm4gZmFsc2U7cmV0dXJuIHRydWU7CiAgfSk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5hLWN0YWciKS50ZXh0Q29udGVudD1mZC5sZW5ndGgrIiB1c3VceEUxcmlvcyI7CiAgdmFyIGtwaXM9JzxkaXYgY2xhc3M9Imtyb3cgazMiIHN0eWxlPSJtYXJnaW4tYm90dG9tOjE2cHg7Ij4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+TnVuY2EgYXNzaXN0aXJhbTwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy15Ij4nK2ZkLmxlbmd0aCsnPC9kaXY+PGRpdiBjbGFzcz0ia3N1YiI+dXN1XHhFMXJpb3MgY2FkYXN0cmFkb3M8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+RW1wcmVzYXMgYWZldGFkYXM8L2Rpdj48ZGl2IGNsYXNzPSJrdmFsIGMtYiI+JytbLi4ubmV3IFNldChmZC5tYXAoZnVuY3Rpb24odSl7cmV0dXJuIHUuY29tcGFueTt9KSldLmxlbmd0aCsnPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJrcGkiPjxkaXYgY2xhc3M9ImtsYmwiPkNTTXMgZW52b2x2aWRvczwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1rIj4nK1suLi5uZXcgU2V0KGZkLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jc207fSkuZmlsdGVyKEJvb2xlYW4pKV0ubGVuZ3RoKyc8L2Rpdj48L2Rpdj4nKwogICc8L2Rpdj4nOwogIHZhciByb3dzPWZkLnNsaWNlKDAsNTAwKS5tYXAoZnVuY3Rpb24odSl7CiAgICByZXR1cm4gJzx0cj48dGQ+PGRpdiBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2ModS5uYW1lKSsnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij4nK2VzYyh1LmVtYWlsKSsnPC9kaXY+PC90ZD4nKwogICAgICAnPHRkPicrZXNjKHUuY29tcGFueSkrJzwvdGQ+PHRkPicrZXNjKHUuY3NtfHwiXHUyMDE0IikrJzwvdGQ+PHRkPicrZXNjKHUuY3JlYXRlZF9hdHx8Ilx1MjAxNCIpKyc8L3RkPjwvdHI+JzsKICB9KS5qb2luKCcnKTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmEtYm9keSIpLmlubmVySFRNTD1rcGlzKwogICAgJzxkaXYgY2xhc3M9InR3cmFwIj48ZGl2IGNsYXNzPSJ0aGRyIj48ZGl2IGNsYXNzPSJ0dGwiPkNhZGFzdHJhZG9zIHF1ZSBudW5jYSBhc3Npc3RpcmFtPC9kaXY+PGRpdiBjbGFzcz0idGNudCI+JytmZC5sZW5ndGgrJyB1c3VceEUxcmlvczwvZGl2PjwvZGl2PicrCiAgICAnPGRpdiBjbGFzcz0idHNjciI+PHRhYmxlPjx0aGVhZD48dHI+PHRoPlVzdVx4RTFyaW88L3RoPjx0aD5FbXByZXNhPC90aD48dGg+Q1NNPC90aD48dGg+Q3JpYWRvIGVtPC90aD48L3RyPjwvdGhlYWQ+JysKICAgICc8dGJvZHk+Jytyb3dzKyc8L3Rib2R5PjwvdGFibGU+PC9kaXY+PC9kaXY+JzsKfQpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmEtcSIpLmFkZEV2ZW50TGlzdGVuZXIoImlucHV0IixydW5OYSk7ClsibmEtY28iLCJuYS1jc20iXS5mb3JFYWNoKGZ1bmN0aW9uKGlkKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5OYSk7fSk7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuYS1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmEtcSIpLnZhbHVlPSIiO1sibmEtY28iLCJuYS1jc20iXS5mb3JFYWNoKGZ1bmN0aW9uKGlkKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCkudmFsdWU9IiI7fSk7cnVuTmEoKTt9KTsKZnVuY3Rpb24gcnVuTmYoKXsKICB2YXIgcT1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtcSIpLnZhbHVlLnRvTG93ZXJDYXNlKCk7CiAgdmFyIGNvbnM9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5mLWNvbnMiKS52YWx1ZTsKICB2YXIgZmQ9TkYuZmlsdGVyKGZ1bmN0aW9uKGMpewogICAgaWYocSYmYy5lbXByZXNhLnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwKXJldHVybiBmYWxzZTsKICAgIGlmKGNvbnM9PT0ic2ltIiYmIWMudGV2ZV9jb25zdW1vKXJldHVybiBmYWxzZTsKICAgIGlmKGNvbnM9PT0ibmFvIiYmYy50ZXZlX2NvbnN1bW8pcmV0dXJuIGZhbHNlOwogICAgcmV0dXJuIHRydWU7CiAgfSk7CiAgZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm5mLWN0YWciKS50ZXh0Q29udGVudD1mZC5sZW5ndGgrIiBlbXByZXNhcyI7CiAgdmFyIGtwaXM9JzxkaXYgY2xhc3M9Imtyb3cgazMiIHN0eWxlPSJtYXJnaW4tYm90dG9tOjE2cHg7Ij4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+VG90YWwgZW1wcmVzYXM8L2Rpdj48ZGl2IGNsYXNzPSJrdmFsIGMtcCI+JytmZC5sZW5ndGgrJzwvZGl2PjxkaXYgY2xhc3M9ImtzdWIiPm5ceEUzbyBlbmNvbnRyYWRhcyBjb21vIGF0aXZhczwvZGl2PjwvZGl2PicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5Db20gY29uc3VtbyBkZSBhdWxhczwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1vIj4nK2ZkLmZpbHRlcihmdW5jdGlvbihjKXtyZXR1cm4gYy50ZXZlX2NvbnN1bW87fSkubGVuZ3RoKyc8L2Rpdj48L2Rpdj4nKwogICAgJzxkaXYgY2xhc3M9ImtwaSI+PGRpdiBjbGFzcz0ia2xibCI+VXN1XHhFMXJpb3MgbmVzdGFzIGVtcHJlc2FzPC9kaXY+PGRpdiBjbGFzcz0ia3ZhbCBjLWIiPicrZmQucmVkdWNlKGZ1bmN0aW9uKGEsYyl7cmV0dXJuIGErYy50b3RhbDt9LDApKyc8L2Rpdj48L2Rpdj4nKwogICc8L2Rpdj4nOwogIHZhciByb3dzPWZkLm1hcChmdW5jdGlvbihjKXsKICAgIHJldHVybiAnPHRyPjx0ZCBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2MoYy5lbXByZXNhKSsnPC90ZD4nKwogICAgICAnPHRkIHN0eWxlPSJmb250LXdlaWdodDo3MDA7dGV4dC1hbGlnbjpjZW50ZXI7Ij4nK2MudG90YWwrJzwvdGQ+JysKICAgICAgJzx0ZD4nKyhjLnRldmVfY29uc3Vtbz8nPHNwYW4gY2xhc3M9InBpbGwgcC1nIj4mIzEwMDAzOyBTaW08L3NwYW4+JzonPHNwYW4gY2xhc3M9InBpbGwgcC1nciI+Tlx4RTNvPC9zcGFuPicpKyc8L3RkPjwvdHI+JzsKICB9KS5qb2luKCcnKTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtYm9keSIpLmlubmVySFRNTD1rcGlzKwogICAgJzxkaXYgY2xhc3M9Imlib3ggaWJveC1wIj4mIzEwMDY3OyBFbXByZXNhcyBjb20gdXN1XHhFMXJpb3MgY2FkYXN0cmFkb3MgcXVlIG5ceEUzbyBlc3RceEUzbyBuYSBiYXNlIGRlIGNsaWVudGVzIGNvbW8gPHN0cm9uZz5BdGl2YXM8L3N0cm9uZz4uIE1hcGVpZSBlIGNhZGFzdHJlIGFzIHF1ZSBmb3JlbSBjbGllbnRlcyBhdGl2b3MuPC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0d3JhcCI+PGRpdiBjbGFzcz0idGhkciI+PGRpdiBjbGFzcz0idHRsIj5FbXByZXNhcyBuXHhFM28gbWFwZWFkYXM8L2Rpdj48ZGl2IGNsYXNzPSJ0Y250Ij4nK2ZkLmxlbmd0aCsnIGVtcHJlc2FzPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0c2NyIj48dGFibGU+PHRoZWFkPjx0cj48dGg+RW1wcmVzYTwvdGg+PHRoPlVzdVx4RTFyaW9zPC90aD48dGg+Q29uc3VtaXUgYXVsYXM/PC90aD48L3RyPjwvdGhlYWQ+JysKICAgICc8dGJvZHk+Jytyb3dzKyc8L3Rib2R5PjwvdGFibGU+PC9kaXY+PC9kaXY+JzsKfQpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtcSIpLmFkZEV2ZW50TGlzdGVuZXIoImlucHV0IixydW5OZik7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1jb25zIikuYWRkRXZlbnRMaXN0ZW5lcigiY2hhbmdlIixydW5OZik7CmRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1yc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjbGljayIsZnVuY3Rpb24oKXtkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgibmYtcSIpLnZhbHVlPSIiO2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJuZi1jb25zIikudmFsdWU9IiI7cnVuTmYoKTt9KTsKZnVuY3Rpb24gcnVuT3IoKXsKICB2YXIgcT1kb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3ItcSIpLnZhbHVlLnRvTG93ZXJDYXNlKCksc3Q9ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLXN0IikudmFsdWU7CiAgdmFyIHNpeEFnbz1uZXcgRGF0ZSgpO3NpeEFnby5zZXRNb250aChzaXhBZ28uZ2V0TW9udGgoKS02KTsKICB2YXIgZmQ9T1IuZmlsdGVyKGZ1bmN0aW9uKHUpewogICAgaWYodS5jb19zdGF0dXM9PT0iQ2h1cm4iKXt2YXIgcmVjZW50PXUubGFzdF9jb25zdW1lZCYmbmV3IERhdGUodS5sYXN0X2NvbnN1bWVkKT49c2l4QWdvO2lmKCFyZWNlbnQpcmV0dXJuIGZhbHNlO30KICAgIGlmKHEmJnUubmFtZS50b0xvd2VyQ2FzZSgpLmluZGV4T2YocSk8MCYmdS5lbWFpbC50b0xvd2VyQ2FzZSgpLmluZGV4T2YocSk8MCYmdS5jb21wYW55LnRvTG93ZXJDYXNlKCkuaW5kZXhPZihxKTwwKXJldHVybiBmYWxzZTsKICAgIGlmKHN0JiZ1LmNvX3N0YXR1cyE9PXN0KXJldHVybiBmYWxzZTtyZXR1cm4gdHJ1ZTsKICB9KTsKICBkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3ItY3RhZyIpLnRleHRDb250ZW50PWZkLmxlbmd0aCsiIHVzdVx4RTFyaW9zIjsKICB2YXIga3Bpcz0nPGRpdiBjbGFzcz0ia3JvdyBrMiIgc3R5bGU9Im1hcmdpbi1ib3R0b206MTZweDsiPicrCiAgICAnPGRpdiBjbGFzcz0ia3BpIj48ZGl2IGNsYXNzPSJrbGJsIj5Vc3VceEUxcmlvcyBmb3JhIGRvIGRhc2hib2FyZDwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1wIj4nK2ZkLmxlbmd0aCsnPC9kaXY+PGRpdiBjbGFzcz0ia3N1YiI+ZW1wcmVzYSBuXHhFM28gZXN0XHhFMSBhdGl2YSBuYSBiYXNlPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJrcGkiPjxkaXYgY2xhc3M9ImtsYmwiPkVtcHJlc2FzIGRpc3RpbnRhczwvZGl2PjxkaXYgY2xhc3M9Imt2YWwgYy1iIj4nK1suLi5uZXcgU2V0KGZkLm1hcChmdW5jdGlvbih1KXtyZXR1cm4gdS5jb21wYW55O30pKV0ubGVuZ3RoKyc8L2Rpdj48L2Rpdj4nKwogICc8L2Rpdj4nOwogIHZhciByb3dzPWZkLnNsaWNlKDAsNTAwKS5tYXAoZnVuY3Rpb24odSl7CiAgICByZXR1cm4gJzx0cj48dGQ+PGRpdiBzdHlsZT0iZm9udC13ZWlnaHQ6NjAwOyI+Jytlc2ModS5uYW1lKSsnPC9kaXY+PGRpdiBzdHlsZT0iZm9udC1zaXplOjExcHg7Y29sb3I6dmFyKC0tZzQwMCk7Ij4nK2VzYyh1LmVtYWlsKSsnPC9kaXY+PC90ZD4nKwogICAgICAnPHRkPicrZXNjKHUuY29tcGFueSkrJzwvdGQ+PHRkPicrc3RQaWxsKHUuY29fc3RhdHVzKSsnPC90ZD4nKwogICAgICAnPHRkPicrKHUudG90YWxfY29uc3VtZWQ+MD8nPHNwYW4gY2xhc3M9InBpbGwgcC1nIj4mIzEwMDAzOyBTaW0gKCcrdS50b3RhbF9jb25zdW1lZCsnKTwvc3Bhbj4nOic8c3BhbiBjbGFzcz0icGlsbCBwLWdyIj5OXHhFM288L3NwYW4+JykrJzwvdGQ+PC90cj4nOwogIH0pLmpvaW4oJycpOwogIGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvci1ib2R5IikuaW5uZXJIVE1MPWtwaXMrCiAgICAnPGRpdiBjbGFzcz0iaWJveCBpYm94LXkiPiYjOTg4ODsmIzY1MDM5OyBVc3VceEUxcmlvcyBxdWUgY29uc3VtaXJhbSBhdWxhcyBub3MgXHhGQWx0aW1vcyAzIG1lc2VzIG1hcyBjdWphIGVtcHJlc2Egblx4RTNvIGVzdFx4RTEgYXRpdmEgbmEgYmFzZS4gQ29ycmlqYSBvIHN0YXR1cyBvdSBhZGljaW9uZSB1bSBhbGlhcyBubyBzY3JpcHQuPC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0d3JhcCI+PGRpdiBjbGFzcz0idGhkciI+PGRpdiBjbGFzcz0idHRsIj5Vc3VceEUxcmlvcyBmb3JhIGRvIGRhc2hib2FyZCBwcmluY2lwYWw8L2Rpdj48ZGl2IGNsYXNzPSJ0Y250Ij4nKyhmZC5sZW5ndGg+NTAwPyI1MDAgZGUgIitmZC5sZW5ndGg6ZmQubGVuZ3RoKyIgdXN1XHhFMXJpb3MiKSsnPC9kaXY+PC9kaXY+JysKICAgICc8ZGl2IGNsYXNzPSJ0c2NyIj48dGFibGU+PHRoZWFkPjx0cj48dGg+VXN1XHhFMXJpbzwvdGg+PHRoPkVtcHJlc2E8L3RoPjx0aD5TdGF0dXMgZW1wcmVzYTwvdGg+PHRoPkNvbnN1bWl1IGF1bGFzPzwvdGg+PC90cj48L3RoZWFkPicrCiAgICAnPHRib2R5Picrcm93cysnPC90Ym9keT48L3RhYmxlPjwvZGl2PjwvZGl2Pic7Cn0KZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLXEiKS5hZGRFdmVudExpc3RlbmVyKCJpbnB1dCIscnVuT3IpOwpkb2N1bWVudC5nZXRFbGVtZW50QnlJZCgib3Itc3QiKS5hZGRFdmVudExpc3RlbmVyKCJjaGFuZ2UiLHJ1bk9yKTsKZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLXJzdCIpLmFkZEV2ZW50TGlzdGVuZXIoImNsaWNrIixmdW5jdGlvbigpe2RvY3VtZW50LmdldEVsZW1lbnRCeUlkKCJvci1xIikudmFsdWU9IiI7ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoIm9yLXN0IikudmFsdWU9IiI7cnVuT3IoKTt9KTsKcnVuT3YoKTtydW5FbSgpO3J1blVzKCk7cnVuTmEoKTtydW5OZigpO3J1bk9yKCk7Cg==").decode('utf-8')

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
