#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PipeLovers - Gerador de Dashboard de Engajamento
=================================================
Como usar:
  1. Coloque os 4 CSVs na mesma pasta que este script:
       consumo.csv      -> relatório de consumo da plataforma
       clientes.csv     -> base de clientes (com coluna Status e CSM)
       usuarios.csv     -> base completa de usuários da plataforma
       nao_iniciou.csv  -> relatório de quem nunca assistiu nenhuma aula
  2. Rode: python3 gerar_dashboard.py
  3. O arquivo index.html será gerado/atualizado automaticamente
"""

import csv
import json
import os
import sys
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ─────────────────────────────────────────
#  CONFIGURAÇÃO — nomes dos arquivos
# ─────────────────────────────────────────
CONSUMO_CSV    = "consumo.csv"
CLIENTES_CSV   = "clientes.csv"
USUARIOS_CSV   = "usuarios.csv"
NAO_INICIOU_CSV = "nao_iniciou.csv"
OUTPUT_HTML    = "index.html"

# ─────────────────────────────────────────
#  ALIASES — variações de nome entre arquivos
#  Formato: 'nome_no_arquivo' -> 'nome_na_base_de_clientes'
# ─────────────────────────────────────────
ALIASES = {
    # Intelbras
    'Intelbras 2': 'Intelbras', 'INTELBRAS 2': 'Intelbras',
    # Baldussi
    'Baldussi': 'Baldussi Telecon',
    # Teruya
    'Teruya Ferramentas': 'Teruya', 'TERUYA FERRAMENTAS': 'Teruya',
    # Ayko
    'AYKO': 'Ayko Tech',
    # Sinch
    'SINCH': 'Sinch',
    # Centric
    'Centric': 'Centric Solutions',
    # TR EPIS
    'TR EPI': 'TR EPIS',
    # AMPCO
    'AMPCO METAL': 'AMPCO',
    # Clinica Experts
    'Clínica Experts': 'Clinica Experts',
    # TotalPass variações
    'TotalPass SMB': 'TotalPass', 'TOTALPASS SMB': 'TotalPass',
    'TotalPass SMB 1': 'TotalPass', 'TotalPass SMB 2': 'TotalPass',
    'TotalPass Enterprise': 'TotalPass',
    'TotalPass TP WEB': 'TotalPass', 'TP WEB': 'TotalPass',
    # Okser
    'Okser Software': 'Okser',
    # Conexão Sistemas
    'Conexão Sistemas': 'Conexão Sistemas de Próteses',
    'Conexão Sistemas de Protese': 'Conexão Sistemas de Próteses',
    # Mailbiz
    'MAILBIZ': 'Mailbiz', 'MAILBIZ TECNOLOGIA': 'Mailbiz',
    # Synoro (Triibo, Axyma)
    'Triibo': 'Synoro', 'TRIIBO': 'Synoro',
    'Triibo e Axyma': 'Synoro', 'Axyma': 'Synoro',
    # Valeti
    'Valeti': 'Valeti App',
    # WebMais
    'WebMais Sistemas': 'WebMais', 'WEBMAIS': 'WebMais', 'Webmais': 'WebMais',
    # Sidrasul
    'Sidrasul Sistemas Hidráulicos Ltda': 'Sidrasul',
    # Gradisa
    'Gradisa Soluções em Ferro': 'Gradisa',
    # HSM
    'HSM DO BRASIL S.A.': 'HSM',
    # Tech-Ind
    'TECH IND': 'Tech-Ind',
    # R&Damasco
    'RDamasco Soluções Industriaisi': 'R&Damasco',
    # Urânia
    'Urânia Projetores': 'Urânia Planetário',
    # Strada
    'Strada Mob LTDA': 'Strada Mobi',
    # E aí
    'E AI Educa': 'E aí',
    # Kalashi
    'Kalashi': 'Kalashi Marcas e Patentes',
    # Omni
    'Omni Acessoria': 'Omni Assessoria',
    # Magis5
    'MAGIS5': 'Magis5',
    # Cerâmica City
    'Ceramica City': 'Cerâmica City',
    # VinhoTinta
    'Vinho Tinta': 'VinhoTinta',
    # Facilit'air
    "Facilit'Air: Soluções por Drones": "Facilit'air",
    # GNM Engenharia
    'Gen': 'GNM Engenharia',
    # Hytec
    'Hytec Automação Industrial': 'Hytec',
    # Innovoc
    'Innovo': 'Innovoc',
    # Inntecnet
    'INNTECNET SOFTWARE': 'Inntecnet',
    # Inovamotion
    'INOVAMOTION': 'Inovamotion Industria e tecnologia Ltda',
    # LID Travel
    'LID TRAVEL': 'LID Travel Viagens e Turismo',
    # Lolis
    'Lolis Transportes Internacionais': 'Lolis Transportes',
    # Agrocomm
    'Merc': 'Agrocomm comercio',
    # Couto Tech
    'Couto Tech': 'Couto Tech Soluções Energéticas',
    # Nelson Wilians
    'UP': 'Nelson Wilians Group',
    # Oximed
    'Oximed Gases': 'Oximed',
    # SEAPS
    'Seaps Consultoria': 'SEAPS',
    # Squad
    'SQUAD': 'Squad Terceirização',
    # Volt
    'VoltBras': 'Volt', 'SolarVolt': 'Volt',
    # outros
    '2P': '2P Group',
    'ALS BRASIL': 'ALS',
    'Alpha': 'Alpha cm',
    'Alta Geotecnia Ambiental SA': 'Alta Geotecnia',
    'Bistex Alimentos': 'Bistex',
    'Cubos': 'Cubos Tecnologia',
    'DV2 TOTVS': 'DV2',
    'Engeform Energia': 'Engeform',
    'Enkel Informática': 'Enkel',
    'FORSA': 'Forsa Brasil',
    'GOO': 'Goo! Life',
    'GZV IT SOLUTIONS': 'GZV',
    'Golden Cloud Technology': 'Golden Cloud',
    'Goose Educação': 'Goose',
    'Great people esg': 'Great People',
    'Grupo Nobre Embalagem': 'Nobre Embalagem',
    'Hubee design': 'Hubee',
    'Icom': 'Icom Marketing',
    'JCR': 'JCR Tecnologia',
    'Localize Digital': 'Localize', 'Localize Digital LTDA': 'Localize',
    'Logithink Tecnologia': 'Logithink',
    'Oxy Camaras Hiperbáricas': 'Oxy Camara',
    'Popedi Brasil': 'Popedi',
    'RunRun': 'Runrun.it',
    'STOA': 'Grupo STOA',
    'Samba': 'Samba Tech',
    'TARGIT': 'Targit Brasil',
    'Wiki Consultoria': 'Wiki',
}

# ─────────────────────────────────────────
#  UTILITÁRIOS
# ─────────────────────────────────────────
TODAY = datetime.now(timezone.utc)
THIS_MONTH = TODAY.strftime('%Y-%m')
_y, _m = TODAY.year, TODAY.month
CURRENT_MONTH = f"{_y:04d}-{_m:02d}"
_m2 = _m - 1; _y2 = _y if _m2 > 0 else _y - 1; _m2 = _m2 if _m2 > 0 else 12
PREV_MONTH = f"{_y2:04d}-{_m2:02d}"
THREE_MONTHS_AGO = TODAY - timedelta(days=90)

STATUS_PRIORITY = {'Ativo': 0, 'Try and Buy': 1, 'Inativo': 2, 'Churn': 3, '': 4}

def encontrar_csv(nome_config, prefixos):
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, nome_config)
    if os.path.exists(caminho):
        return caminho
    for f in os.listdir(pasta):
        fl = f.lower()
        if fl.endswith('.csv') and any(fl.startswith(p.lower()) for p in prefixos):
            print(f"  Auto-detectado: {f}")
            return os.path.join(pasta, f)
    return None

def get_flag(days, monthly):
    if CURRENT_MONTH in monthly and PREV_MONTH in monthly:
        return 'offensive'
    if days < 30:  return 'green'
    if days < 60:  return 'yellow'
    if days < 90:  return 'red'
    return 'black'

# ─────────────────────────────────────────
#  PROCESSAMENTO
# ─────────────────────────────────────────
def processar():
    print("\nPipeLovers - Gerador de Dashboard de Engajamento")
    print("=" * 50)

    # Localizar arquivos
    p_consumo   = encontrar_csv(CONSUMO_CSV,    ['consumo', 'pipelovers_b2b', 'consumption'])
    p_clientes  = encontrar_csv(CLIENTES_CSV,   ['clientes', 'base_de_clientes', 'planilha'])
    p_usuarios  = encontrar_csv(USUARIOS_CSV,   ['usuarios', 'membros', 'users'])
    p_nao       = encontrar_csv(NAO_INICIOU_CSV,['nao_iniciou', 'report_nao', 'nunca'])

    for nome, caminho in [('consumo', p_consumo), ('clientes', p_clientes),
                          ('usuarios', p_usuarios), ('nao_iniciou', p_nao)]:
        if not caminho:
            print(f"\nERRO: Arquivo '{nome}' nao encontrado.")
            print(f"  Renomeie para '{nome}.csv' e coloque na mesma pasta.")
            sys.exit(1)

    print(f"\nArquivos:")
    print(f"  consumo:    {os.path.basename(p_consumo)}")
    print(f"  clientes:   {os.path.basename(p_clientes)}")
    print(f"  usuarios:   {os.path.basename(p_usuarios)}")
    print(f"  nao_iniciou:{os.path.basename(p_nao)}")

    # ── 1. Base de clientes ──
    print("\nCarregando base de clientes...")
    clientes_raw = {}
    with open(p_clientes, encoding='utf-8') as f:
        # Detectar coluna Status (pode ter espaço no início)
        reader = csv.DictReader(f)
        for row in reader:
            emp = row.get('Empresa', '').strip()
            if not emp: continue
            # Coluna Status pode ser 'Status' ou ' Status'
            st = (row.get('Status') or row.get(' Status') or '').strip()
            csm = row.get('CSM', '').strip()
            if emp not in clientes_raw or \
               STATUS_PRIORITY.get(st, 4) < STATUS_PRIORITY.get(clientes_raw[emp]['status'], 4):
                clientes_raw[emp] = {'status': st, 'csm': csm}

    lower_to_nome = {e.lower(): e for e in clientes_raw}
    ativas_raw   = {e for e, d in clientes_raw.items() if d['status'] == 'Ativo'}
    ativas_lower = {e.lower(): e for e in ativas_raw}
    print(f"  {len(clientes_raw)} empresas | {len(ativas_raw)} ativas")

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

    # ── 2. Consumo ──
    print("\nCarregando consumo...")
    user_map = {}
    with open(p_consumo, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            email   = row.get('user_email', '').strip().lower()
            company = row.get('company', '').strip()
            if not email: continue
            date_s  = row.get('first_consumed_at', '')
            creat_s = row.get('user_created_at', '')
            name    = row.get('user_full_name', '').strip()
            try:    dt = datetime.fromisoformat(date_s.replace('Z', '+00:00'))
            except: dt = None
            try:    cr = datetime.fromisoformat(creat_s.replace('Z', '+00:00'))
            except: cr = None
            if email not in user_map:
                user_map[email] = {'email': email, 'name': name, 'company': company,
                                   'last_consumed': None, 'total_consumed': 0,
                                   'created_at': cr, 'monthly': defaultdict(int)}
            u = user_map[email]
            if dt:
                if not u['last_consumed'] or dt > u['last_consumed']:
                    u['last_consumed'] = dt
                u['monthly'][dt.strftime('%Y-%m')] += 1
            u['total_consumed'] += 1
            if cr and (not u['created_at'] or cr < u['created_at']):
                u['created_at'] = cr
    print(f"  {len(user_map):,} usuários únicos com consumo")

    # ── 3. Base de usuários ──
    print("\nCarregando base de usuários...")
    all_users_base = {}
    with open(p_usuarios, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # Coluna de email pode variar
            email = (row.get('Url do E-mail do Membro') or
                     row.get('email') or row.get('Email') or '').strip().lower()
            if '@' not in email: continue
            # Coluna de nome
            name = (row.get('Nome Completo') or
                    row.get('nome_completo') or
                    f"{row.get('Nome','')} {row.get('Sobrenome','')}".strip())
            # Coluna de empresa
            company = (row.get('Nome da Empresa') or
                       row.get('company') or row.get('Empresa') or '').strip()
            if email not in all_users_base:
                all_users_base[email] = {'name': name.strip(), 'company': company}
    print(f"  {len(all_users_base):,} usuários na base")

    # ── 4. Cruzar ──
    print("\nCruzando dados...")
    users_list   = []
    orphan_users = []
    not_found_set = defaultdict(lambda: {'total': 0, 'teve_consumo': False, 'co_status': ''})

    for email, uinfo in all_users_base.items():
        company = uinfo['company']
        if not company: continue
        canon, info = resolve(company)
        co_status = info.get('status', '')
        csm       = info.get('csm', '')
        cons      = user_map.get(email, {})
        last_dt   = cons.get('last_consumed')
        days      = int((TODAY - last_dt).days) if last_dt else 9999
        monthly   = dict(cons.get('monthly', {}))
        flag      = get_flag(days, monthly)
        created_at = cons.get('created_at')

        entry = {
            'email':             email,
            'name':              uinfo['name'] or cons.get('name', ''),
            'company':           canon,
            'co_status':         co_status,
            'csm':               csm,
            'total_consumed':    cons.get('total_consumed', 0),
            'last_consumed':     last_dt.strftime('%Y-%m-%d') if last_dt else '',
            'days_inactive':     days,
            'flag':              flag,
            'active_this_month': THIS_MONTH in monthly,
            'created_at':        created_at.strftime('%Y-%m-%d') if created_at else '',
            'monthly':           monthly,
            'never_consumed':    cons.get('total_consumed', 0) == 0,
        }

        if is_ativa(company):
            users_list.append(entry)
        else:
            # Aba órfãos: só se consumiu nos últimos 3 meses
            if last_dt and last_dt >= THREE_MONTHS_AGO:
                orphan_users.append({**entry, 'company': company, 'co_status': co_status})
            not_found_set[canon]['total'] += 1
            not_found_set[canon]['co_status'] = co_status
            if cons.get('total_consumed', 0) > 0:
                not_found_set[canon]['teve_consumo'] = True

    # ── 5. Company summaries ──
    co_map = defaultdict(lambda: {
        'total': 0, 'active_m': 0,
        'offensive': 0, 'green': 0, 'yellow': 0, 'red': 0, 'black': 0, 'never': 0
    })
    for u in users_list:
        c = u['company']
        co_map[c]['total'] += 1
        if u['active_this_month']: co_map[c]['active_m'] += 1
        co_map[c][u['flag']] += 1
        if u['never_consumed']: co_map[c]['never'] += 1

    # Incluir empresas ativas sem usuários
    empresas_com_usuarios_lower = {e.lower() for e in co_map}
    company_list = []
    for emp in sorted(co_map.keys()):
        _, info = resolve(emp)
        company_list.append({'empresa': emp, 'csm': info.get('csm', ''),
                              'co_status': info.get('status', ''), **co_map[emp]})
    for emp in sorted(ativas_raw):
        if emp.lower() not in empresas_com_usuarios_lower:
            info = clientes_raw[emp]
            company_list.append({'empresa': emp, 'csm': info.get('csm', ''),
                                 'co_status': 'Ativo', 'total': 0, 'active_m': 0,
                                 'offensive': 0, 'green': 0, 'yellow': 0, 'red': 0,
                                 'black': 0, 'never': 0})
    company_list.sort(key=lambda x: x['empresa'])

    # ── 6. Nunca assistiram ──
    never_list = [u for u in users_list if u['never_consumed']]

    # ── 7. Nao iniciou ──
    nao_list = []
    with open(p_nao, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            company = row.get('company', '').strip()
            if not is_ativa(company): continue
            _, info = resolve(company)
            nao_list.append({
                'name':      row.get('user_full_name', '').strip(),
                'email':     row.get('email', '').strip(),
                'company':   company,
                'csm':       info.get('csm', ''),
                'co_status': info.get('status', ''),
            })

    # ── 8. Not found (só não cadastradas) ──
    not_found_list = [
        {'empresa': emp, 'co_status': d['co_status'],
         'total': d['total'], 'teve_consumo': d['teve_consumo']}
        for emp, d in sorted(not_found_set.items(), key=lambda x: -x[1]['total'])
        if d['co_status'] not in ('Churn', 'Inativo')
    ]

    total  = len(users_list)
    active = sum(1 for u in users_list if u['active_this_month'])
    print(f"  {total:,} usuários de empresas ativas")
    print(f"  {active:,} ativos este mês")
    print(f"  {len(company_list)} empresas no dashboard")
    print(f"  {len(orphan_users)} usuários s/ empresa (últimos 3 meses)")
    print(f"  {len(not_found_list)} empresas não cadastradas")

    return {
        'users':    users_list,
        'companies': company_list,
        'never':    never_list,
        'notfound': not_found_list,
        'orphans':  orphan_users,
    }

# ─────────────────────────────────────────
#  GERAÇÃO DO HTML
# ─────────────────────────────────────────
def gerar_html(dados):
    agora = datetime.now().strftime('%d/%m/%Y')
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, OUTPUT_HTML)

    print(f"\nGerando HTML...")

    U  = json.dumps(dados['users'],     ensure_ascii=False, separators=(',', ':'))
    C  = json.dumps(dados['companies'], ensure_ascii=False, separators=(',', ':'))
    NV = json.dumps(dados['never'],     ensure_ascii=False, separators=(',', ':'))
    NF = json.dumps(dados['notfound'],  ensure_ascii=False, separators=(',', ':'))
    OR = json.dumps(dados['orphans'],   ensure_ascii=False, separators=(',', ':'))

    css = '''<style>
:root{--navy:#0f2952;--mid:#2563b0;--sky:#3b82f6;--sky-l:#eff6ff;--sky-p:#f8faff;--g50:#f9fafb;--g100:#f1f5f9;--g200:#e2e8f0;--g400:#94a3b8;--g500:#64748b;--g600:#475569;--g700:#334155;--g800:#1e293b;--green:#059669;--gl:#ecfdf5;--gb:#6ee7b7;--yel:#d97706;--yl:#fffbeb;--yb:#fcd34d;--red:#dc2626;--rl:#fef2f2;--rb:#fca5a5;--blk:#334155;--bkl:#f8fafc;--bkb:#94a3b8;--ora:#ea580c;--ol:#fff7ed;--ob:#fdba74;--pur:#7c3aed;--pl:#f5f3ff;--pb:#c4b5fd;--r:12px;--sh:0 1px 3px rgba(15,41,82,.07),0 1px 2px rgba(15,41,82,.04);}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:"Plus Jakarta Sans",sans-serif;background:var(--g50);color:var(--g800);min-height:100vh;font-size:14px;}
.hdr{background:var(--navy);height:56px;padding:0 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:400;box-shadow:0 2px 10px rgba(15,41,82,.2);}
.brand{display:flex;align-items:center;gap:10px;}.bico{width:30px;height:30px;background:var(--sky);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;}.bname{font-size:16px;font-weight:700;color:#fff;}.btag{font-size:11px;color:rgba(255,255,255,.4);margin-top:1px;}.upd{font-size:11px;color:rgba(255,255,255,.35);}
.nav{background:#fff;border-bottom:1px solid var(--g200);padding:0 24px;display:flex;position:sticky;top:56px;z-index:300;box-shadow:var(--sh);overflow-x:auto;}
.ntab{padding:13px 16px;font-size:13px;font-weight:600;color:var(--g500);cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;white-space:nowrap;}.ntab:hover{color:var(--mid);}.ntab.on{color:var(--mid);border-bottom-color:var(--sky);}
.fbar{background:#fff;border-bottom:1px solid var(--g200);padding:10px 24px;display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;}
.fg{display:flex;flex-direction:column;gap:3px;}.fl{font-size:10px;font-weight:700;color:var(--g400);text-transform:uppercase;letter-spacing:.5px;}
select,input[type=text]{background:var(--g50);border:1.5px solid var(--g200);color:var(--g800);padding:6px 10px;border-radius:7px;font-size:12px;font-family:inherit;outline:none;min-width:140px;transition:border-color .15s;}
select:focus,input:focus{border-color:var(--sky);background:#fff;}
.btnf{background:#fff;border:1.5px solid var(--g200);color:var(--g600);padding:6px 12px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;transition:all .15s;align-self:flex-end;}.btnf:hover{border-color:var(--sky);color:var(--mid);}
.ctag{font-size:12px;font-weight:600;color:var(--mid);background:var(--sky-l);border:1px solid #bfdbfe;padding:4px 10px;border-radius:20px;align-self:flex-end;}
.pg{display:none;padding:20px 24px;}.pg.on{display:block;}
.krow{display:grid;gap:12px;margin-bottom:20px;}.k6{grid-template-columns:repeat(6,1fr);}.k3{grid-template-columns:repeat(3,1fr);max-width:520px;}.k2{grid-template-columns:repeat(2,1fr);max-width:360px;}
.kpi{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh);}.kpi.clk{cursor:pointer;transition:all .15s;}.kpi.clk:hover{border-color:var(--sky);box-shadow:0 4px 16px rgba(15,41,82,.1);}.kpi.sel{border-color:var(--sky);box-shadow:0 0 0 3px rgba(59,130,246,.12);}
.klbl{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--g400);margin-bottom:6px;}.kval{font-size:24px;font-weight:800;line-height:1;letter-spacing:-.5px;}.ksub{font-size:11px;color:var(--g400);margin-top:3px;}
.c-b{color:var(--mid);}.c-g{color:var(--green);}.c-y{color:var(--yel);}.c-r{color:var(--red);}.c-k{color:var(--blk);}.c-o{color:var(--ora);}.c-p{color:var(--pur);}
.sec{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;color:var(--g400);margin-bottom:10px;display:flex;align-items:center;gap:8px;}.sec::after{content:"";flex:1;height:1px;background:var(--g200);}
.twrap{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);overflow:hidden;box-shadow:var(--sh);margin-bottom:20px;}
.thdr{padding:12px 16px;border-bottom:1px solid var(--g100);display:flex;justify-content:space-between;align-items:center;}.ttl{font-size:13px;font-weight:700;color:var(--g700);}.tcnt{font-size:12px;color:var(--g400);}
.tscr{overflow-x:auto;max-height:520px;overflow-y:auto;}
table{width:100%;border-collapse:collapse;}th{padding:9px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--g400);background:var(--g50);border-bottom:1px solid var(--g200);white-space:nowrap;position:sticky;top:0;z-index:1;}
td{padding:10px 12px;font-size:12px;border-bottom:1px solid var(--g100);vertical-align:middle;}tr:last-child td{border-bottom:none;}tr:hover td{background:var(--sky-p);}
.pill{display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:700;white-space:nowrap;}
.p-o{background:var(--ol);color:var(--ora);border:1px solid var(--ob);}.p-g{background:var(--gl);color:var(--green);border:1px solid var(--gb);}.p-y{background:var(--yl);color:var(--yel);border:1px solid var(--yb);}.p-r{background:var(--rl);color:var(--red);border:1px solid var(--rb);}.p-k{background:var(--bkl);color:var(--blk);border:1px solid var(--bkb);}.p-p{background:var(--pl);color:var(--pur);border:1px solid var(--pb);}.p-gr{background:var(--g100);color:var(--g500);border:1px solid var(--g200);}
.cogrid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}
.cocard{background:#fff;border:1.5px solid var(--g200);border-radius:var(--r);padding:14px 16px;box-shadow:var(--sh);cursor:pointer;transition:all .15s;}.cocard:hover{border-color:var(--sky);box-shadow:0 4px 14px rgba(15,41,82,.1);}.cocard.sel{border-color:var(--sky);box-shadow:0 0 0 3px rgba(59,130,246,.12);}
.co-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;}.co-name{font-size:13px;font-weight:700;color:var(--navy);line-height:1.2;}.co-csm{font-size:10px;color:var(--g400);margin-top:2px;}
.co-bar{height:4px;background:var(--g100);border-radius:2px;overflow:hidden;margin:8px 0 6px;}.co-bf{height:100%;border-radius:2px;}
.co-stats{display:flex;gap:5px;flex-wrap:wrap;}.cos{display:flex;align-items:center;gap:3px;font-size:10px;font-weight:600;}
.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}.d-o{background:var(--ora);}.d-g{background:var(--green);}.d-y{background:var(--yel);}.d-r{background:var(--red);}.d-k{background:var(--blk);}
.det{background:#fff;border:1.5px solid var(--sky);border-radius:var(--r);padding:16px 20px;margin-bottom:20px;box-shadow:0 0 0 3px rgba(59,130,246,.08);}
.det-ttl{font-size:14px;font-weight:700;color:var(--navy);margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;}
.cls{cursor:pointer;color:var(--g400);font-size:18px;line-height:1;}.cls:hover{color:var(--g700);}
.ibox{border-radius:var(--r);padding:12px 16px;margin-bottom:16px;font-size:13px;font-weight:500;}
.ibox-p{background:var(--pl);border:1.5px solid var(--pb);color:var(--pur);}.ibox-y{background:var(--yl);border:1.5px solid var(--yb);color:var(--yel);}
.ck-group{display:flex;flex-direction:column;gap:4px;padding:4px 0;}
.ck-lbl{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--g600);cursor:pointer;white-space:nowrap;}
.ck-lbl input[type=checkbox]{width:14px;height:14px;accent-color:var(--sky);cursor:pointer;flex-shrink:0;}
.ck-lbl:hover{color:var(--mid);}
::-webkit-scrollbar{width:5px;height:5px;}::-webkit-scrollbar-track{background:transparent;}::-webkit-scrollbar-thumb{background:var(--g200);border-radius:3px;}
</style>'''

    js = r'''
document.getElementById("upd-lbl").textContent="Atualizado em "+UPD;
function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
function pct(a,b){return b>0?Math.round(a/b*100):0;}
function mSince(ds){if(!ds)return 999;var d=new Date(ds),n=new Date();return(n.getFullYear()-d.getFullYear())*12+(n.getMonth()-d.getMonth());}
function fPill(f){
  if(f==="offensive")return'<span class="pill p-o">&#128293; Ofensiva</span>';
  if(f==="green")    return'<span class="pill p-g">&#128994; Green</span>';
  if(f==="yellow")   return'<span class="pill p-y">&#128993; Yellow</span>';
  if(f==="red")      return'<span class="pill p-r">&#128308; Red</span>';
  return'<span class="pill p-k">&#9899; Black</span>';
}
function stPill(s){
  if(s==="Churn")  return'<span class="pill p-r">Churn</span>';
  if(s==="Inativo")return'<span class="pill p-k">Inativo</span>';
  if(s==="Ativo")  return'<span class="pill p-g">Ativo</span>';
  return'<span class="pill p-p">N\xE3o cadastrada</span>';
}
function goTab(n,el){
  document.querySelectorAll(".pg").forEach(function(p){p.classList.remove("on");});
  document.querySelectorAll(".ntab").forEach(function(t){t.classList.remove("on");});
  document.getElementById("pg-"+n).classList.add("on");el.classList.add("on");
}
function pop(id,vals){var s=document.getElementById(id);vals.forEach(function(v){var o=document.createElement("option");o.value=v;o.textContent=v;s.appendChild(o);});}
var acos=[...new Set(U.map(function(u){return u.company;}))].sort();
var acsms=[...new Set(U.map(function(u){return u.csm;}).filter(Boolean))].sort();
pop("ov-co",acos);pop("ov-csm",acsms);pop("em-csm",acsms);
pop("us-co",acos);pop("us-csm",acsms);
pop("na-co",[...new Set(NV.map(function(u){return u.company;}))].sort());
pop("na-csm",[...new Set(NV.map(function(u){return u.csm;}).filter(Boolean))].sort());
var ovF=null;
function runOv(){
  var co=document.getElementById("ov-co").value,csm=document.getElementById("ov-csm").value;
  var crChecked=[...document.querySelectorAll(".ov-cr:checked")].map(function(c){return c.value;});
  var fd=U.filter(function(u){
    if(co&&u.company!==co)return false;
    if(csm&&u.csm!==csm)return false;
    if(crChecked.length>0){
      var noDate=!u.created_at;
      var m=noDate?-1:mSince(u.created_at);
      var lt3=!noDate&&m<3,is3to6=!noDate&&m>=3&&m<=6,gt6=!noDate&&m>6;
      var ok=(crChecked.indexOf("lt3")>=0&&lt3)||(crChecked.indexOf("3to6")>=0&&is3to6)||
             (crChecked.indexOf("gt6")>=0&&gt6)||(crChecked.indexOf("nodate")>=0&&noDate);
      if(!ok)return false;
    }
    return true;
  });
  var tot=fd.length,aM=fd.filter(function(u){return u.active_this_month;}).length;
  var off=fd.filter(function(u){return u.flag==="offensive";});
  var yel=fd.filter(function(u){return u.flag==="yellow";});
  var red=fd.filter(function(u){return u.flag==="red";});
  var blk=fd.filter(function(u){return u.flag==="black";});
  var kpis=[
    {lbl:"Total Usu\xE1rios",    val:tot,       sub:"empresas ativas",              cls:"c-b",grp:null},
    {lbl:"Ativos este m\xEAs",   val:aM,        sub:pct(aM,tot)+"% do total",       cls:"c-g",grp:"active"},
    {lbl:"&#128293; Ofensiva",   val:off.length,sub:"ativos nos 2 \xFAltimos meses",cls:"c-o",grp:"offensive"},
    {lbl:"&#128993; Yellow",     val:yel.length,sub:"inativos 30-60 dias",          cls:"c-y",grp:"yellow"},
    {lbl:"&#128308; Red",        val:red.length,sub:"inativos 60-90 dias",          cls:"c-r",grp:"red"},
    {lbl:"&#9899; Black",        val:blk.length,sub:"inativos 90+ dias",            cls:"c-k",grp:"black"},
  ];
  var kh='<div class="krow k6">';
  kpis.forEach(function(k){
    var isSel=(ovF===k.grp&&k.grp!==null)?" sel":"",isClk=k.grp?" clk":"";
    kh+='<div class="kpi'+isClk+isSel+'"'+(k.grp?' onclick="togOv(\''+k.grp+'\')"':'')+'>'+
      '<div class="klbl">'+k.lbl+'</div><div class="kval '+k.cls+'">'+k.val+'</div><div class="ksub">'+k.sub+'</div></div>';
  });
  kh+='</div>';
  var dh='';
  if(ovF){
    var sub;
    if(ovF==="active")sub=fd.filter(function(u){return u.active_this_month;});
    else if(ovF==="offensive")sub=off;
    else sub=fd.filter(function(u){return u.flag===ovF;});
    var seen={};sub=sub.filter(function(u){if(seen[u.email])return false;seen[u.email]=1;return true;});
    var lblMap={"active":"Ativos este m\xeas","offensive":"Em Ofensiva (2 \xFAltimos meses)","yellow":"Yellow Flag","red":"Red Flag","black":"Black Flag"};
    var rows=sub.slice(0,300).map(function(u){
      return '<tr><td><div style="font-weight:600;">'+esc(u.name)+'</div><div style="font-size:11px;color:var(--g400);">'+esc(u.email)+'</div></td>'+
        '<td>'+esc(u.company)+'</td><td>'+esc(u.csm||"\u2014")+'</td><td>'+fPill(u.flag)+'</td>'+
        '<td>'+esc(u.last_consumed||"\u2014")+'</td><td>'+u.total_consumed+'</td></tr>';
    }).join('');
    dh='<div class="det"><div class="det-ttl"><span>'+lblMap[ovF]+' \u2014 '+sub.length+' usu\xE1rios</span>'+
      '<span class="cls" onclick="ovF=null;runOv()">&#10005;</span></div>'+
      '<div class="tscr"><table><thead><tr><th>Usu\xE1rio</th><th>Empresa</th><th>CSM</th><th>Flag</th><th>\xDAltimo consumo</th><th>Total aulas</th></tr></thead>'+
      '<tbody>'+rows+'</tbody></table></div>'+
      (sub.length>300?'<div style="padding:8px;font-size:11px;color:var(--g400);">Mostrando 300 de '+sub.length+'</div>':'')+
    '</div>';
  }
  document.getElementById("ov-body").innerHTML='<div style="padding:20px 24px;">'+kh+dh+'</div>';
}
function togOv(g){ovF=(ovF===g)?null:g;runOv();}
document.getElementById("ov-co").addEventListener("change",runOv);
document.getElementById("ov-csm").addEventListener("change",runOv);
document.querySelectorAll(".ov-cr").forEach(function(c){c.addEventListener("change",runOv);});
document.getElementById("ov-rst").addEventListener("click",function(){
  document.getElementById("ov-co").value="";
  document.getElementById("ov-csm").value="";
  document.querySelectorAll(".ov-cr").forEach(function(c){c.checked=false;});
  ovF=null;runOv();
});
var selCo=null;
function runEm(){
  var q=document.getElementById("em-q").value.toLowerCase(),csm=document.getElementById("em-csm").value;
  var fd=C.filter(function(c){if(q&&c.empresa.toLowerCase().indexOf(q)<0)return false;if(csm&&c.csm!==csm)return false;return true;});
  document.getElementById("em-ctag").textContent=fd.length+" empresas";
  var cards=fd.map(function(co){
    var p=pct(co.active_m,co.total);
    var fc=p>=70?"var(--green)":p>=40?"var(--yel)":"var(--red)";
    var pc2=p>=70?"p-g":p>=40?"p-y":"p-r";
    var isSel=(selCo===co.empresa)?" sel":"";
    var ee=esc(co.empresa).replace(/\\/g,"\\\\").replace(/'/g,"\\'");
    return '<div class="cocard'+isSel+'" onclick="pickCo(\''+ee+'\')">'+
      '<div class="co-top"><div><div class="co-name">'+esc(co.empresa)+'</div><div class="co-csm">'+esc(co.csm||"Sem CSM")+'</div></div>'+
      '<span class="pill '+pc2+'">'+p+'%</span></div>'+
      '<div class="co-bar"><div class="co-bf" style="width:'+p+'%;background:'+fc+'"></div></div>'+
      '<div class="co-stats">'+
        '<span class="cos"><span class="dot d-o"></span>'+co.offensive+'</span>'+
        '<span class="cos"><span class="dot d-g"></span>'+co.green+'</span>'+
        '<span class="cos"><span class="dot d-y"></span>'+co.yellow+'</span>'+
        '<span class="cos"><span class="dot d-r"></span>'+co.red+'</span>'+
        '<span class="cos"><span class="dot d-k"></span>'+co.black+'</span>'+
        '<span style="font-size:10px;color:var(--g400);margin-left:auto;">'+co.total+' usu\xE1rios</span>'+
      '</div></div>';
  }).join('');
  var det='';
  if(selCo){
    var cu=U.filter(function(u){return u.company===selCo;});
    var rows=cu.map(function(u){
      return '<tr><td><div style="font-weight:600;">'+esc(u.name)+'</div><div style="font-size:11px;color:var(--g400);">'+esc(u.email)+'</div></td>'+
        '<td>'+fPill(u.flag)+'</td><td>'+(u.days_inactive>=9000?"\u2014":u.days_inactive+"d")+'</td>'+
        '<td>'+esc(u.last_consumed||"\u2014")+'</td><td>'+u.total_consumed+'</td><td>'+esc(u.created_at||"\u2014")+'</td></tr>';
    }).join('');
    det='<div class="det"><div class="det-ttl"><span>'+esc(selCo)+' \u2014 '+cu.length+' usu\xE1rios</span>'+
      '<span class="cls" onclick="selCo=null;runEm()">&#10005;</span></div>'+
      '<div class="tscr"><table><thead><tr><th>Usu\xE1rio</th><th>Flag</th><th>Inativo h\xE1</th><th>\xDAltimo consumo</th><th>Total aulas</th><th>Criado em</th></tr></thead>'+
      '<tbody>'+rows+'</tbody></table></div></div>';
  }
  document.getElementById("em-body").innerHTML='<div class="sec">'+fd.length+' Empresas</div><div class="cogrid">'+cards+'</div>'+det;
}
function pickCo(e){selCo=(selCo===e)?null:e;runEm();}
document.getElementById("em-q").addEventListener("input",runEm);
document.getElementById("em-csm").addEventListener("change",runEm);
document.getElementById("em-rst").addEventListener("click",function(){document.getElementById("em-q").value="";document.getElementById("em-csm").value="";selCo=null;runEm();});
function runUs(){
  var q=document.getElementById("us-q").value.toLowerCase();
  var co=document.getElementById("us-co").value,csm=document.getElementById("us-csm").value;
  var fl=document.getElementById("us-fl").value,cr=document.getElementById("us-cr").value;
  var fd=U.filter(function(u){
    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0)return false;
    if(co&&u.company!==co)return false;if(csm&&u.csm!==csm)return false;
    if(fl&&u.flag!==fl)return false;
    if(cr){var m=mSince(u.created_at);if(cr==="lt3"&&m>=3)return false;if(cr==="3to6"&&(m<3||m>6))return false;if(cr==="gt6"&&m<=6)return false;}
    return true;
  });
  document.getElementById("us-ctag").textContent=fd.length+" usu\xE1rios";
  var rows=fd.slice(0,500).map(function(u){
    return '<tr><td><div style="font-weight:600;">'+esc(u.name)+'</div><div style="font-size:11px;color:var(--g400);">'+esc(u.email)+'</div></td>'+
      '<td>'+esc(u.company)+'</td><td>'+esc(u.csm||"\u2014")+'</td><td>'+fPill(u.flag)+'</td>'+
      '<td>'+(u.days_inactive>=9000?"\u2014":u.days_inactive+" dias")+'</td>'+
      '<td>'+esc(u.last_consumed||"\u2014")+'</td><td>'+u.total_consumed+'</td><td>'+esc(u.created_at||"\u2014")+'</td></tr>';
  }).join('');
  document.getElementById("us-body").innerHTML=
    '<div class="twrap"><div class="thdr"><div class="ttl">Lista de Usu\xE1rios</div>'+
    '<div class="tcnt">'+(fd.length>500?"500 de "+fd.length+" \u2014 filtre para ver mais":fd.length+" usu\xE1rios")+'</div></div>'+
    '<div class="tscr"><table><thead><tr><th>Usu\xE1rio</th><th>Empresa</th><th>CSM</th><th>Flag</th><th>Inativo h\xE1</th><th>\xDAltimo consumo</th><th>Total aulas</th><th>Criado em</th></tr></thead>'+
    '<tbody>'+rows+'</tbody></table></div></div>';
}
document.getElementById("us-q").addEventListener("input",runUs);
["us-co","us-csm","us-fl","us-cr"].forEach(function(id){document.getElementById(id).addEventListener("change",runUs);});
document.getElementById("us-rst").addEventListener("click",function(){document.getElementById("us-q").value="";["us-co","us-csm","us-fl","us-cr"].forEach(function(id){document.getElementById(id).value="";});runUs();});
function runNa(){
  var q=document.getElementById("na-q").value.toLowerCase();
  var co=document.getElementById("na-co").value,csm=document.getElementById("na-csm").value;
  var fd=NV.filter(function(u){
    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0)return false;
    if(co&&u.company!==co)return false;if(csm&&u.csm!==csm)return false;return true;
  });
  document.getElementById("na-ctag").textContent=fd.length+" usu\xE1rios";
  var kpis='<div class="krow k3" style="margin-bottom:16px;">'+
    '<div class="kpi"><div class="klbl">Nunca assistiram</div><div class="kval c-y">'+fd.length+'</div><div class="ksub">usu\xE1rios cadastrados</div></div>'+
    '<div class="kpi"><div class="klbl">Empresas afetadas</div><div class="kval c-b">'+[...new Set(fd.map(function(u){return u.company;}))].length+'</div></div>'+
    '<div class="kpi"><div class="klbl">CSMs envolvidos</div><div class="kval c-k">'+[...new Set(fd.map(function(u){return u.csm;}).filter(Boolean))].length+'</div></div>'+
  '</div>';
  var rows=fd.slice(0,500).map(function(u){
    return '<tr><td><div style="font-weight:600;">'+esc(u.name)+'</div><div style="font-size:11px;color:var(--g400);">'+esc(u.email)+'</div></td>'+
      '<td>'+esc(u.company)+'</td><td>'+esc(u.csm||"\u2014")+'</td><td>'+esc(u.created_at||"\u2014")+'</td></tr>';
  }).join('');
  document.getElementById("na-body").innerHTML=kpis+
    '<div class="twrap"><div class="thdr"><div class="ttl">Cadastrados que nunca assistiram</div><div class="tcnt">'+fd.length+' usu\xE1rios</div></div>'+
    '<div class="tscr"><table><thead><tr><th>Usu\xE1rio</th><th>Empresa</th><th>CSM</th><th>Criado em</th></tr></thead>'+
    '<tbody>'+rows+'</tbody></table></div></div>';
}
document.getElementById("na-q").addEventListener("input",runNa);
["na-co","na-csm"].forEach(function(id){document.getElementById(id).addEventListener("change",runNa);});
document.getElementById("na-rst").addEventListener("click",function(){document.getElementById("na-q").value="";["na-co","na-csm"].forEach(function(id){document.getElementById(id).value="";});runNa();});
function runNf(){
  var q=document.getElementById("nf-q").value.toLowerCase();
  var cons=document.getElementById("nf-cons").value;
  var fd=NF.filter(function(c){
    if(q&&c.empresa.toLowerCase().indexOf(q)<0)return false;
    if(cons==="sim"&&!c.teve_consumo)return false;
    if(cons==="nao"&&c.teve_consumo)return false;
    return true;
  });
  document.getElementById("nf-ctag").textContent=fd.length+" empresas";
  var kpis='<div class="krow k3" style="margin-bottom:16px;">'+
    '<div class="kpi"><div class="klbl">Total empresas</div><div class="kval c-p">'+fd.length+'</div><div class="ksub">n\xE3o encontradas como ativas</div></div>'+
    '<div class="kpi"><div class="klbl">Com consumo de aulas</div><div class="kval c-o">'+fd.filter(function(c){return c.teve_consumo;}).length+'</div></div>'+
    '<div class="kpi"><div class="klbl">Usu\xE1rios nestas empresas</div><div class="kval c-b">'+fd.reduce(function(a,c){return a+c.total;},0)+'</div></div>'+
  '</div>';
  var rows=fd.map(function(c){
    return '<tr><td style="font-weight:600;">'+esc(c.empresa)+'</td>'+
      '<td style="font-weight:700;text-align:center;">'+c.total+'</td>'+
      '<td>'+(c.teve_consumo?'<span class="pill p-g">&#10003; Sim</span>':'<span class="pill p-gr">N\xE3o</span>')+'</td></tr>';
  }).join('');
  document.getElementById("nf-body").innerHTML=kpis+
    '<div class="ibox ibox-p">&#10067; Empresas com usu\xE1rios cadastrados que n\xE3o est\xE3o na base de clientes como <strong>Ativas</strong>. Mapeie e cadastre as que forem clientes ativos.</div>'+
    '<div class="twrap"><div class="thdr"><div class="ttl">Empresas n\xE3o mapeadas</div><div class="tcnt">'+fd.length+' empresas</div></div>'+
    '<div class="tscr"><table><thead><tr><th>Empresa</th><th>Usu\xE1rios</th><th>Consumiu aulas?</th></tr></thead>'+
    '<tbody>'+rows+'</tbody></table></div></div>';
}
document.getElementById("nf-q").addEventListener("input",runNf);
document.getElementById("nf-cons").addEventListener("change",runNf);
document.getElementById("nf-rst").addEventListener("click",function(){document.getElementById("nf-q").value="";document.getElementById("nf-cons").value="";runNf();});
function runOr(){
  var q=document.getElementById("or-q").value.toLowerCase(),st=document.getElementById("or-st").value;
  var sixAgo=new Date();sixAgo.setMonth(sixAgo.getMonth()-6);
  var fd=OR.filter(function(u){
    if(u.co_status==="Churn"){var recent=u.last_consumed&&new Date(u.last_consumed)>=sixAgo;if(!recent)return false;}
    if(q&&u.name.toLowerCase().indexOf(q)<0&&u.email.toLowerCase().indexOf(q)<0&&u.company.toLowerCase().indexOf(q)<0)return false;
    if(st&&u.co_status!==st)return false;return true;
  });
  document.getElementById("or-ctag").textContent=fd.length+" usu\xE1rios";
  var kpis='<div class="krow k2" style="margin-bottom:16px;">'+
    '<div class="kpi"><div class="klbl">Usu\xE1rios fora do dashboard</div><div class="kval c-p">'+fd.length+'</div><div class="ksub">empresa n\xE3o est\xE1 ativa na base</div></div>'+
    '<div class="kpi"><div class="klbl">Empresas distintas</div><div class="kval c-b">'+[...new Set(fd.map(function(u){return u.company;}))].length+'</div></div>'+
  '</div>';
  var rows=fd.slice(0,500).map(function(u){
    return '<tr><td><div style="font-weight:600;">'+esc(u.name)+'</div><div style="font-size:11px;color:var(--g400);">'+esc(u.email)+'</div></td>'+
      '<td>'+esc(u.company)+'</td><td>'+stPill(u.co_status)+'</td>'+
      '<td>'+(u.total_consumed>0?'<span class="pill p-g">&#10003; Sim ('+u.total_consumed+')</span>':'<span class="pill p-gr">N\xE3o</span>')+'</td></tr>';
  }).join('');
  document.getElementById("or-body").innerHTML=kpis+
    '<div class="ibox ibox-y">&#9888;&#65039; Usu\xE1rios que consumiram aulas nos \xFAltimos 3 meses mas cuja empresa n\xE3o est\xE1 ativa na base. Corrija o status ou adicione um alias no script.</div>'+
    '<div class="twrap"><div class="thdr"><div class="ttl">Usu\xE1rios fora do dashboard principal</div><div class="tcnt">'+(fd.length>500?"500 de "+fd.length:fd.length+" usu\xE1rios")+'</div></div>'+
    '<div class="tscr"><table><thead><tr><th>Usu\xE1rio</th><th>Empresa</th><th>Status empresa</th><th>Consumiu aulas?</th></tr></thead>'+
    '<tbody>'+rows+'</tbody></table></div></div>';
}
document.getElementById("or-q").addEventListener("input",runOr);
document.getElementById("or-st").addEventListener("change",runOr);
document.getElementById("or-rst").addEventListener("click",function(){document.getElementById("or-q").value="";document.getElementById("or-st").value="";runOr();});
runOv();runEm();runUs();runNa();runNf();runOr();'''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PipeLovers - Engajamento</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
{css}
</head>
<body>
<div class="hdr">
  <div class="brand"><div class="bico">PL</div><div><div class="bname">PipeLovers</div><div class="btag">Dashboard de Engajamento</div></div></div>
  <span class="upd" id="upd-lbl"></span>
</div>
<div class="nav">
  <div class="ntab on" onclick="goTab('ov',this)">&#128202; Overview</div>
  <div class="ntab"    onclick="goTab('em',this)">&#127970; Empresas</div>
  <div class="ntab"    onclick="goTab('us',this)">&#128100; Usu&aacute;rios</div>
  <div class="ntab"    onclick="goTab('na',this)">&#9888;&#65039; Nunca Assistiram</div>
  <div class="ntab"    onclick="goTab('nf',this)">&#10067; Empresas s/ cadastro</div>
  <div class="ntab"    onclick="goTab('or',this)">&#128100; Usu&aacute;rios s/ empresa</div>
</div>
<div id="pg-ov" class="pg on">
  <div class="fbar">
    <div class="fg"><div class="fl">Empresa</div><select id="ov-co"><option value="">Todas</option></select></div>
    <div class="fg"><div class="fl">CSM</div><select id="ov-csm"><option value="">Todos</option></select></div>
    <div class="fg">
      <div class="fl">Cria&ccedil;&atilde;o do usu&aacute;rio</div>
      <div class="ck-group">
        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="lt3"> Menos de 3 meses</label>
        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="3to6"> 3 a 6 meses</label>
        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="gt6"> Mais de 6 meses</label>
        <label class="ck-lbl"><input type="checkbox" class="ov-cr" value="nodate"> Sem data</label>
      </div>
    </div>
    <button class="btnf" id="ov-rst">Limpar</button>
  </div>
  <div id="ov-body"></div>
</div>
<div id="pg-em" class="pg">
  <div class="fbar">
    <div class="fg"><div class="fl">Buscar</div><input type="text" id="em-q" placeholder="Nome da empresa..."></div>
    <div class="fg"><div class="fl">CSM</div><select id="em-csm"><option value="">Todos</option></select></div>
    <button class="btnf" id="em-rst">Limpar</button>
    <div class="ctag" id="em-ctag"></div>
  </div>
  <div id="em-body" style="padding:20px 24px;"></div>
</div>
<div id="pg-us" class="pg">
  <div class="fbar">
    <div class="fg"><div class="fl">Buscar</div><input type="text" id="us-q" placeholder="Nome ou e-mail..."></div>
    <div class="fg"><div class="fl">Empresa</div><select id="us-co"><option value="">Todas</option></select></div>
    <div class="fg"><div class="fl">CSM</div><select id="us-csm"><option value="">Todos</option></select></div>
    <div class="fg"><div class="fl">Flag</div>
      <select id="us-fl">
        <option value="">Todas</option>
        <option value="offensive">&#128293; Ofensiva</option>
        <option value="green">&#128994; Green</option>
        <option value="yellow">&#128993; Yellow</option>
        <option value="red">&#128308; Red</option>
        <option value="black">&#9899; Black</option>
      </select>
    </div>
    <div class="fg"><div class="fl">Cria&ccedil;&atilde;o</div>
      <select id="us-cr">
        <option value="">Qualquer</option>
        <option value="lt3">Menos de 3 meses</option>
        <option value="3to6">3 a 6 meses</option>
        <option value="gt6">Mais de 6 meses</option>
      </select>
    </div>
    <button class="btnf" id="us-rst">Limpar</button>
    <div class="ctag" id="us-ctag"></div>
  </div>
  <div id="us-body" style="padding:20px 24px;"></div>
</div>
<div id="pg-na" class="pg">
  <div class="fbar">
    <div class="fg"><div class="fl">Buscar</div><input type="text" id="na-q" placeholder="Nome ou e-mail..."></div>
    <div class="fg"><div class="fl">Empresa</div><select id="na-co"><option value="">Todas</option></select></div>
    <div class="fg"><div class="fl">CSM</div><select id="na-csm"><option value="">Todos</option></select></div>
    <button class="btnf" id="na-rst">Limpar</button>
    <div class="ctag" id="na-ctag"></div>
  </div>
  <div id="na-body" style="padding:20px 24px;"></div>
</div>
<div id="pg-nf" class="pg">
  <div class="fbar">
    <div class="fg"><div class="fl">Buscar empresa</div><input type="text" id="nf-q" placeholder="Nome da empresa..."></div>
    <div class="fg"><div class="fl">Consumiu aulas?</div>
      <select id="nf-cons">
        <option value="">Todos</option>
        <option value="sim">Sim</option>
        <option value="nao">N&atilde;o</option>
      </select>
    </div>
    <button class="btnf" id="nf-rst">Limpar</button>
    <div class="ctag" id="nf-ctag"></div>
  </div>
  <div id="nf-body" style="padding:20px 24px;"></div>
</div>
<div id="pg-or" class="pg">
  <div class="fbar">
    <div class="fg"><div class="fl">Buscar</div><input type="text" id="or-q" placeholder="Nome, e-mail ou empresa..."></div>
    <div class="fg"><div class="fl">Status empresa</div>
      <select id="or-st">
        <option value="">Todos</option>
        <option value="Churn">Churn</option>
        <option value="Inativo">Inativo</option>
        <option value="N&atilde;o cadastrada">N&atilde;o cadastrada</option>
      </select>
    </div>
    <button class="btnf" id="or-rst">Limpar</button>
    <div class="ctag" id="or-ctag"></div>
  </div>
  <div id="or-body" style="padding:20px 24px;"></div>
</div>
<script>
var U={U};
var C={C};
var NV={NV};
var NF={NF};
var OR={OR};
var UPD="{agora}";
{js}
</script>
</body>
</html>'''

    html = html.replace('var U={U};', f'var U={U};')
    html = html.replace('var C={C};', f'var C={C};')
    html = html.replace('var NV={NV};', f'var NV={NV};')
    html = html.replace('var NF={NF};', f'var NF={NF};')
    html = html.replace('var OR={OR};', f'var OR={OR};')
    html = html.replace('var UPD="{agora}";', f'var UPD="{agora}";')
    html = html.replace('{js}', js)

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  {OUTPUT_HTML} gerado ({len(html)//1024} KB)")
    return caminho


# ─────────────────────────────────────────
#  ENTRADA
# ─────────────────────────────────────────
if __name__ == '__main__':
    dados = processar()
    caminho = gerar_html(dados)
    print(f"\nPronto! Dashboard gerado: {os.path.basename(caminho)}")
    print("\nPróximos passos:")
    print("  1. Abra o index.html no navegador para conferir")
    print("  2. Suba os arquivos no GitHub para publicar")
