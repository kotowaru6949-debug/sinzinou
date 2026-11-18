import urllib.request
import re
import json
import os
import sys
import time
import argparse

# 2026年 ドラフト指名情報
DRAFT_PICKS_2026 = [
    {'order': 1,  'owner': 'ケツからぼたもち',         'player': '立石 正広',   'pos': '内野手', 'role': 'hitter'},
    {'order': 2,  'owner': 'おならぶーぶぶ',           'player': '中川 勇斗',   'pos': '捕手',   'role': 'hitter'},
    {'order': 3,  'owner': 'パパパパパパパパパパワー', 'player': '工藤 泰成',   'pos': '投手',   'role': 'pitcher'},
    {'order': 4,  'owner': '毛玉おやぢ',               'player': '下村 海翔',   'pos': '投手',   'role': 'pitcher'},
    {'order': 5,  'owner': 'あッチょんぶりけ',         'player': '岡城 快生',   'pos': '外野手', 'role': 'hitter'},
    {'order': 6,  'owner': 'ケツからぼたもち',         'player': '今朝丸 裕喜', 'pos': '投手',   'role': 'pitcher'},
    {'order': 7,  'owner': 'おならぶーぶぶ',           'player': '木下 里都',   'pos': '投手',   'role': 'pitcher'},
    {'order': 8,  'owner': 'パパパパパパパパパパワー', 'player': '山田 脩也',   'pos': '内野手', 'role': 'hitter'},
    {'order': 9,  'owner': '毛玉おやぢ',               'player': '百崎 蒼生',   'pos': '内野手', 'role': 'hitter'},
    {'order': 10, 'owner': 'あッチょんぶりけ',         'player': '嶋村 麟士朗', 'pos': '捕手',   'role': 'hitter'},
]

OWNERS_2026 = ['おならぶーぶぶ', 'パパパパパパパパパパワー', '毛玉おやぢ', 'ケツからぼたもち', 'あッチょんぶりけ']

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_name(name):
    s = name.replace(' ', '').replace('\u3000', '')
    s = s.replace('﨑', '崎').replace('髙', '高')
    return s


def to_int(val):
    try:
        return int(val)
    except Exception:
        return 0


def to_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0


def get_year_urls(year):
    prefix = '' if year == 2026 else f'{year % 100:02d}/'
    return {
        'h1': f'https://baseball-data.com/{prefix}stats/hitter2-all/tpa-1.html',
        'p1': f'https://baseball-data.com/{prefix}stats/pitcher2-all/ip3-1.html',
        'h7': f'https://baseball-data.com/{prefix}stats/hitter2-all/tpa-7.html',
        'p7': f'https://baseball-data.com/{prefix}stats/pitcher2-all/ip3-7.html',
    }


def fetch_parsed(url, retries=3, delay=0.6):
    last_err = None
    for attempt in range(retries):
        try:
            if attempt > 0:
                time.sleep(delay * (attempt + 1))
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='ignore')
            tr_th_m = re.search(r'<tr[^>]*>(.*?)</tr>', html, re.S)
            if not tr_th_m:
                raise ValueError(f'Header row not found in {url}')
            ths = [re.sub(r'<[^>]+>', '', th).strip() for th in re.findall(r'<th[^>]*>(.*?)</th>', tr_th_m.group(1), re.S)]
            rows = []
            for r in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S):
                tds = [re.sub(r'<[^>]+>', '', td).strip() for td in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
                if tds and len(tds) == len(ths):
                    rows.append(dict(zip(ths, tds)))
            time.sleep(delay)
            return ths, rows
        except Exception as e:
            last_err = e
    raise last_err


def compute_year_data(year, h1, p1, h7, p7):
    # 1軍リーグ全体平均の算出
    tot_h_pa = sum(to_int(r['打席数']) for r in h1)
    tot_ab   = sum(to_int(r['打数']) for r in h1)
    tot_h    = sum(to_int(r['安打']) for r in h1)
    tot_tb   = sum(to_int(r['塁打']) for r in h1)
    tot_bb   = sum(to_int(r['四球']) for r in h1)
    tot_hbp  = sum(to_int(r['死球']) for r in h1)
    tot_sf   = sum(to_int(r['犠飛']) for r in h1)

    denom_lg_obp = tot_ab + tot_bb + tot_hbp + tot_sf
    lg_obp = (tot_h + tot_bb + tot_hbp) / denom_lg_obp if denom_lg_obp > 0 else 0.300
    lg_slg = tot_tb / tot_ab if tot_ab > 0 else 0.370
    lg_ops = lg_obp + lg_slg

    tot_p_bf  = sum(to_int(r['打者']) for r in p1)
    tot_p_k   = sum(to_int(r['奪三振']) for r in p1)
    tot_p_bb  = sum(to_int(r['与四球']) for r in p1)
    lg_k_pct  = (tot_p_k / tot_p_bf * 100) if tot_p_bf > 0 else 20.0
    lg_bb_pct = (tot_p_bb / tot_p_bf * 100) if tot_p_bf > 0 else 8.0
    lg_kbb_pct = ((tot_p_k - tot_p_bb) / tot_p_bf * 100) if tot_p_bf > 0 else 12.0

    league_avg = {
        'hitter_count': len(h1),
        'total_pa': tot_h_pa,
        'lg_obp': round(lg_obp, 4),
        'lg_slg': round(lg_slg, 4),
        'lg_ops': round(lg_ops, 4),
        'pitcher_count': len(p1),
        'total_bf': tot_p_bf,
        'total_k': tot_p_k,
        'total_bb': tot_p_bb,
        'lg_k_pct': round(lg_k_pct, 2),
        'lg_bb_pct': round(lg_bb_pct, 2),
        'lg_kbb_pct': round(lg_kbb_pct, 2),
    }

    draft_map_hitter = {}
    draft_map_pitcher = {}
    if year == 2026:
        for d in DRAFT_PICKS_2026:
            nkey = normalize_name(d['player'])
            if d['role'] == 'hitter':
                draft_map_hitter[nkey] = d
            else:
                draft_map_pitcher[nkey] = d

    # 全新人王有資格野手
    rookie_hitters = []
    for r in h7:
        name_raw = r['選手名'].replace('\u3000', ' ')
        nkey = normalize_name(name_raw)
        team = r['チーム']
        pa = to_int(r['打席数'])
        ab = to_int(r['打数'])
        g  = to_int(r['試合'])
        h  = to_int(r['安打'])
        hr = to_int(r['本塁打'])
        rbi = to_int(r['打点'])
        tb = to_int(r['塁打'])
        bb = to_int(r['四球'])
        hbp = to_int(r['死球'])
        sf = to_int(r['犠飛'])
        so = to_int(r['三振'])
        sb = to_int(r['盗塁'])

        denom_obp = ab + bb + hbp + sf
        obp = (h + bb + hbp) / denom_obp if denom_obp > 0 else 0.0
        slg = tb / ab if ab > 0 else 0.0
        ops = obp + slg
        ops_plus = 100 * (obp / lg_obp + slg / lg_slg - 1) if pa > 0 else None
        tb_bb = tb + bb

        is_hanshin = (team == '阪神')
        draft_info = draft_map_hitter.get(nkey) if is_hanshin else None

        rookie_hitters.append({
            'year': year,
            'role': 'hitter',
            'site_rank': to_int(r['順位']),
            'name': name_raw,
            'nkey': nkey,
            'team': team,
            'is_hanshin': is_hanshin,
            'is_drafted': draft_info is not None,
            'owner': draft_info['owner'] if draft_info else None,
            'draft_order': draft_info['order'] if draft_info else None,
            'pos': draft_info['pos'] if draft_info else '野手',
            'games': g if r['試合'] != '-' else 0,
            'avg': r['打率'],
            'pa': pa,
            'ab': ab,
            'h': h,
            'hr': hr,
            'rbi': rbi,
            'tb': tb,
            'bb': bb,
            'hbp': hbp,
            'so': so,
            'sb': sb,
            'tb_bb': tb_bb,
            'obp': round(obp, 3) if pa > 0 else None,
            'slg': round(slg, 3) if pa > 0 else None,
            'ops': round(ops, 3) if pa > 0 else None,
            'ops_plus': round(ops_plus, 1) if ops_plus is not None else None,
            'points': pa,
        })

    h_active = [x for x in rookie_hitters if x['pa'] > 0]
    h_20 = [x for x in rookie_hitters if x['pa'] >= 20]
    h_hanshin = [x for x in rookie_hitters if x['is_hanshin']]
    h_hanshin_active = [x for x in h_hanshin if x['pa'] > 0]

    for x in rookie_hitters:
        x['pa_rank'] = 1 + sum(1 for o in rookie_hitters if o['pa'] > x['pa'])
        x['tbbb_rank'] = 1 + sum(1 for o in rookie_hitters if o['tb_bb'] > x['tb_bb'])
        x['ops_plus_rank_20'] = (1 + sum(1 for o in h_20 if o['ops_plus'] > x['ops_plus'])) if x['pa'] >= 20 else None
        x['ops_plus_rank_all'] = (1 + sum(1 for o in h_active if o['ops_plus'] > x['ops_plus'])) if x['pa'] > 0 else None
        if x['is_hanshin']:
            x['hanshin_pa_rank'] = 1 + sum(1 for o in h_hanshin if o['pa'] > x['pa'])
            x['hanshin_tbbb_rank'] = 1 + sum(1 for o in h_hanshin if o['tb_bb'] > x['tb_bb'])
            x['hanshin_ops_plus_rank'] = (1 + sum(1 for o in h_hanshin_active if o['ops_plus'] > x['ops_plus'])) if x['pa'] > 0 else None

    # 全新人王有資格投手
    rookie_pitchers = []
    for r in p7:
        name_raw = r['選手名'].replace('\u3000', ' ')
        nkey = normalize_name(name_raw)
        team = r['チーム']
        bf = to_int(r['打者'])
        g  = to_int(r['試合'])
        w  = to_int(r['勝利'])
        l  = to_int(r['敗北'])
        sv = to_int(r['セlブ']) if 'セlブ' in r else to_int(r.get('セーブ', '0'))
        hld = to_int(r['ホlルド']) if 'ホlルド' in r else to_int(r.get('ホールド', '0'))
        k  = to_int(r['奪三振'])
        bb = to_int(r['与四球'])
        hbp = to_int(r['与死球'])
        hits = to_int(r['被安打'])
        hr = to_int(r['被本塁打'])
        er = to_int(r['自責点'])
        k_bb = k - bb
        k_pct = (k / bf * 100) if bf > 0 else None
        bb_pct = (bb / bf * 100) if bf > 0 else None
        kbb_pct = (k_bb / bf * 100) if bf > 0 else None
        kbb_plus = (100 * kbb_pct / lg_kbb_pct) if (bf > 0 and lg_kbb_pct != 0) else None

        is_hanshin = (team == '阪神')
        draft_info = draft_map_pitcher.get(nkey) if is_hanshin else None

        rookie_pitchers.append({
            'year': year,
            'role': 'pitcher',
            'site_ip_rank': to_int(r['順位']),
            'name': name_raw,
            'nkey': nkey,
            'team': team,
            'is_hanshin': is_hanshin,
            'is_drafted': draft_info is not None,
            'owner': draft_info['owner'] if draft_info else None,
            'draft_order': draft_info['order'] if draft_info else None,
            'pos': '投手',
            'games': g if r['試合'] != '-' else 0,
            'era': r['防御率'],
            'ip': r['投球回'],
            'w': w, 'l': l, 'sv': sv, 'hld': hld,
            'bf': bf,
            'k': k,
            'bb': bb,
            'hbp': hbp,
            'hits': hits,
            'hr': hr,
            'er': er,
            'k_bb': k_bb,
            'k_pct': round(k_pct, 2) if k_pct is not None else None,
            'bb_pct': round(bb_pct, 2) if bb_pct is not None else None,
            'kbb_pct': round(kbb_pct, 2) if kbb_pct is not None else None,
            'kbb_plus': round(kbb_plus, 1) if kbb_plus is not None else None,
            'points': bf,
        })

    p_active = [x for x in rookie_pitchers if x['bf'] > 0]
    p_30 = [x for x in rookie_pitchers if x['bf'] >= 30]
    p_hanshin = [x for x in rookie_pitchers if x['is_hanshin']]
    p_hanshin_active = [x for x in p_hanshin if x['bf'] > 0]

    for x in rookie_pitchers:
        x['bf_rank'] = 1 + sum(1 for o in rookie_pitchers if o['bf'] > x['bf'])
        x['kbb_rank'] = (1 + sum(1 for o in p_active if o['k_bb'] > x['k_bb'])) if x['bf'] > 0 else None
        x['kbb_pct_rank_30'] = (1 + sum(1 for o in p_30 if o['kbb_pct'] > x['kbb_pct'])) if x['bf'] >= 30 else None
        x['kbb_pct_rank_all'] = (1 + sum(1 for o in p_active if o['kbb_pct'] > x['kbb_pct'])) if x['bf'] > 0 else None
        if x['is_hanshin']:
            x['hanshin_bf_rank'] = 1 + sum(1 for o in p_hanshin if o['bf'] > x['bf'])
            x['hanshin_kbb_rank'] = (1 + sum(1 for o in p_hanshin_active if o['k_bb'] > x['k_bb'])) if x['bf'] > 0 else None
            x['hanshin_kbb_plus_rank'] = (1 + sum(1 for o in p_hanshin_active if o['kbb_plus'] > x['kbb_plus'])) if x['bf'] > 0 else None

    return build_year_record(
        year, league_avg, rookie_hitters, rookie_pitchers,
        h_active, h_20, h_hanshin,
        p_active, p_30, p_hanshin
    )


def build_year_record(year, league_avg, rookie_hitters, rookie_pitchers,
                      h_active, h_20, h_hanshin, p_active, p_30, p_hanshin):
    counts = {
        'rookie_hitters_total': len(rookie_hitters),
        'rookie_hitters_active': len(h_active),
        'rookie_hitters_20pa': len(h_20),
        'rookie_pitchers_total': len(rookie_pitchers),
        'rookie_pitchers_active': len(p_active),
        'rookie_pitchers_30bf': len(p_30),
        'hanshin_hitters': len(h_hanshin),
        'hanshin_pitchers': len(p_hanshin),
    }

    hanshin_hitters_sorted = sorted(h_hanshin, key=lambda x: (x['pa'], x['tb_bb']), reverse=True)
    hanshin_pitchers_sorted = sorted(p_hanshin, key=lambda x: x['bf'], reverse=True)
    rookie_pitchers_by_bf = sorted(rookie_pitchers, key=lambda x: x['bf'], reverse=True)
    rookie_hitters_by_pa = sorted(rookie_hitters, key=lambda x: (x['pa'], x['tb_bb']), reverse=True)

    # Top 15 + 阪神出場者（比較表用）
    p_top15 = rookie_pitchers_by_bf[:15]
    p_top_ids = {x['nkey'] for x in p_top15}
    top15_pitchers = list(p_top15)
    for x in hanshin_pitchers_sorted:
        if (x.get('is_drafted') or x['bf'] > 0) and x['nkey'] not in p_top_ids:
            top15_pitchers.append(x)

    h_top15 = rookie_hitters_by_pa[:15]
    h_top_ids = {x['nkey'] for x in h_top15}
    top15_hitters = list(h_top15)
    for x in hanshin_hitters_sorted:
        if (x.get('is_drafted') or x['pa'] > 0) and x['nkey'] not in h_top_ids:
            top15_hitters.append(x)

    # 散布図用データ（軽量化）
    scatter_pitchers = []
    for p in rookie_pitchers_by_bf:
        if p['bf'] == 0:
            continue
        if not p['is_hanshin'] and p['bf'] < 30:
            continue
        scatter_pitchers.append({
            'x': p['bf'],
            'y': p['kbb_plus'],
            'name': p['name'],
            'team': p['team'],
            'is_hanshin': p['is_hanshin'],
            'is_drafted': p.get('is_drafted', False),
            'owner': p.get('owner') or ('阪神(未指名)' if p['is_hanshin'] else p['team']),
            'kbb_pct': p['kbb_pct'],
            'k_bb': p['k_bb'],
            'era': p['era'],
            'ip': p['ip'],
            'bf_rank': p['bf_rank'],
            'kbb_pct_rank_30': p['kbb_pct_rank_30'],
        })

    scatter_hitters = []
    for h in rookie_hitters_by_pa:
        if h['pa'] == 0:
            continue
        if not h['is_hanshin'] and h['pa'] < 20:
            continue
        scatter_hitters.append({
            'pa': h['pa'],
            'tb_bb': h['tb_bb'],
            'y': h['ops_plus'],
            'name': h['name'],
            'team': h['team'],
            'is_hanshin': h['is_hanshin'],
            'is_drafted': h.get('is_drafted', False),
            'owner': h.get('owner') or ('阪神(未指名)' if h['is_hanshin'] else h['team']),
            'ops': h['ops'],
            'avg': h['avg'],
            'tb': h['tb'],
            'bb': h['bb'],
            'pa_rank': h['pa_rank'],
            'ops_plus_rank_20': h['ops_plus_rank_20'],
        })

    record = {
        'year': year,
        'league_avg': league_avg,
        'counts': counts,
        'hanshin_hitters': hanshin_hitters_sorted,
        'hanshin_pitchers': hanshin_pitchers_sorted,
        'top15_pitchers': top15_pitchers,
        'top15_hitters': top15_hitters,
        'scatter_pitchers': scatter_pitchers,
        'scatter_hitters': scatter_hitters,
    }

    # 2026年専用：ドラフト集計
    if year == 2026:
        h_by_nkey = {x['nkey']: x for x in h_hanshin}
        p_by_nkey = {x['nkey']: x for x in p_hanshin}
        drafted_players = []
        for d in DRAFT_PICKS_2026:
            nkey = normalize_name(d['player'])
            pdata = h_by_nkey[nkey] if d['role'] == 'hitter' else p_by_nkey[nkey]
            drafted_players.append({'role': d['role'], **pdata})
        teams_summary = []
        for owner in OWNERS_2026:
            picks = sorted([p for p in drafted_players if p['owner'] == owner], key=lambda x: x['points'], reverse=True)
            teams_summary.append({
                'owner': owner,
                'total_points': sum(p['points'] for p in picks),
                'picks': picks,
            })
        teams_summary.sort(key=lambda x: x['total_points'], reverse=True)
        for idx, t in enumerate(teams_summary, 1):
            t['rank'] = idx
        record['teams_summary'] = teams_summary
        record['drafted_players'] = drafted_players

    return record


def convert_legacy_game_result(legacy):
    # 既存の game_result.json から 2026年 year_record を復元
    rh = legacy['rookie_hitters_all']
    rp = legacy['rookie_pitchers_by_bf']
    for x in rh:
        x['year'] = 2026
        x['role'] = 'hitter'
    for x in rp:
        x['year'] = 2026
        x['role'] = 'pitcher'
    h_active = [x for x in rh if x['pa'] > 0]
    h_20 = [x for x in rh if x['pa'] >= 20]
    h_hanshin = [x for x in rh if x['is_hanshin']]
    p_active = [x for x in rp if x['bf'] > 0]
    p_30 = [x for x in rp if x['bf'] >= 30]
    p_hanshin = [x for x in rp if x['is_hanshin']]
    return build_year_record(2026, legacy['league_avg'], rh, rp, h_active, h_20, h_hanshin, p_active, p_30, p_hanshin)


def fetch_year_data(year):
    urls = get_year_urls(year)
    _, h1 = fetch_parsed(urls['h1'])
    _, p1 = fetch_parsed(urls['p1'])
    _, h7 = fetch_parsed(urls['h7'])
    _, p7 = fetch_parsed(urls['p7'])
    return compute_year_data(year, h1, p1, h7, p7)


def load_existing_history():
    hist_path = os.path.join(BASE_DIR, 'history_data.json')
    if os.path.exists(hist_path):
        with open(hist_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'years' in data:
                return data
    years_dict = {}
    gr_path = os.path.join(BASE_DIR, 'game_result.json')
    if os.path.exists(gr_path):
        with open(gr_path, 'r', encoding='utf-8') as f:
            gr = json.load(f)
            if 'rookie_hitters_all' in gr:
                years_dict['2026'] = convert_legacy_game_result(gr)
            elif 'year' in gr:
                years_dict[str(gr['year'])] = gr
    return {'years': years_dict}


def save_outputs(history_obj):
    # 年を昇順でソートして保存
    sorted_years = {str(y): history_obj['years'][str(y)] for y in sorted([int(k) for k in history_obj['years'].keys()])}
    history_obj['years'] = sorted_years

    # 歴代（全年度）の阪神選手集計を付与
    all_hanshin_pitchers = []
    all_hanshin_hitters = []
    yearly_totals = []

    for y_str, ydata in sorted_years.items():
        yr = int(y_str)
        p_sum = sum(p['bf'] for p in ydata['hanshin_pitchers'])
        h_sum = sum(h['pa'] for h in ydata['hanshin_hitters'])
        p_top = ydata['hanshin_pitchers'][0] if ydata['hanshin_pitchers'] else None
        h_top = ydata['hanshin_hitters'][0] if ydata['hanshin_hitters'] else None
        yearly_totals.append({
            'year': yr,
            'pitcher_points': p_sum,
            'hitter_points': h_sum,
            'total_points': p_sum + h_sum,
            'top_pitcher': f"{p_top['name']}({p_top['bf']})" if p_top and p_top['bf'] > 0 else '-',
            'top_hitter': f"{h_top['name']}({h_top['pa']})" if h_top and h_top['pa'] > 0 else '-',
        })
        for p in ydata['hanshin_pitchers']:
            if p['bf'] > 0:
                all_hanshin_pitchers.append({
                    'year': yr,
                    'name': p['name'],
                    'is_drafted': p.get('is_drafted', False),
                    'owner': p.get('owner'),
                    'bf': p['bf'],
                    'ip': p['ip'],
                    'era': p['era'],
                    'k_bb': p['k_bb'],
                    'kbb_pct': p['kbb_pct'],
                    'kbb_plus': p['kbb_plus'],
                    'bf_rank': p['bf_rank'],
                    'kbb_pct_rank_30': p['kbb_pct_rank_30'],
                })
        for h in ydata['hanshin_hitters']:
            if h['pa'] > 0:
                all_hanshin_hitters.append({
                    'year': yr,
                    'name': h['name'],
                    'is_drafted': h.get('is_drafted', False),
                    'owner': h.get('owner'),
                    'pa': h['pa'],
                    'tb_bb': h['tb_bb'],
                    'tb': h['tb'],
                    'bb': h['bb'],
                    'avg': h['avg'],
                    'ops': h['ops'],
                    'ops_plus': h['ops_plus'],
                    'pa_rank': h['pa_rank'],
                    'ops_plus_rank_20': h['ops_plus_rank_20'],
                })

    history_obj['all_time'] = {
        'yearly_totals': yearly_totals,
        'pitchers': all_hanshin_pitchers,
        'hitters': all_hanshin_hitters,
    }

    hist_path = os.path.join(BASE_DIR, 'history_data.json')
    with open(hist_path, 'w', encoding='utf-8') as f:
        json.dump(history_obj, f, ensure_ascii=False, separators=(',', ':'))
    print(f'Saved {hist_path} ({len(sorted_years)} years)')

    html_path = os.path.join(BASE_DIR, 'index.html')
    generate_html(history_obj, html_path)
    print(f'Saved {html_path}')


def generate_html(history_obj, html_path):
    data_json_str = json.dumps(history_obj, ensure_ascii=False, separators=(',', ':'))

    template = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#0b0d11">
  <title>阪神 新人王有資格者ドラフト｜2009〜2026年「量×質」ダッシュボード</title>

  <!-- OGP for LINE / SNS Preview -->
  <meta property="og:title" content="阪神 新人王有資格者ドラフト｜2009〜2026年「量×質」分析">
  <meta property="og:description" content="1打席/1対戦打者=1ptのドラフト結果＆K-BB+・OPS+で2009年〜2026年の歴代阪神ルーキーを比較！スマホで仮想ドラフトも遊べます。">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://kotowaru6949-debug.github.io/sinzinou/">
  <meta name="twitter:card" content="summary">

  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700;900&family=Teko:wght@600;700&display=swap" rel="stylesheet">

  <style>
    body {
      font-family: 'Noto Sans JP', sans-serif;
      background-color: #0b0d11;
      color: #f3f4f6;
      -webkit-tap-highlight-color: transparent;
    }
    .font-num {
      font-family: 'Teko', sans-serif;
      letter-spacing: 0.04em;
    }
    .tigers-yellow { color: #ffe200; }
    .gold-gradient { background: linear-gradient(135deg, #ffd700 0%, #b8860b 100%); }
    .silver-gradient { background: linear-gradient(135deg, #e0e0e0 0%, #8a9ba8 100%); }
    .bronze-gradient { background: linear-gradient(135deg, #cd7f32 0%, #8b4513 100%); }
    .no-scrollbar::-webkit-scrollbar { display: none; }
    .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
    .sticky-col {
      position: sticky;
      left: 0;
      z-index: 10;
    }
  </style>
</head>
<body class="min-h-screen pb-24 md:pb-12">

  <!-- Top Sticky Year Navigation -->
  <nav class="sticky top-0 z-40 bg-[#0b0d11]/90 backdrop-blur-md border-b border-gray-800/90 shadow-lg">
    <div class="max-w-7xl mx-auto px-3 md:px-6 py-2.5 flex items-center gap-2">
      <div id="yearPills" class="flex-1 flex items-center gap-1.5 overflow-x-auto no-scrollbar py-0.5">
        <!-- Populated by JS -->
      </div>
      <div class="shrink-0 flex items-center gap-1.5">
        <select id="yearSelect" class="bg-gray-900 text-xs md:text-sm font-bold text-yellow-300 border border-gray-700 rounded-lg px-2 py-1.5 focus:outline-none focus:border-yellow-400">
        </select>
        <button onclick="shareToLine()" class="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#06C755] hover:bg-[#05b34c] text-white text-xs font-bold transition shadow">
          <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.346 0 .627.285.627.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
          LINE共有
        </button>
        <button onclick="copyShareUrl()" class="hidden md:inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs font-bold border border-gray-700 transition">
          URLコピー
        </button>
      </div>
    </div>
  </nav>

  <main class="max-w-7xl mx-auto px-3 md:px-6 pt-5 space-y-8">
    <!-- Dynamic Header -->
    <header class="text-center pb-5 border-b border-gray-800">
      <div class="inline-block px-3 py-0.5 mb-2 text-[11px] font-bold tracking-wider uppercase bg-yellow-400 text-black rounded-full">
        Hanshin Tigers Rookie Analytics (2009–2026)
      </div>
      <h1 id="pageTitle" class="text-2xl md:text-4xl font-black tracking-tight text-white mb-2">
        2026年 阪神新人王有資格者ドラフト
      </h1>
      <p id="pageSubtitle" class="text-xs md:text-sm text-gray-400 max-w-3xl mx-auto leading-relaxed">
      </p>
    </header>

    <!-- YEAR VIEW -->
    <div id="yearView" class="space-y-8">

      <!-- 2026 Draft Section (Only visible when year == 2026) -->
      <section id="draft2026Section" class="space-y-5 hidden">
        <div class="flex items-center justify-between">
          <h2 class="text-lg md:text-xl font-bold text-yellow-400">1. 2026ドラフト 最終順位 ＆ チーム別サマリー</h2>
          <span class="text-[11px] text-gray-400">1打席 / 1対戦打者 = 1pt</span>
        </div>
        <div id="teamCardsGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 md:gap-4"></div>
        <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 md:p-5 shadow-lg">
          <h3 class="text-sm md:text-base font-bold text-white mb-3">指名者別 獲得ポイント内訳（独自ルール）</h3>
          <div class="relative h-56 md:h-64">
            <canvas id="userChart"></canvas>
          </div>
        </div>

        <!-- Drafted 10 Players Quality x Quantity -->
        <div class="space-y-4">
          <h3 class="text-base md:text-lg font-bold text-yellow-400">指名10選手の「量 × 質」詳細 ＆ 新人内ランキング</h3>
          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-3 bg-blue-950/30 border-b border-gray-800 flex flex-wrap justify-between gap-2">
              <span class="text-sm font-bold text-blue-300">⚾ 投手編（指名4名）</span>
              <span class="text-[11px] text-gray-400">横スクロールできます →</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs md:text-sm text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950 text-[11px] text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2.5 px-3 text-center">順</th>
                    <th class="py-2.5 px-3 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2.5 px-3">指名者</th>
                    <th class="py-2.5 px-3 text-right">打者(pt)</th>
                    <th class="py-2.5 px-3 text-right">K-BB</th>
                    <th class="py-2.5 px-3 text-right">K-BB%</th>
                    <th class="py-2.5 px-3 text-right">K-BB+</th>
                    <th class="py-2.5 px-3 text-center">12球団 量 / 質(30BF以上)</th>
                    <th class="py-2.5 px-3 text-center">阪神内</th>
                  </tr>
                </thead>
                <tbody id="draftPitcherTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>

          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-3 bg-orange-950/30 border-b border-gray-800 flex flex-wrap justify-between gap-2">
              <span class="text-sm font-bold text-orange-300">🏏 野手編（指名6名）</span>
              <span class="text-[11px] text-gray-400">横スクロールできます →</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs md:text-sm text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950 text-[11px] text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2.5 px-3 text-center">順</th>
                    <th class="py-2.5 px-3 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2.5 px-3">指名者</th>
                    <th class="py-2.5 px-3 text-right">打席(pt)</th>
                    <th class="py-2.5 px-3 text-right">塁打+四球</th>
                    <th class="py-2.5 px-3 text-right">OPS</th>
                    <th class="py-2.5 px-3 text-right">OPS+</th>
                    <th class="py-2.5 px-3 text-center">12球団 量 / 質(20PA以上)</th>
                    <th class="py-2.5 px-3 text-center">阪神内</th>
                  </tr>
                </thead>
                <tbody id="draftHitterTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- Top 5 Hanshin Rookie Points in Selected Year -->
      <section class="space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 id="top5Title" class="text-lg md:text-xl font-bold text-yellow-400">阪神新人 ポイント番付 Top 5</h2>
          <span class="text-[11px] text-gray-400">投手・野手合算（1打席 / 1対戦打者 = 1pt）</span>
        </div>
        <div id="top5Grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3"></div>
      </section>

      <!-- Virtual Draft Simulator -->
      <section class="bg-gradient-to-br from-gray-900 via-gray-900 to-yellow-950/20 border border-yellow-500/30 rounded-2xl p-4 md:p-5 shadow-lg space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="text-base md:text-lg font-black text-yellow-400 flex items-center gap-1.5">
              🎮 もしこの年に2人指名するなら？（仮想ドラフト）
            </h2>
            <p class="text-[11px] md:text-xs text-gray-400">下の阪神ルーキーから2名をタップして、自分だけのペア合計ポイントを計算できます</p>
          </div>
          <button onclick="resetSim()" class="px-2.5 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 border border-gray-700">リセット</button>
        </div>

        <div id="simResultBox" class="bg-gray-950/80 border border-gray-800 rounded-xl p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div class="text-xs text-gray-400">選手を2人選択してください</div>
        </div>

        <div id="simChips" class="flex flex-wrap gap-2"></div>
      </section>

      <!-- 4-Quadrant Scatter Charts -->
      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg md:text-xl font-bold text-yellow-400">質 × 量 4象限ポジショニングマップ</h2>
          <div class="flex items-center gap-3 text-[11px] text-gray-400">
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-yellow-400 inline-block"></span>阪神(指名)</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block"></span>阪神(その他)</span>
            <span class="inline-flex items-center gap-1"><span class="w-2.5 h-2.5 rounded-full bg-gray-400 inline-block"></span>他球団</span>
          </div>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 shadow-lg">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm md:text-base font-bold text-blue-300">投手：対戦打者数（量）× K-BB+（質）</h3>
              <span id="pScatterMeta" class="text-[11px] text-gray-400"></span>
            </div>
            <div class="relative h-72 md:h-80">
              <canvas id="pitcherScatter"></canvas>
            </div>
          </div>

          <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 shadow-lg">
            <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
              <h3 class="text-sm md:text-base font-bold text-orange-300">野手：<span id="hitterXLabel">打席数</span>（量）× OPS+（質）</h3>
              <div class="inline-flex rounded-lg bg-gray-950 p-0.5 border border-gray-800 text-[11px]">
                <button id="btnHitterPA" onclick="switchHitterX('pa')" class="px-2 py-1 rounded bg-yellow-400 text-black font-bold">打席数</button>
                <button id="btnHitterTBBB" onclick="switchHitterX('tb_bb')" class="px-2 py-1 rounded text-gray-400 hover:text-white">塁打＋四球</button>
              </div>
            </div>
            <div class="relative h-72 md:h-80">
              <canvas id="hitterScatter"></canvas>
            </div>
          </div>
        </div>
      </section>

      <!-- Hanshin Full Roster Table for the Year -->
      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 id="hanshinListTitle" class="text-lg md:text-xl font-bold text-yellow-400">阪神 新人王有資格者 全員一覧</h2>
          <span class="text-[11px] text-gray-400">横スクロールできます →</span>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-2.5 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
              <h3 class="text-xs md:text-sm font-bold text-blue-300">阪神 投手有資格者 <span id="hpCount" class="text-gray-400 font-normal"></span></h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2 px-2.5 text-center">虎</th>
                    <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2 px-2.5 text-right">打者(pt)</th>
                    <th class="py-2 px-2.5 text-right">回</th>
                    <th class="py-2 px-2.5 text-right">防</th>
                    <th class="py-2 px-2.5 text-right">K-BB</th>
                    <th class="py-2 px-2.5 text-right">K-BB%</th>
                    <th class="py-2 px-2.5 text-right">K-BB+</th>
                    <th class="py-2 px-2.5 text-center">12球団 量/質</th>
                  </tr>
                </thead>
                <tbody id="hanshinPitcherTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>

          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-2.5 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
              <h3 class="text-xs md:text-sm font-bold text-orange-300">阪神 野手有資格者 <span id="hhCount" class="text-gray-400 font-normal"></span></h3>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2 px-2.5 text-center">虎</th>
                    <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2 px-2.5 text-right">打席(pt)</th>
                    <th class="py-2 px-2.5 text-right">塁+四</th>
                    <th class="py-2 px-2.5 text-right">打率</th>
                    <th class="py-2 px-2.5 text-right">OPS</th>
                    <th class="py-2 px-2.5 text-right">OPS+</th>
                    <th class="py-2 px-2.5 text-center">12球団 量/質</th>
                  </tr>
                </thead>
                <tbody id="hanshinHitterTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      <!-- 12-Team Top 15 Comparison -->
      <section class="space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-lg md:text-xl font-bold text-yellow-400">12球団 全新人王有資格者 Top15 ＆ 阪神勢比較</h2>
          <span class="text-[11px] text-gray-400">黄色＝阪神指名 / 水色＝阪神選手</span>
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-2.5 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
              <h3 class="text-xs md:text-sm font-bold text-blue-300">12球団 投手（対戦打者Top15＋阪神出場選手）</h3>
              <span id="npbPCount" class="text-[11px] text-gray-400"></span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2 px-2.5 text-center">順</th>
                    <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2 px-2.5">球団</th>
                    <th class="py-2 px-2.5 text-right">打者</th>
                    <th class="py-2 px-2.5 text-right">回</th>
                    <th class="py-2 px-2.5 text-right">防</th>
                    <th class="py-2 px-2.5 text-right">K-BB</th>
                    <th class="py-2 px-2.5 text-right">K-BB%</th>
                    <th class="py-2 px-2.5 text-right">K-BB+</th>
                    <th class="py-2 px-2.5 text-center">質順</th>
                  </tr>
                </thead>
                <tbody id="npbPitcherTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>

          <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
            <div class="px-4 py-2.5 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
              <h3 class="text-xs md:text-sm font-bold text-orange-300">12球団 野手（打席数Top15＋阪神出場選手）</h3>
              <span id="npbHCount" class="text-[11px] text-gray-400"></span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
                <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                  <tr>
                    <th class="py-2 px-2.5 text-center">順</th>
                    <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                    <th class="py-2 px-2.5">球団</th>
                    <th class="py-2 px-2.5 text-right">打席</th>
                    <th class="py-2 px-2.5 text-right">塁+四</th>
                    <th class="py-2 px-2.5 text-right">打率</th>
                    <th class="py-2 px-2.5 text-right">OPS</th>
                    <th class="py-2 px-2.5 text-right">OPS+</th>
                    <th class="py-2 px-2.5 text-center">質順</th>
                  </tr>
                </thead>
                <tbody id="npbHitterTbody" class="divide-y divide-gray-800/60"></tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- ALL-TIME COMPARISON VIEW (2009-2026) -->
    <div id="allTimeView" class="space-y-8 hidden">
      <!-- Yearly Trend Chart -->
      <section class="bg-gray-900 border border-gray-800 rounded-2xl p-4 md:p-5 shadow-lg space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="text-base md:text-xl font-bold text-yellow-400">2009〜2026年 年度別・阪神ルーキー総獲得ポイント推移</h2>
            <p class="text-[11px] md:text-xs text-gray-400">各年の棒をタップするとその年度のページへジャンプします</p>
          </div>
        </div>
        <div class="relative h-64 md:h-80">
          <canvas id="yearlyTrendChart"></canvas>
        </div>
      </section>

      <!-- All-Time Top 30 Rankings -->
      <section class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <!-- Pitchers Top 30 -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="p-4 bg-blue-950/30 border-b border-gray-800 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 class="text-sm md:text-base font-bold text-blue-300">🏆 阪神ルーキー 歴代投手 Top 30</h3>
              <p class="text-[11px] text-gray-400">2009〜2026年 新人王有資格者（質ソート時は60打者以上対象）</p>
            </div>
            <div class="inline-flex rounded-lg bg-gray-950 p-0.5 border border-gray-800 text-[11px]">
              <button onclick="setAllTimePSort('bf')" id="sortP_bf" class="px-2 py-1 rounded bg-yellow-400 text-black font-bold">量(打者)</button>
              <button onclick="setAllTimePSort('kbb_plus')" id="sortP_kbb_plus" class="px-2 py-1 rounded text-gray-400">質(K-BB+)</button>
              <button onclick="setAllTimePSort('k_bb')" id="sortP_k_bb" class="px-2 py-1 rounded text-gray-400">K-BB実数</button>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-2.5 text-center">順</th>
                  <th class="py-2 px-2.5 text-center">年</th>
                  <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                  <th class="py-2 px-2.5 text-right">打者(pt)</th>
                  <th class="py-2 px-2.5 text-right">防御率</th>
                  <th class="py-2 px-2.5 text-right">K-BB</th>
                  <th class="py-2 px-2.5 text-right">K-BB%</th>
                  <th class="py-2 px-2.5 text-right">K-BB+</th>
                </tr>
              </thead>
              <tbody id="allTimePTbody" class="divide-y divide-gray-800/60"></tbody>
            </table>
          </div>
        </div>

        <!-- Hitters Top 30 -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="p-4 bg-orange-950/30 border-b border-gray-800 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 class="text-sm md:text-base font-bold text-orange-300">🏆 阪神ルーキー 歴代野手 Top 30</h3>
              <p class="text-[11px] text-gray-400">2009〜2026年 新人王有資格者（質ソート時は40打席以上対象）</p>
            </div>
            <div class="inline-flex rounded-lg bg-gray-950 p-0.5 border border-gray-800 text-[11px]">
              <button onclick="setAllTimeHSort('pa')" id="sortH_pa" class="px-2 py-1 rounded bg-yellow-400 text-black font-bold">量(打席)</button>
              <button onclick="setAllTimeHSort('ops_plus')" id="sortH_ops_plus" class="px-2 py-1 rounded text-gray-400">質(OPS+)</button>
              <button onclick="setAllTimeHSort('tb_bb')" id="sortH_tb_bb" class="px-2 py-1 rounded text-gray-400">塁打+四球</button>
            </div>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-2.5 text-center">順</th>
                  <th class="py-2 px-2.5 text-center">年</th>
                  <th class="py-2 px-2.5 sticky-col bg-gray-950">選手名</th>
                  <th class="py-2 px-2.5 text-right">打席(pt)</th>
                  <th class="py-2 px-2.5 text-right">塁打+四球</th>
                  <th class="py-2 px-2.5 text-right">打率</th>
                  <th class="py-2 px-2.5 text-right">OPS</th>
                  <th class="py-2 px-2.5 text-right">OPS+</th>
                </tr>
              </thead>
              <tbody id="allTimeHTbody" class="divide-y divide-gray-800/60"></tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <footer class="text-center text-xs text-gray-600 py-4 border-t border-gray-800">
      出典：<a href="https://baseball-data.com/" target="_blank" class="underline hover:text-gray-400">プロ野球データFreak</a> 1軍公式戦成績より集計
    </footer>
  </main>

  <!-- Mobile Bottom Floating Share Bar -->
  <div class="md:hidden fixed bottom-0 inset-x-0 z-50 bg-[#0b0d11]/95 backdrop-blur-md border-t border-gray-800 px-3 py-2.5 flex items-center gap-2 shadow-2xl">
    <button onclick="shareToLine()" class="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#06C755] active:bg-[#05b34c] text-white font-black text-sm shadow-lg">
      <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63h2.386c.346 0 .627.285.627.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.63-.63.346 0 .628.285.628.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.282.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"/></svg>
      LINEで友達に送る
    </button>
    <button onclick="copyShareUrl()" class="px-4 py-2.5 rounded-xl bg-gray-800 active:bg-gray-700 text-gray-200 font-bold text-sm border border-gray-700">
      URLコピー
    </button>
  </div>

  <!-- Toast -->
  <div id="toast" class="fixed top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full bg-yellow-400 text-black font-bold text-xs shadow-xl opacity-0 pointer-events-none transition-opacity duration-300">
    URLをコピーしました！
  </div>

  <script>
    const HISTORY_DATA = __DATA_JSON__;
    const AVAILABLE_YEARS = Object.keys(HISTORY_DATA.years).map(Number).sort((a, b) => b - a);
    let currentView = AVAILABLE_YEARS.includes(2026) ? '2026' : String(AVAILABLE_YEARS[0] || 'all');
    let hitterXMode = 'pa';
    let simSelected = [];
    let allTimePSort = 'bf';
    let allTimeHSort = 'pa';

    // Chart instances
    let userChartInst = null;
    let pitcherScatterInst = null;
    let hitterScatterInst = null;
    let yearlyTrendInst = null;

    const avgLinePlugin = {
      id: 'avgLine',
      beforeDatasetsDraw(chart) {
        const { ctx, chartArea: { left, right, top, bottom }, scales: { y } } = chart;
        if (!y) return;
        const yPos = y.getPixelForValue(100);
        if (yPos < top || yPos > bottom) return;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([5, 4]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.75)';
        ctx.moveTo(left, yPos);
        ctx.lineTo(right, yPos);
        ctx.stroke();
        ctx.fillStyle = 'rgba(52, 211, 153, 0.9)';
        ctx.font = '10px "Noto Sans JP", sans-serif';
        ctx.fillText('1軍平均 (100)', left + 6, yPos - 5);
        ctx.restore();
      }
    };

    function init() {
      const params = new URLSearchParams(window.location.search);
      const qYear = params.get('year');
      if (qYear === 'all' || (qYear && HISTORY_DATA.years[qYear])) {
        currentView = qYear;
      }
      buildYearNav();
      selectView(currentView, false);
    }

    function buildYearNav() {
      const pillsEl = document.getElementById('yearPills');
      const selectEl = document.getElementById('yearSelect');
      pillsEl.innerHTML = '';
      selectEl.innerHTML = '';

      const items = [];
      if (HISTORY_DATA.years['2026']) items.push({ key: '2026', label: '🔥2026 ドラフト' });
      items.push({ key: 'all', label: '🏆歴代比較 (09-26)' });
      AVAILABLE_YEARS.filter(y => y !== 2026).forEach(y => items.push({ key: String(y), label: `${y}年` }));

      items.forEach(it => {
        const btn = document.createElement('button');
        btn.dataset.key = it.key;
        btn.textContent = it.label;
        btn.onclick = () => selectView(it.key, true);
        btn.className = 'year-pill shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition border';
        pillsEl.appendChild(btn);

        const opt = document.createElement('option');
        opt.value = it.key;
        opt.textContent = it.label;
        selectEl.appendChild(opt);
      });

      selectEl.onchange = (e) => selectView(e.target.value, true);
    }

    function updateNavActive() {
      document.querySelectorAll('.year-pill').forEach(btn => {
        if (btn.dataset.key === currentView) {
          btn.className = 'year-pill shrink-0 px-3 py-1.5 rounded-full text-xs font-black transition border bg-yellow-400 text-black border-yellow-400 shadow';
        } else {
          btn.className = 'year-pill shrink-0 px-3 py-1.5 rounded-full text-xs font-bold transition border bg-gray-900 text-gray-300 border-gray-700 hover:border-gray-500';
        }
      });
      document.getElementById('yearSelect').value = currentView;
    }

    function selectView(key, updateUrl) {
      currentView = key;
      simSelected = [];
      updateNavActive();

      if (updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set('year', key);
        window.history.replaceState({}, '', url.toString());
      }

      if (key === 'all') {
        document.getElementById('yearView').classList.add('hidden');
        document.getElementById('allTimeView').classList.remove('hidden');
        renderAllTimeView();
      } else {
        document.getElementById('allTimeView').classList.add('hidden');
        document.getElementById('yearView').classList.remove('hidden');
        renderYearView(key);
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function renderYearView(yKey) {
      const yd = HISTORY_DATA.years[yKey];
      if (!yd) return;
      const la = yd.league_avg;
      const cnt = yd.counts;

      const is2026 = (yKey === '2026' && yd.teams_summary);
      document.getElementById('pageTitle').innerHTML = is2026
        ? '2026年 新人王有資格者ドラフト <span class="tigers-yellow">量 × 質</span>'
        : `${yKey}年 阪神 新人王有資格者 <span class="tigers-yellow">量 × 質 分析</span>`;
      document.getElementById('pageSubtitle').innerHTML =
        `【${yKey}年 1軍平均(=100)】投手 K-BB% <span class="text-blue-300 font-bold">${la.lg_kbb_pct}%</span> (K% ${la.lg_k_pct}% / BB% ${la.lg_bb_pct}%) ｜ 野手 OPS <span class="text-orange-300 font-bold">${la.lg_ops.toFixed(3)}</span> (出塁 ${la.lg_obp.toFixed(3)} / 長打 ${la.lg_slg.toFixed(3)})`;

      // 2026 Draft Section
      const draftSec = document.getElementById('draft2026Section');
      if (is2026) {
        draftSec.classList.remove('hidden');
        render2026Draft(yd);
      } else {
        draftSec.classList.add('hidden');
      }

      // Top 5 Banner
      document.getElementById('top5Title').textContent = `${yKey}年 阪神新人 ポイント番付 Top 5`;
      renderTop5(yd);

      // Virtual Draft Simulator
      renderSimulator(yd);

      // Scatter Plots
      renderScatters(yd);

      // Hanshin Roster Tables
      document.getElementById('hanshinListTitle').textContent = `${yKey}年 阪神 新人王有資格者 全${cnt.hanshin_pitchers + cnt.hanshin_hitters}名`;
      document.getElementById('hpCount').textContent = `(${cnt.hanshin_pitchers}名)`;
      document.getElementById('hhCount').textContent = `(${cnt.hanshin_hitters}名)`;
      renderHanshinTables(yd);

      // 12-team Comparison
      document.getElementById('npbPCount').textContent = `全${cnt.rookie_pitchers_total}名中`;
      document.getElementById('npbHCount').textContent = `全${cnt.rookie_hitters_total}名中`;
      render12TeamTables(yd);
    }

    function render2026Draft(yd) {
      const teams = yd.teams_summary;
      const cnt = yd.counts;
      const badges = [
        ['Champion 1st', 'gold-gradient text-black', '優勝', 'border-2 border-yellow-400/80 bg-gradient-to-b from-yellow-950/40 to-gray-900', 'tigers-yellow text-4xl'],
        ['2nd Place', 'silver-gradient text-black', `準優勝 (-${teams[0].total_points - teams[1].total_points}pt)`, 'border border-gray-700 bg-gray-900', 'text-gray-100 text-3xl'],
        ['3rd Place', 'bronze-gradient text-white', '第3位', 'border border-gray-700 bg-gray-900', 'text-amber-500 text-3xl'],
        ['4th Place', 'bg-gray-700 text-gray-200', `第4位 (3位差 -${teams[2].total_points - teams[3].total_points}pt)`, 'border border-gray-800 bg-gray-900/80', 'text-gray-300 text-3xl'],
        ['5th Place', 'bg-gray-800 text-gray-400', '第5位', 'border border-gray-800 bg-gray-900/80', 'text-gray-300 text-3xl'],
      ];

      document.getElementById('teamCardsGrid').innerHTML = teams.map((t, idx) => {
        const [bt, bc, st, cc, pc] = badges[idx];
        const p1 = t.picks[0], p2 = t.picks[1];
        const qStr = (p) => p.role === 'pitcher'
          ? `K-BB+ ${p.kbb_plus ?? '-'} / ${p.kbb_pct ?? '-'}%`
          : (p.ops_plus !== null ? `OPS+ ${p.ops_plus}` : '出場なし');
        return `
          <div class="relative rounded-2xl p-4 flex flex-col justify-between shadow-xl ${cc}">
            <div class="absolute -top-2.5 left-4 ${bc} font-black text-[10px] px-2.5 py-0.5 rounded-full shadow">${bt}</div>
            <div>
              <div class="text-[11px] text-yellow-400/80 font-bold mt-1">${st}</div>
              <div class="text-base font-black text-white truncate" title="${t.owner}">${t.owner}</div>
              <div class="font-black font-num my-0.5 ${pc}">${t.total_points} <span class="text-sm font-normal text-gray-400">pt</span></div>
            </div>
            <div class="text-xs space-y-1.5 pt-2.5 border-t border-gray-800 text-gray-300">
              <div>
                <div class="flex justify-between font-bold"><span>${p1.name}</span><span class="text-yellow-400">${p1.points} pt</span></div>
                <div class="text-[10px] text-gray-400 text-right">${qStr(p1)}</div>
              </div>
              <div>
                <div class="flex justify-between font-bold"><span>${p2.name}</span><span class="text-yellow-400">${p2.points} pt</span></div>
                <div class="text-[10px] text-gray-400 text-right">${qStr(p2)}</div>
              </div>
            </div>
          </div>`;
      }).join('');

      if (userChartInst) userChartInst.destroy();
      userChartInst = new Chart(document.getElementById('userChart').getContext('2d'), {
        type: 'bar',
        data: {
          labels: teams.map(t => t.owner),
          datasets: [
            { label: '主力指名選手', data: teams.map(t => t.picks[0].points), backgroundColor: '#ffe200', borderRadius: 4 },
            { label: '2人目指名選手', data: teams.map(t => t.picks[1].points), backgroundColor: '#f97316', borderRadius: 4 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#d1d5db', font: { size: 11 } } },
            tooltip: {
              callbacks: {
                afterLabel: (ctx) => {
                  const p = teams[ctx.dataIndex].picks[ctx.datasetIndex];
                  return `${p.name}: ${p.points}pt`;
                }
              }
            }
          },
          scales: {
            x: { stacked: true, ticks: { color: '#d1d5db', font: { size: 10 } }, grid: { color: '#1f2937' } },
            y: { stacked: true, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } }
          }
        }
      });

      // Drafted Pitchers Table
      const dp = yd.drafted_players.filter(p => p.role === 'pitcher').sort((a, b) => b.points - a.points);
      document.getElementById('draftPitcherTbody').innerHTML = dp.map(p => {
        const cls = p.kbb_plus >= 100 ? 'text-emerald-400 font-black' : 'text-rose-400 font-bold';
        const r30 = p.kbb_pct_rank_30 ? `${p.kbb_pct_rank_30}/${cnt.rookie_pitchers_30bf}` : '-';
        return `<tr class="hover:bg-gray-800/40">
          <td class="py-2.5 px-3 text-center text-gray-400 font-bold">#${p.draft_order}</td>
          <td class="py-2.5 px-3 sticky-col bg-gray-900 font-bold text-yellow-300">${p.name}</td>
          <td class="py-2.5 px-3 text-white">${p.owner}</td>
          <td class="py-2.5 px-3 text-right font-num text-lg text-yellow-400">${p.bf}</td>
          <td class="py-2.5 px-3 text-right font-bold text-blue-300">${p.k_bb >= 0 ? '+' + p.k_bb : p.k_bb}</td>
          <td class="py-2.5 px-3 text-right font-bold text-white">${p.kbb_pct.toFixed(2)}%</td>
          <td class="py-2.5 px-3 text-right font-num text-lg ${cls}">${p.kbb_plus.toFixed(1)}</td>
          <td class="py-2.5 px-3 text-center text-xs">${p.bf_rank}/${cnt.rookie_pitchers_total}位 / ${r30}位</td>
          <td class="py-2.5 px-3 text-center text-xs text-yellow-300">量${p.hanshin_bf_rank} / 質${p.hanshin_kbb_plus_rank}</td>
        </tr>`;
      }).join('');

      // Drafted Hitters Table
      const dh = yd.drafted_players.filter(h => h.role === 'hitter').sort((a, b) => b.points - a.points);
      document.getElementById('draftHitterTbody').innerHTML = dh.map(h => {
        const opspCls = h.ops_plus === null ? 'text-gray-500' : (h.ops_plus >= 100 ? 'text-emerald-400 font-black' : 'text-rose-400 font-bold');
        const r20 = h.ops_plus_rank_20 ? `${h.ops_plus_rank_20}/${cnt.rookie_hitters_20pa}位` : (h.pa > 0 ? '20打席未満' : '出場なし');
        return `<tr class="hover:bg-gray-800/40">
          <td class="py-2.5 px-3 text-center text-gray-400 font-bold">#${h.draft_order}</td>
          <td class="py-2.5 px-3 sticky-col bg-gray-900 font-bold text-yellow-300">${h.name}</td>
          <td class="py-2.5 px-3 text-white">${h.owner}</td>
          <td class="py-2.5 px-3 text-right font-num text-lg text-yellow-400">${h.pa}</td>
          <td class="py-2.5 px-3 text-right font-bold text-orange-300">${h.tb_bb} <span class="text-[10px] text-gray-500">(${h.tb}+${h.bb})</span></td>
          <td class="py-2.5 px-3 text-right font-bold text-white">${h.ops !== null ? h.ops.toFixed(3) : '-'}</td>
          <td class="py-2.5 px-3 text-right font-num text-lg ${opspCls}">${h.ops_plus !== null ? h.ops_plus.toFixed(1) : '-'}</td>
          <td class="py-2.5 px-3 text-center text-xs">${h.pa_rank}/${cnt.rookie_hitters_total}位 / ${r20}</td>
          <td class="py-2.5 px-3 text-center text-xs text-yellow-300">量${h.hanshin_pa_rank} / 質${h.hanshin_ops_plus_rank ?? '-'}</td>
        </tr>`;
      }).join('');
    }

    function renderTop5(yd) {
      const combined = [
        ...yd.hanshin_pitchers.map(p => ({ ...p, kindLabel: '投', pt: p.bf })),
        ...yd.hanshin_hitters.map(h => ({ ...h, kindLabel: '野', pt: h.pa }))
      ].filter(x => x.pt > 0).sort((a, b) => b.pt - a.pt).slice(0, 5);

      if (combined.length === 0) {
        document.getElementById('top5Grid').innerHTML = '<div class="text-xs text-gray-500 col-span-5">この年の1軍出場新人選手はいません</div>';
        return;
      }

      document.getElementById('top5Grid').innerHTML = combined.map((p, i) => {
        const isP = p.kindLabel === '投';
        const qVal = isP ? `K-BB+ ${p.kbb_plus ?? '-'}` : `OPS+ ${p.ops_plus ?? '-'}`;
        const sub = isP ? `K-BB% ${p.kbb_pct ?? '-'}% / 防${p.era}` : `打率${p.avg} / 塁+四 ${p.tb_bb}`;
        const badgeCls = isP ? 'bg-blue-950 text-blue-300 border-blue-800' : 'bg-orange-950 text-orange-300 border-orange-800';
        const ownerTag = p.owner ? `<div class="text-[10px] text-yellow-300 font-bold truncate">★${p.owner}</div>` : '';
        return `
          <div class="bg-gray-900 border ${i === 0 ? 'border-yellow-400/70' : 'border-gray-800'} rounded-xl p-3.5 flex flex-col justify-between">
            <div class="flex items-center justify-between gap-2 mb-1">
              <span class="text-xs font-black ${i === 0 ? 'text-yellow-400' : 'text-gray-400'}">${i + 1}位</span>
              <span class="px-1.5 py-0.5 text-[10px] rounded border ${badgeCls}">${p.kindLabel}</span>
            </div>
            <div class="font-bold text-sm text-white truncate">${p.name}</div>
            ${ownerTag}
            <div class="flex items-baseline justify-between mt-2 pt-2 border-t border-gray-800">
              <span class="font-num text-3xl text-yellow-400">${p.pt}<span class="text-xs font-sans text-gray-400 ml-0.5">pt</span></span>
              <div class="text-right">
                <div class="text-xs font-bold ${(isP ? p.kbb_plus : p.ops_plus) >= 100 ? 'text-emerald-400' : 'text-gray-300'}">${qVal}</div>
                <div class="text-[10px] text-gray-500">${sub}</div>
              </div>
            </div>
          </div>`;
      }).join('');
    }

    function renderSimulator(yd) {
      const pool = [
        ...yd.hanshin_pitchers.map(p => ({ id: 'P_' + p.name, name: p.name, kind: '投', pt: p.bf, q: p.kbb_plus, qLabel: `K-BB+ ${p.kbb_plus ?? '-'}` })),
        ...yd.hanshin_hitters.map(h => ({ id: 'H_' + h.name, name: h.name, kind: '野', pt: h.pa, q: h.ops_plus, qLabel: `OPS+ ${h.ops_plus ?? '-'}` }))
      ].filter(x => x.pt > 0).sort((a, b) => b.pt - a.pt);

      const chipsEl = document.getElementById('simChips');
      chipsEl.innerHTML = '';
      pool.forEach(item => {
        const btn = document.createElement('button');
        const active = simSelected.some(s => s.id === item.id);
        btn.className = active
          ? 'px-2.5 py-1.5 rounded-xl text-xs font-black bg-yellow-400 text-black border border-yellow-300 shadow transition'
          : 'px-2.5 py-1.5 rounded-xl text-xs font-semibold bg-gray-950 text-gray-200 border border-gray-700 hover:border-yellow-400/60 transition';
        btn.innerHTML = `<span class="opacity-75">[${item.kind}]</span> ${item.name} <span class="${active ? 'text-black' : 'text-yellow-400'} font-bold">${item.pt}pt</span>`;
        btn.onclick = () => {
          const idx = simSelected.findIndex(s => s.id === item.id);
          if (idx >= 0) {
            simSelected.splice(idx, 1);
          } else {
            if (simSelected.length >= 2) simSelected.shift();
            simSelected.push(item);
          }
          renderSimulator(yd);
        };
        chipsEl.appendChild(btn);
      });

      const resBox = document.getElementById('simResultBox');
      if (simSelected.length === 0) {
        resBox.innerHTML = '<div class="text-xs text-gray-400">上の選手チップから2人までタップしてペアを組めます</div>';
      } else {
        const tot = simSelected.reduce((a, b) => a + b.pt, 0);
        const diff2026 = tot - 240;
        const compTxt = diff2026 >= 0
          ? `<span class="text-emerald-400 font-bold">2026年優勝(240pt)を +${diff2026}pt 上回る最強ペア！</span>`
          : `<span class="text-gray-400">2026年優勝(240pt)まで あと ${-diff2026}pt</span>`;
        const namesTxt = simSelected.map(s => `${s.name}(${s.pt}pt / ${s.qLabel})`).join(' ＋ ');
        resBox.innerHTML = `
          <div>
            <div class="text-xs text-gray-300 font-bold mb-0.5">${namesTxt}</div>
            <div class="text-[11px]">${compTxt}</div>
          </div>
          <div class="shrink-0 text-right">
            <span class="text-xs text-gray-400 mr-1">ペア合計</span>
            <span class="font-num text-3xl text-yellow-400">${tot}</span>
            <span class="text-xs text-gray-400">pt</span>
          </div>`;
      }
    }

    function resetSim() {
      simSelected = [];
      renderSimulator(HISTORY_DATA.years[currentView]);
    }

    function renderScatters(yd) {
      const sp = yd.scatter_pitchers || [];
      const pOther = sp.filter(d => !d.is_hanshin);
      const pHanshinUndrafted = sp.filter(d => d.is_hanshin && !d.is_drafted);
      const pHanshinDrafted = sp.filter(d => d.is_drafted);

      document.getElementById('pScatterMeta').textContent = `30打者以上(${yd.counts.rookie_pitchers_30bf}名)＋阪神`;

      if (pitcherScatterInst) pitcherScatterInst.destroy();
      pitcherScatterInst = new Chart(document.getElementById('pitcherScatter').getContext('2d'), {
        type: 'scatter',
        data: {
          datasets: [
            { label: '他球団', data: pOther, backgroundColor: 'rgba(156,163,175,0.4)', pointRadius: 4.5 },
            { label: '阪神(その他)', data: pHanshinUndrafted, backgroundColor: 'rgba(34,211,238,0.85)', borderColor: '#06b6d4', pointRadius: 7 },
            { label: '阪神(2026指名)', data: pHanshinDrafted, backgroundColor: '#ffe200', borderColor: '#fff', borderWidth: 1.5, pointRadius: 9 }
          ].filter(ds => ds.data.length > 0)
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#d1d5db', font: { size: 10 } } },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const d = ctx.raw;
                  return [`${d.name} (${d.team})`, `打者: ${d.x} (${d.bf_rank}位) / 防${d.era}`, `K-BB+: ${d.y} (K-BB% ${d.kbb_pct}% / 実数${d.k_bb})`];
                }
              }
            }
          },
          scales: {
            x: { title: { display: true, text: '対戦打者数（量）', color: '#9ca3af', font: { size: 11 } }, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } },
            y: { title: { display: true, text: 'K-BB+（100=平均）', color: '#9ca3af', font: { size: 11 } }, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } }
          }
        },
        plugins: [avgLinePlugin]
      });

      updateHitterScatter(yd);
    }

    function updateHitterScatter(yd) {
      const sh = (yd.scatter_hitters || []).map(d => ({ ...d, x: d[hitterXMode] }));
      const hOther = sh.filter(d => !d.is_hanshin);
      const hHanshinUndrafted = sh.filter(d => d.is_hanshin && !d.is_drafted);
      const hHanshinDrafted = sh.filter(d => d.is_drafted);

      const labelTxt = hitterXMode === 'pa' ? '打席数' : '塁打＋四球';
      document.getElementById('hitterXLabel').textContent = labelTxt;

      if (hitterScatterInst) hitterScatterInst.destroy();
      hitterScatterInst = new Chart(document.getElementById('hitterScatter').getContext('2d'), {
        type: 'scatter',
        data: {
          datasets: [
            { label: '他球団', data: hOther, backgroundColor: 'rgba(156,163,175,0.4)', pointRadius: 4.5 },
            { label: '阪神(その他)', data: hHanshinUndrafted, backgroundColor: 'rgba(34,211,238,0.85)', borderColor: '#06b6d4', pointRadius: 7 },
            { label: '阪神(2026指名)', data: hHanshinDrafted, backgroundColor: '#ffe200', borderColor: '#fff', borderWidth: 1.5, pointRadius: 9 }
          ].filter(ds => ds.data.length > 0)
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { labels: { color: '#d1d5db', font: { size: 10 } } },
            tooltip: {
              callbacks: {
                label: (ctx) => {
                  const d = ctx.raw;
                  return [`${d.name} (${d.team})`, `打席: ${d.pa} (${d.pa_rank}位) / 塁+四: ${d.tb_bb}`, `OPS+: ${d.y} (OPS ${d.ops?.toFixed(3)} / 打率${d.avg})`];
                }
              }
            }
          },
          scales: {
            x: { title: { display: true, text: `${labelTxt}（量）`, color: '#9ca3af', font: { size: 11 } }, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } },
            y: { title: { display: true, text: 'OPS+（100=平均）', color: '#9ca3af', font: { size: 11 } }, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' } }
          }
        },
        plugins: [avgLinePlugin]
      });
    }

    function switchHitterX(mode) {
      hitterXMode = mode;
      const btnPA = document.getElementById('btnHitterPA');
      const btnTBBB = document.getElementById('btnHitterTBBB');
      if (mode === 'pa') {
        btnPA.className = 'px-2 py-1 rounded bg-yellow-400 text-black font-bold';
        btnTBBB.className = 'px-2 py-1 rounded text-gray-400 hover:text-white';
      } else {
        btnTBBB.className = 'px-2 py-1 rounded bg-yellow-400 text-black font-bold';
        btnPA.className = 'px-2 py-1 rounded text-gray-400 hover:text-white';
      }
      if (HISTORY_DATA.years[currentView]) {
        updateHitterScatter(HISTORY_DATA.years[currentView]);
      }
    }

    function renderHanshinTables(yd) {
      document.getElementById('hanshinPitcherTbody').innerHTML = yd.hanshin_pitchers.map(p => {
        const bg = p.is_drafted ? 'bg-yellow-950/20' : '';
        const stickyBg = p.is_drafted ? 'bg-[#1d190b]' : 'bg-gray-900';
        const tag = p.is_drafted ? `<span class="ml-1 text-[10px] px-1 rounded bg-yellow-400 text-black font-bold">指</span>` : '';
        const qCls = (p.kbb_plus && p.kbb_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 ${bg}">
          <td class="py-2 px-2.5 text-center text-gray-400">${p.hanshin_bf_rank}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${p.name}${tag}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${p.bf}</td>
          <td class="py-2 px-2.5 text-right">${p.ip}</td>
          <td class="py-2 px-2.5 text-right">${p.era}</td>
          <td class="py-2 px-2.5 text-right text-blue-300 font-semibold">${p.bf > 0 ? (p.k_bb >= 0 ? '+' + p.k_bb : p.k_bb) : '-'}</td>
          <td class="py-2 px-2.5 text-right">${p.kbb_pct !== null ? p.kbb_pct.toFixed(2) + '%' : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${p.kbb_plus !== null ? p.kbb_plus.toFixed(1) : '-'}</td>
          <td class="py-2 px-2.5 text-center">${p.bf_rank}位 / ${p.kbb_pct_rank_30 ?? '-'}位</td>
        </tr>`;
      }).join('');

      document.getElementById('hanshinHitterTbody').innerHTML = yd.hanshin_hitters.map(h => {
        const bg = h.is_drafted ? 'bg-yellow-950/20' : '';
        const stickyBg = h.is_drafted ? 'bg-[#1d190b]' : 'bg-gray-900';
        const tag = h.is_drafted ? `<span class="ml-1 text-[10px] px-1 rounded bg-yellow-400 text-black font-bold">指</span>` : '';
        const qCls = (h.ops_plus !== null && h.ops_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 ${bg}">
          <td class="py-2 px-2.5 text-center text-gray-400">${h.hanshin_pa_rank}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${h.name}${tag}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${h.pa}</td>
          <td class="py-2 px-2.5 text-right text-orange-300 font-semibold">${h.tb_bb}</td>
          <td class="py-2 px-2.5 text-right">${h.avg}</td>
          <td class="py-2 px-2.5 text-right">${h.ops !== null ? h.ops.toFixed(3) : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${h.ops_plus !== null ? h.ops_plus.toFixed(1) : '-'}</td>
          <td class="py-2 px-2.5 text-center">${h.pa_rank}位 / ${h.ops_plus_rank_20 ?? '-'}位</td>
        </tr>`;
      }).join('');
    }

    function render12TeamTables(yd) {
      document.getElementById('npbPitcherTbody').innerHTML = yd.top15_pitchers.map(p => {
        const rowCls = p.is_drafted ? 'bg-yellow-950/25 border-l-2 border-yellow-400' : (p.is_hanshin ? 'bg-cyan-950/20 border-l-2 border-cyan-400' : '');
        const stickyBg = p.is_drafted ? 'bg-[#1d190b]' : (p.is_hanshin ? 'bg-[#0b1b24]' : 'bg-gray-900');
        const qCls = (p.kbb_plus && p.kbb_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 ${rowCls}">
          <td class="py-2 px-2.5 text-center font-bold text-gray-400">${p.bf_rank}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${p.name}</td>
          <td class="py-2 px-2.5 text-gray-300">${p.team}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${p.bf}</td>
          <td class="py-2 px-2.5 text-right">${p.ip}</td>
          <td class="py-2 px-2.5 text-right">${p.era}</td>
          <td class="py-2 px-2.5 text-right text-blue-300">${p.bf > 0 ? (p.k_bb >= 0 ? '+' + p.k_bb : p.k_bb) : '-'}</td>
          <td class="py-2 px-2.5 text-right">${p.kbb_pct !== null ? p.kbb_pct.toFixed(2) + '%' : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${p.kbb_plus !== null ? p.kbb_plus.toFixed(1) : '-'}</td>
          <td class="py-2 px-2.5 text-center">${p.kbb_pct_rank_30 ?? '-'}位</td>
        </tr>`;
      }).join('');

      document.getElementById('npbHitterTbody').innerHTML = yd.top15_hitters.map(h => {
        const rowCls = h.is_drafted ? 'bg-yellow-950/25 border-l-2 border-yellow-400' : (h.is_hanshin ? 'bg-cyan-950/20 border-l-2 border-cyan-400' : '');
        const stickyBg = h.is_drafted ? 'bg-[#1d190b]' : (h.is_hanshin ? 'bg-[#0b1b24]' : 'bg-gray-900');
        const qCls = (h.ops_plus !== null && h.ops_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 ${rowCls}">
          <td class="py-2 px-2.5 text-center font-bold text-gray-400">${h.pa_rank}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${h.name}</td>
          <td class="py-2 px-2.5 text-gray-300">${h.team}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${h.pa}</td>
          <td class="py-2 px-2.5 text-right text-orange-300">${h.tb_bb}</td>
          <td class="py-2 px-2.5 text-right">${h.avg}</td>
          <td class="py-2 px-2.5 text-right">${h.ops !== null ? h.ops.toFixed(3) : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${h.ops_plus !== null ? h.ops_plus.toFixed(1) : '-'}</td>
          <td class="py-2 px-2.5 text-center">${h.ops_plus_rank_20 ?? '-'}位</td>
        </tr>`;
      }).join('');
    }

    function renderAllTimeView() {
      const yrSpan = AVAILABLE_YEARS.length > 1 ? `${AVAILABLE_YEARS[AVAILABLE_YEARS.length - 1]}〜${AVAILABLE_YEARS[0]}年` : `${AVAILABLE_YEARS[0]}年`;
      document.getElementById('pageTitle').innerHTML = `阪神ルーキー 歴代比較 <span class="tigers-yellow">(${yrSpan})</span>`;
      document.getElementById('pageSubtitle').textContent = `プロ野球データFreakに掲載されている歴代シーズン（${AVAILABLE_YEARS.length}シーズン）の阪神新人王有資格者を横断比較。`;

      const yt = HISTORY_DATA.all_time.yearly_totals;
      if (yearlyTrendInst) yearlyTrendInst.destroy();
      yearlyTrendInst = new Chart(document.getElementById('yearlyTrendChart').getContext('2d'), {
        type: 'bar',
        data: {
          labels: yt.map(d => `${d.year}`),
          datasets: [
            { label: '投手 合計pt(対戦打者)', data: yt.map(d => d.pitcher_points), backgroundColor: '#3b82f6', borderRadius: 3 },
            { label: '野手 合計pt(打席数)', data: yt.map(d => d.hitter_points), backgroundColor: '#f97316', borderRadius: 3 }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          onClick: (e, elements) => {
            if (elements.length > 0) {
              const yr = yt[elements[0].index].year;
              selectView(String(yr), true);
            }
          },
          plugins: {
            legend: { labels: { color: '#d1d5db', font: { size: 11 } } },
            tooltip: {
              callbacks: {
                afterBody: (items) => {
                  const d = yt[items[0].dataIndex];
                  return [`合計: ${d.total_points}pt`, `投1位: ${d.top_pitcher}`, `野1位: ${d.top_hitter}`];
                }
              }
            }
          },
          scales: {
            x: { stacked: true, ticks: { color: '#d1d5db', font: { size: 10 } }, grid: { color: '#1f2937' } },
            y: { stacked: true, ticks: { color: '#9ca3af' }, grid: { color: '#1f2937' }, title: { display: true, text: '総ポイント (pt)', color: '#9ca3af' } }
          }
        }
      });

      renderAllTimeTables();
    }

    function setAllTimePSort(key) {
      allTimePSort = key;
      ['bf', 'kbb_plus', 'k_bb'].forEach(k => {
        document.getElementById('sortP_' + k).className = k === key
          ? 'px-2 py-1 rounded bg-yellow-400 text-black font-bold'
          : 'px-2 py-1 rounded text-gray-400';
      });
      renderAllTimeTables();
    }

    function setAllTimeHSort(key) {
      allTimeHSort = key;
      ['pa', 'ops_plus', 'tb_bb'].forEach(k => {
        document.getElementById('sortH_' + k).className = k === key
          ? 'px-2 py-1 rounded bg-yellow-400 text-black font-bold'
          : 'px-2 py-1 rounded text-gray-400';
      });
      renderAllTimeTables();
    }

    function renderAllTimeTables() {
      let ps = [...HISTORY_DATA.all_time.pitchers];
      if (allTimePSort === 'kbb_plus') ps = ps.filter(p => p.bf >= 60);
      ps.sort((a, b) => (b[allTimePSort] ?? -999) - (a[allTimePSort] ?? -999));

      document.getElementById('allTimePTbody').innerHTML = ps.slice(0, 30).map((p, idx) => {
        const bg = p.is_drafted ? 'bg-yellow-950/25 border-l-2 border-yellow-400' : '';
        const stickyBg = p.is_drafted ? 'bg-[#1d190b]' : 'bg-gray-900';
        const tag = p.is_drafted ? `<span class="ml-1 text-[10px] px-1 rounded bg-yellow-400 text-black font-bold">26指</span>` : '';
        const qCls = (p.kbb_plus && p.kbb_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 cursor-pointer ${bg}" onclick="selectView('${p.year}', true)">
          <td class="py-2 px-2.5 text-center font-bold text-gray-400">${idx + 1}</td>
          <td class="py-2 px-2.5 text-center text-yellow-300/90 font-semibold">${p.year}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${p.name}${tag}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${p.bf}</td>
          <td class="py-2 px-2.5 text-right">${p.era}</td>
          <td class="py-2 px-2.5 text-right text-blue-300">${p.k_bb >= 0 ? '+' + p.k_bb : p.k_bb}</td>
          <td class="py-2 px-2.5 text-right">${p.kbb_pct !== null ? p.kbb_pct.toFixed(2) + '%' : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${p.kbb_plus !== null ? p.kbb_plus.toFixed(1) : '-'}</td>
        </tr>`;
      }).join('');

      let hs = [...HISTORY_DATA.all_time.hitters];
      if (allTimeHSort === 'ops_plus') hs = hs.filter(h => h.pa >= 40);
      hs.sort((a, b) => (b[allTimeHSort] ?? -999) - (a[allTimeHSort] ?? -999));

      document.getElementById('allTimeHTbody').innerHTML = hs.slice(0, 30).map((h, idx) => {
        const bg = h.is_drafted ? 'bg-yellow-950/25 border-l-2 border-yellow-400' : '';
        const stickyBg = h.is_drafted ? 'bg-[#1d190b]' : 'bg-gray-900';
        const tag = h.is_drafted ? `<span class="ml-1 text-[10px] px-1 rounded bg-yellow-400 text-black font-bold">26指</span>` : '';
        const qCls = (h.ops_plus !== null && h.ops_plus >= 100) ? 'text-emerald-400 font-bold' : 'text-gray-300';
        return `<tr class="hover:bg-gray-800/40 cursor-pointer ${bg}" onclick="selectView('${h.year}', true)">
          <td class="py-2 px-2.5 text-center font-bold text-gray-400">${idx + 1}</td>
          <td class="py-2 px-2.5 text-center text-yellow-300/90 font-semibold">${h.year}</td>
          <td class="py-2 px-2.5 sticky-col ${stickyBg} font-bold text-white">${h.name}${tag}</td>
          <td class="py-2 px-2.5 text-right font-bold text-yellow-400">${h.pa}</td>
          <td class="py-2 px-2.5 text-right text-orange-300">${h.tb_bb}</td>
          <td class="py-2 px-2.5 text-right">${h.avg}</td>
          <td class="py-2 px-2.5 text-right">${h.ops !== null ? h.ops.toFixed(3) : '-'}</td>
          <td class="py-2 px-2.5 text-right ${qCls}">${h.ops_plus !== null ? h.ops_plus.toFixed(1) : '-'}</td>
        </tr>`;
      }).join('');
    }

    function getShareUrl() {
      const u = new URL(window.location.href);
      u.searchParams.set('year', currentView);
      return u.toString();
    }

    function getShareText() {
      const shareUrl = getShareUrl();
      if (currentView === 'all') {
        return `【阪神ルーキー 歴代比較 2009-2026】\n歴代の阪神新人王有資格者の「量×質（K-BB+ / OPS+）」ランキング！\nスマホで見る👇\n${shareUrl}`;
      }
      const yd = HISTORY_DATA.years[currentView];
      if (currentView === '2026' && yd && yd.teams_summary) {
        const t = yd.teams_summary;
        return `【2026 阪神新人王有資格者ドラフト】\n🥇1位: ${t[0].owner} (${t[0].total_points}pt)\n🥈2位: ${t[1].owner} (${t[1].total_points}pt)\n🥉3位: ${t[2].owner} (${t[2].total_points}pt)\n量×質・過去年度比較もスマホで見れるよ👇\n${shareUrl}`;
      }
      if (yd) {
        const hp = yd.hanshin_pitchers[0];
        const hh = yd.hanshin_hitters[0];
        const pTxt = hp && hp.bf > 0 ? `投手1位: ${hp.name}(${hp.bf}pt / K-BB+ ${hp.kbb_plus})` : '投手出場なし';
        const hTxt = hh && hh.pa > 0 ? `野手1位: ${hh.name}(${hh.pa}pt / OPS+ ${hh.ops_plus})` : '野手出場なし';
        return `【${currentView}年 阪神ルーキー分析】\n${pTxt}\n${hTxt}\nこの年で2人選ぶ仮想ドラフトもできるよ👇\n${shareUrl}`;
      }
      return shareUrl;
    }

    function shareToLine() {
      const text = getShareText();
      window.open(`https://line.me/R/share?text=${encodeURIComponent(text)}`, '_blank', 'noopener');
    }

    function copyShareUrl() {
      const url = getShareUrl();
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(() => showToast('URLをコピーしました！LINEに貼って送れます')).catch(() => fallbackCopy(url));
      } else {
        fallbackCopy(url);
      }
    }

    function fallbackCopy(text) {
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast('URLをコピーしました！');
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.classList.remove('opacity-0');
      setTimeout(() => t.classList.add('opacity-0'), 2500);
    }

    init();
  </script>
</body>
</html>
"""

    html = template.replace('__DATA_JSON__', data_json_str)
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description='Hanshin Rookie Draft Analyzer (2009-2026)')
    parser.add_argument('--fetch-range', nargs=2, type=int, metavar=('START', 'END'), help='Fetch year range and write JSON')
    parser.add_argument('--out', type=str, help='Output file path for --fetch-range')
    parser.add_argument('--merge', nargs='+', type=str, help='Merge fetched partial JSON files into history_data.json & index.html')
    args = parser.parse_args()

    if args.fetch_range:
        start_y, end_y = args.fetch_range
        out_file = args.out or os.path.join(BASE_DIR, f'part_{start_y}_{end_y}.json')
        result_years = {}
        existing = load_existing_history()
        for y in range(start_y, end_y + 1):
            print(f'Fetching {y}...')
            try:
                ydata = fetch_year_data(y)
                result_years[str(y)] = ydata
                print(f'  OK {y}: hitters={ydata["counts"]["hanshin_hitters"]}, pitchers={ydata["counts"]["hanshin_pitchers"]}')
            except Exception as e:
                print(f'  WARN {y} fetch failed: {e}')
                if str(y) in existing['years']:
                    print(f'  Using existing fallback cache for {y}')
                    result_years[str(y)] = existing['years'][str(y)]
                else:
                    raise
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump({'years': result_years}, f, ensure_ascii=False)
        print(f'Saved partial range to {out_file}')
        return

    if args.merge:
        history_obj = load_existing_history()
        for path in args.merge:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    part = json.load(f)
                    for y_str, ydata in part.get('years', {}).items():
                        history_obj['years'][y_str] = ydata
        save_outputs(history_obj)
        return

    # 通常実行：既存キャッシュをベースに2026年のみ最新化を試みる
    history_obj = load_existing_history()
    try:
        print('Fetching latest 2026 data...')
        y2026 = fetch_year_data(2026)
        history_obj['years']['2026'] = y2026
        print('Updated 2026 data successfully.')
    except Exception as e:
        print(f'Note: 2026 live fetch skipped/failed ({e}). Using cached data.')

    if not history_obj['years']:
        raise RuntimeError('No year data available!')

    save_outputs(history_obj)


if __name__ == '__main__':
    main()
