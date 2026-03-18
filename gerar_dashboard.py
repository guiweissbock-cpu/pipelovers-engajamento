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

    CSS = '\n:root{--navy:#0f2952;--mid:#2563b0;--sky:#3b82f6;--sky-l:#eff6ff;--sky-p:#f8faff;--g50:#f9fafb;--g100:#f1f5f9;--g200:#e2e8f0;--g400:#94a3b8;--g500:#64748b;--g600:#475569;--g700:#334155;--g800:#1e293b;--green:#059669;--gl:#ecfdf5;--gb:#6ee7b7;--yel:#d97706;--yl:#fffbeb;--yb:#fcd34d;--red:#dc2626;--rl:#fef2f2;--rb:#fca5a5;--blk:#334155;--bkl:#f8fafc;--bkb:#94a3b8;--ora:#ea580c;--ol:#fff7ed;--ob:#fdba74;--pur:#7c3aed;--pl:#f5f3ff;--pb:#c4b5fd;--r:12px;--sh:0 1px 3px rgba(15,41,82,.07),0 1px 2px rgba(15,41,82,.04);}\n*{box-sizing:border-box;margin:0;padding:0;}\nbody{font-family:"Plus Jakarta Sans",sans-serif;background:var(--g50);color:var(--g800);min-height:100vh;font-size:14px;}\n.hdr{background:var(--navy);height:56px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:400;box-shadow:0 2px 10px rgba(15,41,82,.2);}\n.brand{display:flex;align-items:center;gap:10px;}.bico{width:30px;height:30px;background:var(--sky);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;}.bname{font-size:16px;font-weight:700;color:#fff;}.btag{font-size:11px;color:rgba(255,255,255,.4);margin-top:1px;}.upd{font-size:11px;color:rgba(255,255,255,.35);}\n.nav{background:#fff;border-bottom:1px solid var(--g200);padding:0 24px;display:flex;position:sticky;top:56px;z-index:300;box-shadow:var(--sh);overflow-x:auto;}\n.ntab{padding:13px 16px;font-size:13px;font-weight:600;color:var(--g500);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;white-space:nowrap;}.ntab:hover{color:var(--mid);}.ntab.on{color:var(--mid);border-bottom-color:var(--sky);}\n.fbar{background:#fff;border-bottom:1px solid var(--g200);padding:10px 24px;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;}\n.fg{display:flex;flex-direction:column;gap:3px;}.fl{font-size:10px;font-weight:700;color:var(--g400);text-transform:uppercase;letter-spacing:.5px;}\nselect,input[type=text]{background:var(--g50);border:1.5px solid var(--g200);color:var(--g800);padding:6px 10px;border-radius:7px;font-size:12px;font-family:inherit;outline:none;min-width:140px;transition:border-color .15s;}\nselect:focus,input:focus{border-color:var(--sky);background:#fff;}\n.btnf{background:#fff;border:1.5px solid var(--g200);color:var(--g600);padding:6px 12px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;align-self:flex-end;}.btnf:hover{border-color:var(--sky);color:var(--mid);}\n.ctag{font-size:12px;font-weight:600;color:var(--mid);background:var(--sky-l);border:1px solid #bfdbfe;padding:4px 10px;border-radius:20px;align-self:flex-end;}\n.pg{display:none;padding:20px 24px;}.pg.on{display:block;}\n.krow{display:grid;gap:12px;margin-bottom:20px;}.k6{grid-template-columns:repeat(6,1fr);}.k3{grid-template-columns:repeat(3,1fr);max-width:520px;}.k2{grid-template-columns:repeat(2,1fr);max-width:360px;}\n.kpi{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh);}.kpi.clk{cursor:pointer;transition:all .15s;}.kpi.clk:hover{border-color:var(--sky);box-shadow:0 4px 16px rgba(15,41,82,.1);}.kpi.sel{border-color:var(--sky);box-shadow:0 0 0 3px rgba(59,130,246,.12);}\n.klbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--g400);margin-bottom:6px;}.kval{font-size:24px;font-weight:800;line-height:1;letter-spacing:-.5px;}.ksub{font-size:11px;color:var(--g400);margin-top:3px;}\n.c-b{color:var(--mid);}.c-g{color:var(--green);}.c-y{color:var(--yel);}.c-r{color:var(--red);}.c-k{color:var(--blk);}.c-o{color:var(--ora);}.c-p{color:var(--pur);}\n.sec{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--g400);margin-bottom:10px;display:flex;align-items:center;gap:8px;}.sec::after{content:"";flex:1;height:1px;background:var(--g200);}\n.twrap{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);margin-bottom:20px;}\n.thdr{padding:12px 16px;border-bottom:1px solid var(--g100);display:flex;justify-content:space-between;align-items:center;}.ttl{font-size:13px;font-weight:700;color:var(--g700);}.tcnt{font-size:12px;color:var(--g400);}\n.tscr{overflow-x:auto;max-height:520px;overflow-y:auto;}\ntable{width:100%;border-collapse:collapse;}th{padding:9px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--g400);background:var(--g50);border-bottom:1px solid var(--g200);white-space:nowrap;position:sticky;top:0;z-index:1;}\ntd{padding:10px 12px;font-size:12px;border-bottom:1px solid var(--g100);vertical-align:middle;}tr:last-child td{border-bottom:none;}tr:hover td{background:var(--sky-p);}\n.pill{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap;}\n.p-o{background:var(--ol);color:var(--ora);border:1px solid var(--ob);}.p-g{background:var(--gl);color:var(--green);border:1px solid var(--gb);}.p-y{background:var(--yl);color:var(--yel);border:1px solid var(--yb);}.p-r{background:var(--rl);color:var(--red);border:1px solid var(--rb);}.p-k{background:var(--bkl);color:var(--blk);border:1px solid var(--bkb);}.p-p{background:var(--pl);color:var(--pur);border:1px solid var(--pb);}.p-gr{background:var(--g100);color:var(--g500);border:1px solid var(--g200);}\n.cogrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}\n.cocard{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh);cursor:pointer;transition:all .15s;}.cocard:hover{border-color:var(--sky);box-shadow:0 4px 14px rgba(15,41,82,.1);}.cocard.sel{border-color:var(--sky);box-shadow:0 0 0 3px rgba(59,130,246,.12);}\n.co-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;}.co-name{font-size:13px;font-weight:700;color:var(--navy);line-height:1.2;}.co-csm{font-size:10px;color:var(--g400);margin-top:2px;}\n.co-bar{height:4px;background:var(--g100);border-radius:2px;overflow:hidden;margin:8px 0 6px;}.co-bf{height:100%;border-radius:2px;}\n.co-stats{display:flex;gap:5px;flex-wrap:wrap;}.cos{display:flex;align-items:center;gap:3px;font-size:10px;font-weight:600;}\n.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}.d-o{background:var(--ora);}.d-g{background:var(--green);}.d-y{background:var(--yel);}.d-r{background:var(--red);}.d-k{background:var(--blk);}\n.det{background:#fff;border:1.5px solid var(--sky);border-radius:var(--r);padding:16px 20px;margin-bottom:20px;box-shadow:0 0 0 3px rgba(59,130,246,.08);}\n.det-ttl{font-size:14px;font-weight:700;color:var(--navy);margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;}\n.cls{cursor:pointer;color:var(--g400);font-size:18px;line-height:1;}.cls:hover{color:var(--g700);}\n.ibox{border-radius:var(--r);padding:12px 16px;margin-bottom:16px;font-size:13px;font-weight:500;}\n.ibox-p{background:var(--pl);border:1.5px solid var(--pb);color:var(--pur);}.ibox-y{background:var(--yl);border:1.5px solid var(--yb);color:var(--yel);}\n.ck-group{display:flex;flex-direction:column;gap:4px;padding:4px 0;}\n.ck-lbl{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--g600);cursor:pointer;white-space:nowrap;}\n.ck-lbl input[type=checkbox]{width:14px;height:14px;accent-color:var(--sky);cursor:pointer;flex-shrink:0;}\n.ck-lbl:hover{color:var(--mid);}\n.chart-section{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);padding:18px 22px;margin:0 24px 20px;box-shadow:var(--sh);}\n.chart-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.7px;color:var(--g400);margin-bottom:14px;display:flex;align-items:center;justify-content:space-between;}\n.chart-canvas-wrap{position:relative;height:180px;}\n.rank-list{display:flex;flex-direction:column;gap:6px;}\n.rank-row{display:flex;align-items:center;gap:10px;font-size:12px;}\n.rank-num{width:18px;font-weight:700;color:var(--g400);text-align:right;flex-shrink:0;}\n.rank-name{flex:1;font-weight:600;color:var(--g700);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}\n.rank-bar-wrap{width:120px;height:6px;background:var(--g100);border-radius:3px;overflow:hidden;flex-shrink:0;}\n.rank-bar-fill{height:100%;border-radius:3px;background:var(--sky);}\n.rank-val{width:40px;text-align:right;font-weight:700;color:var(--mid);flex-shrink:0;}\n.charts-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;padding:0 24px 20px;}\n.charts-grid-3{display:grid;grid-template-columns:2fr 1fr;gap:16px;padding:0 24px 20px;}\n.ret-grid{display:flex;gap:10px;flex-wrap:wrap;}\n.ret-card{flex:1;min-width:80px;background:var(--g50);border-radius:8px;padding:10px 12px;text-align:center;}\n.ret-pct{font-size:22px;font-weight:800;color:var(--mid);}\n.ret-mes{font-size:10px;color:var(--g400);margin-top:2px;}\n.ret-sub{font-size:10px;color:var(--g500);margin-top:1px;}\n::-webkit-scrollbar{width:5px;height:5px;}::-webkit-scrollbar-track{background:transparent;}::-webkit-scrollbar-thumb{background:var(--g200);border-radius:3px;}\n'
    BODY = '\n<div class="hdr">\n  <div class="brand"><div class="bico">PL</div><div><div class="bname">PipeLovers</div><div class="btag">Dashboard de Engajamento</div></div></div>\n  <span class="upd" id="upd-lbl"></span>\n</div>\n<div class="nav">\n  <div class="ntab on" onclick="goTab(\'ov\',this)">&#128202; Overview</div>\n  <div class="ntab"    onclick="goTab(\'em\',this)">&#127970; Empresas</div>\n  <div class="ntab"    onclick="goTab(\'us\',this)">&#128100; Usu&aacute;rios</div>\n  <div class="ntab"    onclick="goTab(\'na\',this)">&#9888;&#65039; Nunca Assistiram</div>\n  <div class="ntab"    onclick="goTab(\'nf\',this)">&#10067; Empresas s/ cadastro</div>\n  <div class="ntab"    onclick="goTab(\'or\',this)">&#128100; Usu&aacute;rios s/ empresa</div>\n</div>\n<div id="pg-ov" class="pg on">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Empresa</div><select id="ov-co"><option value="">Todas</option></select></div>\n    <div class="fg"><div class="fl">CSM</div><select id="ov-csm"><option value="">Todos</option></select></div>\n    <div class="fg">\n      <div class="fl">Cria&ccedil;&atilde;o do usu&aacute;rio</div>\n      <div class="ck-group">\n        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="lt3"> Menos de 3 meses</label>\n        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="3to6"> 3 a 6 meses</label>\n        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="gt6"> Mais de 6 meses</label>\n        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="nodate"> Sem data</label>\n      </div>\n    </div>\n    <div class="fg">\n      <div class="fl">Grupo / Plano</div>\n      <select id="ov-grupo"><option value="">Todos</option></select>\n    </div>\n    <button class="btnf" id="ov-rst">Limpar</button>\n  </div>\n  <div id="ov-body"></div>\n</div>\n\n<div id="ov-charts" style="display:none;">\n  <div class="charts-grid-3">\n    <div class="chart-section" style="margin:0;">\n      <div class="chart-title">Usuários únicos por mês <span id="grupo-sel-lbl" style="font-size:10px;color:var(--sky);"></span></div>\n      <div class="chart-canvas-wrap"><canvas id="chart-mensal"></canvas></div>\n    </div>\n    <div class="chart-section" style="margin:0;">\n      <div class="chart-title">Retenção mês a mês</div>\n      <div id="ret-body"></div>\n    </div>\n  </div>\n  <div class="charts-grid">\n    <div class="chart-section" style="margin:0;">\n      <div class="chart-title">Evolução por grupo</div>\n      <div class="chart-canvas-wrap"><canvas id="chart-grupos"></canvas></div>\n    </div>\n    <div class="chart-section" style="margin:0;">\n      <div class="chart-title">Top empresas (últimos 3 meses) <span style="font-size:10px;color:var(--g400);font-weight:400;">por nº de aulas</span></div>\n      <div class="rank-list" id="rank-body"></div>\n    </div>\n  </div>\n</div>\n<div id="pg-em" class="pg">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Buscar</div><input type="text" id="em-q" placeholder="Nome da empresa..."></div>\n    <div class="fg"><div class="fl">CSM</div><select id="em-csm"><option value="">Todos</option></select></div>\n    <button class="btnf" id="em-rst">Limpar</button>\n    <div class="ctag" id="em-ctag"></div>\n  </div>\n  <div id="em-body" style="padding:20px 24px;"></div>\n</div>\n<div id="pg-us" class="pg">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Buscar</div><input type="text" id="us-q" placeholder="Nome ou e-mail..."></div>\n    <div class="fg"><div class="fl">Empresa</div><select id="us-co"><option value="">Todas</option></select></div>\n    <div class="fg"><div class="fl">CSM</div><select id="us-csm"><option value="">Todos</option></select></div>\n    <div class="fg"><div class="fl">Flag</div>\n      <select id="us-fl">\n        <option value="">Todas</option>\n        <option value="offensive">&#128293; Ofensiva</option>\n        <option value="green">&#128994; Green</option>\n        <option value="yellow">&#128993; Yellow</option>\n        <option value="red">&#128308; Red</option>\n        <option value="black">&#9899; Black</option>\n      </select>\n    </div>\n    <div class="fg"><div class="fl">Cria&ccedil;&atilde;o</div>\n      <select id="us-cr">\n        <option value="">Qualquer</option>\n        <option value="lt3">Menos de 3 meses</option>\n        <option value="3to6">3 a 6 meses</option>\n        <option value="gt6">Mais de 6 meses</option>\n      </select>\n    </div>\n    <button class="btnf" id="us-rst">Limpar</button>\n    <div class="ctag" id="us-ctag"></div>\n  </div>\n  <div id="us-body" style="padding:20px 24px;"></div>\n</div>\n<div id="pg-na" class="pg">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Buscar</div><input type="text" id="na-q" placeholder="Nome ou e-mail..."></div>\n    <div class="fg"><div class="fl">Empresa</div><select id="na-co"><option value="">Todas</option></select></div>\n    <div class="fg"><div class="fl">CSM</div><select id="na-csm"><option value="">Todos</option></select></div>\n    <button class="btnf" id="na-rst">Limpar</button>\n    <div class="ctag" id="na-ctag"></div>\n  </div>\n  <div id="na-body" style="padding:20px 24px;"></div>\n</div>\n<div id="pg-nf" class="pg">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Buscar empresa</div><input type="text" id="nf-q" placeholder="Nome da empresa..."></div>\n    <div class="fg"><div class="fl">Consumiu aulas?</div>\n      <select id="nf-cons">\n        <option value="">Todos</option>\n        <option value="sim">Sim</option>\n        <option value="nao">N&atilde;o</option>\n      </select>\n    </div>\n    <button class="btnf" id="nf-rst">Limpar</button>\n    <div class="ctag" id="nf-ctag"></div>\n  </div>\n  <div id="nf-body" style="padding:20px 24px;"></div>\n</div>\n<div id="pg-or" class="pg">\n  <div class="fbar">\n    <div class="fg"><div class="fl">Buscar</div><input type="text" id="or-q" placeholder="Nome, e-mail ou empresa..."></div>\n    <div class="fg"><div class="fl">Status empresa</div>\n      <select id="or-st">\n        <option value="">Todos</option>\n        <option value="Churn">Churn</option>\n        <option value="Inativo">Inativo</option>\n        <option value="N&atilde;o cadastrada">N&atilde;o cadastrada</option>\n      </select>\n    </div>\n    <button class="btnf" id="or-rst">Limpar</button>\n    <div class="ctag" id="or-ctag"></div>\n  </div>\n  <div id="or-body" style="padding:20px 24px;"></div>\n</div>\n'
    JS_LOGIC = 'document.getElementById("upd-lbl").textContent="Atualizado em "+UPD;\nfunction esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}\nfunction pct(a,b){return b>0?Math.round(a/b*100):0;}\nfunction mSince(ds){if(!ds)return 999;var d=new Date(ds),n=new Date();return(n.getFullYear()-d.getFullYear())*12+(n.getMonth()-d.getMonth());}\nfunction fPill(f){\n  if(f==="offensive")return\'<span class="pill p-o">&#128293; Ofensiva</span>\';\n  if(f==="green")    return\'<span class="pill p-g">&#128994; Green</span>\';\n  if(f==="yellow")   return\'<span class="pill p-y">&#128993; Yellow</span>\';\n  if(f==="red")      return\'<span class="pill p-r">&#128308; Red</span>\';\n  return\'<span class="pill p-k">&#9899; Black</span>\';\n}\nfunction stPill(s){\n  if(s==="Churn")  return\'<span class="pill p-r">Churn</span>\';\n  if(s==="Inativo")return\'<span class="pill p-k">Inativo</span>\';\n  if(s==="Ativo")  return\'<span class="pill p-g">Ativo</span>\';\n  return\'<span class="pill p-p">N\\xE3o cadastrada</span>\';\n}\nfunction goTab(n,el){\n  document.querySelectorAll(".pg").forEach(function(p){p.classList.remove("on");});\n  document.querySelectorAll(".ntab").forEach(function(t){t.classList.remove("on");});\n  document.getElementById("pg-"+n).classList.add("on");el.classList.add("on");\n}\nfunction pop(id,vals){var s=document.getElementById(id);vals.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;s.appendChild(o);});}\nvar acos=[...new Set(U.map(function(u){return u.company;}))].sort();\nvar acsms=[...new Set(U.map(function(u){return u.csm;}).filter(Boolean))].sort();\npop("ov-co",acos);pop("ov-csm",acsms);pop("em-csm",acsms);\npop("us-co",acos);pop("us-csm",acsms);\npop("na-co",[...new Set(NV.map(function(u){return u.company;}))].sort());\npop("na-csm",[...new Set(NV.map(function(u){return u.csm;}).filter(Boolean))].sort());\nvar ovF=null;\nfunction runOv(){\n  var co=document.getElementById("ov-co").value,csm=document.getElementById("ov-csm").value;\n  var crChecked=[...document.querySelectorAll(".ov-cr:checked")].map(function(c){return c.value;});\n  var fd=U.filter(function(u){\n    if(co&&u.company!==co)return false;\n    if(csm&&u.csm!==csm)return false;\n    if(crChecked.length>0){\n      var noDate=!u.created_at;\n      var m=noDate?-1:mSince(u.created_at);\n      var lt3=!noDate&&m<3,is3to6=!noDate&&m>=3&&m<=6,gt6=!noDate&&m>6;\n      var ok=(crChecked.indexOf("lt3")>=0&&lt3)||(crChecked.indexOf("3to6")>=0&&is3to6)||\n             (crChecked.indexOf("gt6")>=0&&gt6)||(crChecked.indexOf("nodate")>=0&&noDate);\n      if(!ok)return false;\n    }\n    return true;\n  });\n  var tot=fd.length,aM=fd.filter(function(u){return u.active_this_month;}).length;\n  var off=fd.filter(function(u){return u.flag==="offensive";});\n  var yel=fd.filter(function(u){return u.flag==="yellow";});\n  var red=fd.filter(function(u){return u.flag==="red";});\n  var blk=fd.filter(function(u){return u.flag==="black";});\n  var kpis=[\n    {lbl:"Total Usu\\xE1rios",    val:tot,       sub:"empresas ativas",              cls:"c-b",grp:null},\n    {lbl:"Ativos este m\\xEAs",   val:aM,        sub:pct(aM,tot)+"% do total",       cls:"c-g",grp:"active"},\n    {lbl:"&#128293; Ofensiva",   val:off.length,sub:"ativos nos 2 \\xFAltimos meses",cls:"c-o",grp:"offensive"},\n    {lbl:"&#128993; Yellow",     val:yel.length,sub:"inativos 30-60 dias",          cls:"c-y",grp:"yellow"},\n    {lbl:"&#128308; Red",        val:red.length,sub:"inativos 60-90 dias",          cls:"c-r",grp:"red"},\n    {lbl:"&#9899; Black",        val:blk.length,sub:"inativos 90+ dias",            cls:"c-k",grp:"black"},\n  ];\n  var kh=\'<div class="krow k6">\';\n  kpis.forEach(function(k){\n    var isSel=(ovF===k.grp&&k.grp!==null)?" sel":"",isClk=k.grp?" clk":"";\n    kh+=\'<div class="kpi\'+isClk+isSel+\'"\'+(k.grp?\' onclick="togOv(\\\'\'+k.grp+\'\\\')"\':\'\')+\'>\'+\n      \'<div class="klbl">\'+k.lbl+\'</div><div class="kval \'+k.cls+\'">\'+k.val+\'</div><div class="ksub">\'+k.sub+\'</div></div>\';\n  });\n  kh+=\'</div>\';\n  var dh=\'\';\n  if(ovF){\n    var sub;\n    if(ovF==="active")sub=fd.filter(function(u){return u.active_this_month;});\n    else if(ovF==="offensive")sub=off;\n    else sub=fd.filter(function(u){return u.flag===ovF;});\n    var seen={};sub=sub.filter(function(u){if(seen[u.email])return false;seen[u.email]=1;return true;});\n    var lblMap={"active":"Ativos este m\\xeas","offensive":"Em Ofensiva (2 \\xFAltimos meses)","yellow":"Yellow Flag","red":"Red Flag","black":"Black Flag"};\n    var rows=sub.slice(0,300).map(function(u){\n      return \'<tr><td><div style="font-weight:600;">\'+esc(u.name)+\'</div><div style="font-size:11px;color:var(--g400);">\'+esc(u.email)+\'</div></td>\'+\n        \'<td>\'+esc(u.company)+\'</td><td>\'+esc(u.csm||"\\u2014")+\'</td><td>\'+fPill(u.flag)+\'</td>\'+\n        \'<td>\'+esc(u.last_consumed||"\\u2014")+\'</td><td>\'+u.total_consumed+\'</td></tr>\';\n    }).join(\'\');\n    dh=\'<div class="det"><div class="det-ttl"><span>\'+lblMap[ovF]+\' \\u2014 \'+sub.length+\' usu\\xE1rios</span>\'+\n      \'<span class="cls" onclick="ovF=null;runOv()">&#10005;</span></div>\'+\n      \'<div class="tscr"><table><thead><tr><th>Usu\\xE1rio</th><th>Empresa</th><th>CSM</th><th>Flag</th><th>\\xDAltimo consumo</th><th>Total aulas</th></tr></thead>\'+\n      \'<tbody>\'+rows+\'</tbody></table></div>\'+\n      (sub.length>300?\'<div style="padding:8px;font-size:11px;color:var(--g400);">Mostrando 300 de \'+sub.length+\'</div>\':\'\')+\n    \'</div>\';\n  }\n  document.getElementById("ov-body").innerHTML=\'<div style="padding:20px 24px;">\'+kh+dh+\'</div>\';\n}\nfunction togOv(g){ovF=(ovF===g)?null:g;runOv();}\ndocument.getElementById("ov-co").addEventListener("change",runOv);\ndocument.getElementById("ov-csm").addEventListener("change",runOv);\ndocument.querySelectorAll(".ov-cr").forEach(function(c){c.addEventListener("change",runOv);});\ndocument.getElementById("ov-grupo").addEventListener("change",runOv);\n\n// Populate grupo dropdown\nvar grupos=[...new Set(Object.keys(CHARTS.grupos))].sort();\nvar grSel=document.getElementById("ov-grupo");\ngrupos.forEach(function(g){var o=document.createElement("option");o.value=g;o.textContent=g;grSel.appendChild(o);});\n\n// Init charts\nvar chartMensal=null,chartGrupos=null;\nfunction initCharts(){\n  var meses=CHARTS.meses.map(function(m){return m.replace(/^\\d{4}-/,\'\');});\n  var COLOR_LINE=\'#3b82f6\';\n  var COLORS=[\'#3b82f6\',\'#059669\',\'#d97706\',\'#dc2626\',\'#7c3aed\',\'#ea580c\'];\n\n  // Chart mensal — total vs ativos\n  var ctx1=document.getElementById("chart-mensal").getContext("2d");\n  chartMensal=new Chart(ctx1,{\n    type:"line",\n    data:{\n      labels:meses,\n      datasets:[\n        {\n          label:"Total histórico",\n          data:CHARTS.evolucao_total,\n          borderColor:"#94a3b8",backgroundColor:"rgba(148,163,184,.06)",\n          borderWidth:2,pointRadius:2,tension:.35,fill:true,\n          borderDash:[4,3]\n        },\n        {\n          label:"Empresas ativas hoje",\n          data:CHARTS.evolucao_ativos,\n          borderColor:COLOR_LINE,backgroundColor:"rgba(59,130,246,.08)",\n          borderWidth:2.5,pointRadius:3,pointBackgroundColor:COLOR_LINE,tension:.35,fill:true\n        }\n      ]\n    },\n    options:{responsive:true,maintainAspectRatio:false,\n      plugins:{\n        legend:{display:true,position:"bottom",labels:{font:{size:10},boxWidth:12,padding:8}},\n        tooltip:{mode:"index",intersect:false}\n      },\n      scales:{x:{grid:{display:false},ticks:{font:{size:10}}},\n              y:{grid:{color:"rgba(0,0,0,.04)"},ticks:{font:{size:10}}}}}\n  });\n\n  // Chart grupos — ativos (sólido) vs total (tracejado)\n  var ctx2=document.getElementById("chart-grupos").getContext("2d");\n  var gruposKeys=Object.keys(CHARTS.grupos_ativos);\n  var dsGrupos=[];\n  gruposKeys.forEach(function(g,i){\n    var cor=COLORS[i%COLORS.length];\n    // Linha ativos (sólida)\n    dsGrupos.push({\n      label:g,data:CHARTS.grupos_ativos[g],\n      borderColor:cor,backgroundColor:"transparent",\n      borderWidth:2.5,pointRadius:2,tension:.35\n    });\n    // Linha total (tracejada, mais fina)\n    dsGrupos.push({\n      label:g+" (total)",data:CHARTS.grupos_total[g],\n      borderColor:cor,backgroundColor:"transparent",\n      borderWidth:1.5,pointRadius:0,tension:.35,\n      borderDash:[4,3],\n      legend:{display:false}\n    });\n  });\n  chartGrupos=new Chart(ctx2,{\n    type:"line",\n    data:{labels:meses,datasets:dsGrupos},\n    options:{responsive:true,maintainAspectRatio:false,\n      plugins:{\n        legend:{\n          position:"bottom",\n          labels:{\n            font:{size:10},boxWidth:12,\n            filter:function(item){return item.text.indexOf("(total)")<0;}\n          }\n        },\n        tooltip:{\n          mode:"index",intersect:false,\n          filter:function(item){return item.dataset.label.indexOf("(total)")<0;}\n        }\n      },\n      scales:{x:{grid:{display:false},ticks:{font:{size:10}}},\n              y:{grid:{color:"rgba(0,0,0,.04)"},ticks:{font:{size:10}}}}}\n  });\n\n  // Retention\n  var retHtml="<div class=\\"ret-grid\\">";\n  CHARTS.retencao.slice(-6).forEach(function(r){\n    var cor=r.taxa>=70?"var(--green)":r.taxa>=50?"var(--yel)":"var(--red)";\n    retHtml+="<div class=\\"ret-card\\"><div class=\\"ret-pct\\" style=\\"color:"+cor+"\\">"+r.taxa+"%</div>"+\n      "<div class=\\"ret-mes\\">"+r.mes.replace(/^\\d{4}-/,"")+"</div>"+\n      "<div class=\\"ret-sub\\">"+r.retidos+"/"+r.base+"</div></div>";\n  });\n  retHtml+="</div>";\n  document.getElementById("ret-body").innerHTML=retHtml;\n\n  // Ranking\n  var maxAulas=CHARTS.ranking[0][1];\n  var rankHtml="";\n  CHARTS.ranking.slice(0,12).forEach(function(r,i){\n    var w=Math.round(r[1]/maxAulas*100);\n    rankHtml+="<div class=\\"rank-row\\"><span class=\\"rank-num\\">"+(i+1)+"</span>"+\n      "<span class=\\"rank-name\\">"+r[0]+"</span>"+\n      "<div class=\\"rank-bar-wrap\\"><div class=\\"rank-bar-fill\\" style=\\"width:"+w+"%\\"></div></div>"+\n      "<span class=\\"rank-val\\">"+r[1]+"</span></div>";\n  });\n  document.getElementById("rank-body").innerHTML=rankHtml;\n\n  document.getElementById("ov-charts").style.display="block";\n}\n\nfunction updateChartMensal(grupo){\n  if(!chartMensal)return;\n  if(!grupo){\n    chartMensal.data.datasets[0].data=CHARTS.evolucao_total;\n    chartMensal.data.datasets[0].label="Total histórico";\n    chartMensal.data.datasets[1].data=CHARTS.evolucao_ativos;\n    chartMensal.data.datasets[1].label="Empresas ativas hoje";\n    document.getElementById("grupo-sel-lbl").textContent="";\n  }else{\n    var tot=CHARTS.grupos_total[grupo]||[];\n    var atv=CHARTS.grupos_ativos[grupo]||[];\n    chartMensal.data.datasets[0].data=tot;\n    chartMensal.data.datasets[0].label=grupo+" (total)";\n    chartMensal.data.datasets[1].data=atv;\n    chartMensal.data.datasets[1].label=grupo+" (ativas)";\n    document.getElementById("grupo-sel-lbl").textContent="— "+grupo;\n  }\n  chartMensal.update();\n}\n\n// Hook grupo filter into chart\ndocument.getElementById("ov-grupo").addEventListener("change",function(){\n  updateChartMensal(this.value);\n});\n\nsetTimeout(initCharts,100);\ndocument.getElementById("ov-rst").addEventListener("click",function(){\n  document.getElementById("ov-co").value="";\n  document.getElementById("ov-csm").value="";\n  document.getElementById("ov-grupo").value="";\n  document.querySelectorAll(".ov-cr").forEach(function(c){c.checked=false;});\n  updateChartMensal("");\n  ovF=null;runOv();\n});\nvar selCo=null;\nfunction runEm(){\n  var q=document.getElementById("em-q").value.toLowerCase(),csm=document.getElementById("em-csm").value;\n  var fd=C.filter(function(c){if(q&&c.empresa.toLowerCase().indexOf(q)<0)return false;if(csm&&c.csm!==csm)return false;return true;});\n  document.getElementById("em-ctag").textContent=fd.length+" empresas";\n  var cards=fd.map(function(co){\n    var p=pct(co.active_m,co.total);\n    var fc=p>=70?"var(--green)":p>=40?"var(--yel)":"var(--red)";\n    var pc2=p>=70?"p-g":p>=40?"p-y":"p-r";\n    var isSel=(selCo===co.empresa)?" sel":"";\n    var ee=esc(co.empresa).replace(/\\\\/g,"\\\\\\\\").replace(/\'/g,"\\\\\'");\n    return \'<div class="cocard\'+isSel+\'" onclick="pickCo(\\\'\'+ee+\'\\\')">\'+\n      \'<div class="co-top"><div><div class="co-name">\'+esc(co.empresa)+\'</div><div class="co-csm">\'+esc(co.csm||"Sem CSM")+\'</div></div>\'+\n      \'<span class="pill \'+pc2+\'">\'+p+\'%</span></div>\'+\n      \'<div class="co-bar"><div class="co-bf" style="width:\'+p+\'%;background:\'+fc+\'"></div></div>\'+\n      \'<div class="co-stats">\'+\n        \'<span class="cos"><span class="dot d-o"></span>\'+co.offensive+\'</span>\'+\n        \'<span class="cos"><span class="dot d-g"></span>\'+co.green+\'</span>\'+\n        \'<span class="cos"><span class="dot d-y"></span>\'+co.yellow+\'</span>\'+\n        \'<span class="cos"><span class="dot d-r"></span>\'+co.red+\'</span>\'+\n        \'<span class="cos"><span class="dot d-k"></span>\'+co.black+\'</span>\'+\n        \'<span style="font-size:10px;color:var(--g400);margin-left:auto;">\'+co.total+\' usu\\xE1rios</span>\'+\n      \'</div></div>\';\n  }).join(\'\');\n  var det=\'\';\n  if(selCo){\n    var cu=U.filter(function(u){return u.company===selCo;});\n    var rows=cu.map(function(u){\n      return \'<tr><td><div style="font-weight:600;">\'+esc(u.name)+\'</div><div style="font-size:11px;color:var(--g400);">\'+esc(u.email)+\'</div></td>\'+\n        \'<td>\'+fPill(u.flag)+\'</td><td>\'+(u.days_inactive>=9000?"\\u2014":u.days_inactive+"d")+\'</td>\'+\n        \'<td>\'+esc(u.last_consumed||"\\u2014")+\'</td><td>\'+u.total_consumed+\'</td><td>\'+esc(u.created_at||"\\u2014")+\'</td></tr>\';\n    }).join(\'\');\n    det=\'<div class="det"><div class="det-ttl"><span>\'+esc(selCo)+\' \\u2014 \'+cu.length+\' usu\\xE1rios</span>\'+\n      \'<span class="cls" onclick="selCo=null;runEm()">&#10005;</span></div>\'+\n      \'<div class="tscr"><table><thead><tr><th>Usu\\xE1rio</th><th>Flag</th><th>Inativo h\\xE1</th><th>\\xDAltimo consumo</th><th>Total aulas</th><th>Criado em</th></tr></thead>\'+\n      \'<tbody>\'+rows+\'</tbody></table></div></div>\';\n  }\n  document.getElementById("em-body").innerHTML=\'<div class="sec">\'+fd.length+\' Empresas</div><div class="cogrid">\'+cards+\'</div>\'+det;\n}\nfunction pickCo(e){selCo=(selCo===e)?null:e;runEm();}\ndocument.getElementById("em-q").addEventListener("input",runEm);\ndocument.getElementById("em-csm").addEventListener("change",runEm);\ndocument.getElementById("em-rst").addEventListener("click",function(){document.getElementById("em-q").value="";document.getElementById("em-csm").value="";selCo=null;runEm();});\nfunction runUs(){\n  var q=document.getElementById("us-q").value.toLowerCase();\n  var co=document.getElementById("us-co").value,csm=document.getElementById("us-csm").value;\n  var fl=document.getElementById("us-fl").value,cr=document.getElementById("us-cr").value;\n  var fd=U.filter(function(u){\n    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0)return false;\n    if(co&&u.company!==co)return false;if(csm&&u.csm!==csm)return false;\n    if(fl&&u.flag!==fl)return false;\n    if(cr){var m=mSince(u.created_at);if(cr==="lt3"&&m>=3)return false;if(cr==="3to6"&&(m<3||m>6))return false;if(cr==="gt6"&&m<=6)return false;}\n    return true;\n  });\n  document.getElementById("us-ctag").textContent=fd.length+" usu\\xE1rios";\n  var rows=fd.slice(0,500).map(function(u){\n    return \'<tr><td><div style="font-weight:600;">\'+esc(u.name)+\'</div><div style="font-size:11px;color:var(--g400);">\'+esc(u.email)+\'</div></td>\'+\n      \'<td>\'+esc(u.company)+\'</td><td>\'+esc(u.csm||"\\u2014")+\'</td><td>\'+fPill(u.flag)+\'</td>\'+\n      \'<td>\'+(u.days_inactive>=9000?"\\u2014":u.days_inactive+" dias")+\'</td>\'+\n      \'<td>\'+esc(u.last_consumed||"\\u2014")+\'</td><td>\'+u.total_consumed+\'</td><td>\'+esc(u.created_at||"\\u2014")+\'</td></tr>\';\n  }).join(\'\');\n  document.getElementById("us-body").innerHTML=\n    \'<div class="twrap"><div class="thdr"><div class="ttl">Lista de Usu\\xE1rios</div>\'+\n    \'<div class="tcnt">\'+(fd.length>500?"500 de "+fd.length+" \\u2014 filtre para ver mais":fd.length+" usu\\xE1rios")+\'</div></div>\'+\n    \'<div class="tscr"><table><thead><tr><th>Usu\\xE1rio</th><th>Empresa</th><th>CSM</th><th>Flag</th><th>Inativo h\\xE1</th><th>\\xDAltimo consumo</th><th>Total aulas</th><th>Criado em</th></tr></thead>\'+\n    \'<tbody>\'+rows+\'</tbody></table></div></div>\';\n}\ndocument.getElementById("us-q").addEventListener("input",runUs);\n["us-co","us-csm","us-fl","us-cr"].forEach(function(id){document.getElementById(id).addEventListener("change",runUs);});\ndocument.getElementById("us-rst").addEventListener("click",function(){document.getElementById("us-q").value="";["us-co","us-csm","us-fl","us-cr"].forEach(function(id){document.getElementById(id).value="";});runUs();});\nfunction runNa(){\n  var q=document.getElementById("na-q").value.toLowerCase();\n  var co=document.getElementById("na-co").value,csm=document.getElementById("na-csm").value;\n  var fd=NV.filter(function(u){\n    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0)return false;\n    if(co&&u.company!==co)return false;if(csm&&u.csm!==csm)return false;return true;\n  });\n  document.getElementById("na-ctag").textContent=fd.length+" usu\\xE1rios";\n  var kpis=\'<div class="krow k3" style="margin-bottom:16px;">\'+\n    \'<div class="kpi"><div class="klbl">Nunca assistiram</div><div class="kval c-y">\'+fd.length+\'</div><div class="ksub">usu\\xE1rios cadastrados</div></div>\'+\n    \'<div class="kpi"><div class="klbl">Empresas afetadas</div><div class="kval c-b">\'+[...new Set(fd.map(function(u){return u.company;}))].length+\'</div></div>\'+\n    \'<div class="kpi"><div class="klbl">CSMs envolvidos</div><div class="kval c-k">\'+[...new Set(fd.map(function(u){return u.csm;}).filter(Boolean))].length+\'</div></div>\'+\n  \'</div>\';\n  var rows=fd.slice(0,500).map(function(u){\n    return \'<tr><td><div style="font-weight:600;">\'+esc(u.name)+\'</div><div style="font-size:11px;color:var(--g400);">\'+esc(u.email)+\'</div></td>\'+\n      \'<td>\'+esc(u.company)+\'</td><td>\'+esc(u.csm||"\\u2014")+\'</td><td>\'+esc(u.created_at||"\\u2014")+\'</td></tr>\';\n  }).join(\'\');\n  document.getElementById("na-body").innerHTML=kpis+\n    \'<div class="twrap"><div class="thdr"><div class="ttl">Cadastrados que nunca assistiram</div><div class="tcnt">\'+fd.length+\' usu\\xE1rios</div></div>\'+\n    \'<div class="tscr"><table><thead><tr><th>Usu\\xE1rio</th><th>Empresa</th><th>CSM</th><th>Criado em</th></tr></thead>\'+\n    \'<tbody>\'+rows+\'</tbody></table></div></div>\';\n}\ndocument.getElementById("na-q").addEventListener("input",runNa);\n["na-co","na-csm"].forEach(function(id){document.getElementById(id).addEventListener("change",runNa);});\ndocument.getElementById("na-rst").addEventListener("click",function(){document.getElementById("na-q").value="";["na-co","na-csm"].forEach(function(id){document.getElementById(id).value="";});runNa();});\nfunction runNf(){\n  var q=document.getElementById("nf-q").value.toLowerCase();\n  var cons=document.getElementById("nf-cons").value;\n  var fd=NF.filter(function(c){\n    if(q&&c.empresa.toLowerCase().indexOf(q)<0)return false;\n    if(cons==="sim"&&!c.teve_consumo)return false;\n    if(cons==="nao"&&c.teve_consumo)return false;\n    return true;\n  });\n  document.getElementById("nf-ctag").textContent=fd.length+" empresas";\n  var kpis=\'<div class="krow k3" style="margin-bottom:16px;">\'+\n    \'<div class="kpi"><div class="klbl">Total empresas</div><div class="kval c-p">\'+fd.length+\'</div><div class="ksub">n\\xE3o encontradas como ativas</div></div>\'+\n    \'<div class="kpi"><div class="klbl">Com consumo de aulas</div><div class="kval c-o">\'+fd.filter(function(c){return c.teve_consumo;}).length+\'</div></div>\'+\n    \'<div class="kpi"><div class="klbl">Usu\\xE1rios nestas empresas</div><div class="kval c-b">\'+fd.reduce(function(a,c){return a+c.total;},0)+\'</div></div>\'+\n  \'</div>\';\n  var rows=fd.map(function(c){\n    return \'<tr><td style="font-weight:600;">\'+esc(c.empresa)+\'</td>\'+\n      \'<td style="font-weight:700;text-align:center;">\'+c.total+\'</td>\'+\n      \'<td>\'+(c.teve_consumo?\'<span class="pill p-g">&#10003; Sim</span>\':\'<span class="pill p-gr">N\\xE3o</span>\')+\'</td></tr>\';\n  }).join(\'\');\n  document.getElementById("nf-body").innerHTML=kpis+\n    \'<div class="ibox ibox-p">&#10067; Empresas com usu\\xE1rios cadastrados que n\\xE3o est\\xE3o na base de clientes como <strong>Ativas</strong>. Mapeie e cadastre as que forem clientes ativos.</div>\'+\n    \'<div class="twrap"><div class="thdr"><div class="ttl">Empresas n\\xE3o mapeadas</div><div class="tcnt">\'+fd.length+\' empresas</div></div>\'+\n    \'<div class="tscr"><table><thead><tr><th>Empresa</th><th>Usu\\xE1rios</th><th>Consumiu aulas?</th></tr></thead>\'+\n    \'<tbody>\'+rows+\'</tbody></table></div></div>\';\n}\ndocument.getElementById("nf-q").addEventListener("input",runNf);\ndocument.getElementById("nf-cons").addEventListener("change",runNf);\ndocument.getElementById("nf-rst").addEventListener("click",function(){document.getElementById("nf-q").value="";document.getElementById("nf-cons").value="";runNf();});\nfunction runOr(){\n  var q=document.getElementById("or-q").value.toLowerCase(),st=document.getElementById("or-st").value;\n  var sixAgo=new Date();sixAgo.setMonth(sixAgo.getMonth()-6);\n  var fd=OR.filter(function(u){\n    if(u.co_status==="Churn"){var recent=u.last_consumed&&new Date(u.last_consumed)>=sixAgo;if(!recent)return false;}\n    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0&&u.company.toLowerCase().indexOf(q)<0)return false;\n    if(st&&u.co_status!==st)return false;return true;\n  });\n  document.getElementById("or-ctag").textContent=fd.length+" usu\\xE1rios";\n  var kpis=\'<div class="krow k2" style="margin-bottom:16px;">\'+\n    \'<div class="kpi"><div class="klbl">Usu\\xE1rios fora do dashboard</div><div class="kval c-p">\'+fd.length+\'</div><div class="ksub">empresa n\\xE3o est\\xE1 ativa na base</div></div>\'+\n    \'<div class="kpi"><div class="klbl">Empresas distintas</div><div class="kval c-b">\'+[...new Set(fd.map(function(u){return u.company;}))].length+\'</div></div>\'+\n  \'</div>\';\n  var rows=fd.slice(0,500).map(function(u){\n    return \'<tr><td><div style="font-weight:600;">\'+esc(u.name)+\'</div><div style="font-size:11px;color:var(--g400);">\'+esc(u.email)+\'</div></td>\'+\n      \'<td>\'+esc(u.company)+\'</td><td>\'+stPill(u.co_status)+\'</td>\'+\n      \'<td>\'+(u.total_consumed>0?\'<span class="pill p-g">&#10003; Sim (\'+u.total_consumed+\')</span>\':\'<span class="pill p-gr">N\\xE3o</span>\')+\'</td></tr>\';\n  }).join(\'\');\n  document.getElementById("or-body").innerHTML=kpis+\n    \'<div class="ibox ibox-y">&#9888;&#65039; Usu\\xE1rios que consumiram aulas nos \\xFAltimos 3 meses mas cuja empresa n\\xE3o est\\xE1 ativa na base. Corrija o status ou adicione um alias no script.</div>\'+\n    \'<div class="twrap"><div class="thdr"><div class="ttl">Usu\\xE1rios fora do dashboard principal</div><div class="tcnt">\'+(fd.length>500?"500 de "+fd.length:fd.length+" usu\\xE1rios")+\'</div></div>\'+\n    \'<div class="tscr"><table><thead><tr><th>Usu\\xE1rio</th><th>Empresa</th><th>Status empresa</th><th>Consumiu aulas?</th></tr></thead>\'+\n    \'<tbody>\'+rows+\'</tbody></table></div></div>\';\n}\ndocument.getElementById("or-q").addEventListener("input",runOr);\ndocument.getElementById("or-st").addEventListener("change",runOr);\ndocument.getElementById("or-rst").addEventListener("click",function(){document.getElementById("or-q").value="";document.getElementById("or-st").value="";runOr();});\nrunOv();runEm();runUs();runNa();runNf();runOr();\n'

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
