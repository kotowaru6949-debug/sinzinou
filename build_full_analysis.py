import urllib.request
import re
import json
import os

# ドラフト指名情報
DRAFT_PICKS = [
    {'order': 1,  'owner': 'ケツからぼたもち',       'player': '立石 正広',   'pos': '内野手', 'role': 'hitter'},
    {'order': 2,  'owner': 'おならぶーぶぶ',         'player': '中川 勇斗',   'pos': '捕手',   'role': 'hitter'},
    {'order': 3,  'owner': 'パパパパパパパパパパワー', 'player': '工藤 泰成',   'pos': '投手',   'role': 'pitcher'},
    {'order': 4,  'owner': '毛玉おやぢ',             'player': '下村 海翔',   'pos': '投手',   'role': 'pitcher'},
    {'order': 5,  'owner': 'あッチょんぶりけ',       'player': '岡城 快生',   'pos': '外野手', 'role': 'hitter'},
    {'order': 6,  'owner': 'ケツからぼたもち',       'player': '今朝丸 裕喜', 'pos': '投手',   'role': 'pitcher'},
    {'order': 7,  'owner': 'おならぶーぶぶ',         'player': '木下 里都',   'pos': '投手',   'role': 'pitcher'},
    {'order': 8,  'owner': 'パパパパパパパパパパワー', 'player': '山田 脩也',   'pos': '内野手', 'role': 'hitter'},
    {'order': 9,  'owner': '毛玉おやぢ',             'player': '百崎 蒼生',   'pos': '内野手', 'role': 'hitter'},
    {'order': 10, 'owner': 'あッチょんぶりけ',       'player': '嶋村 麟士朗', 'pos': '捕手',   'role': 'hitter'},
]

URLS = {
    'h1': 'https://baseball-data.com/stats/hitter2-all/tpa-1.html',
    'p1': 'https://baseball-data.com/stats/pitcher2-all/ip3-1.html',
    'h7': 'https://baseball-data.com/stats/hitter2-all/tpa-7.html',
    'p7': 'https://baseball-data.com/stats/pitcher2-all/ip3-7.html',
}

def normalize_name(name):
    # 全角・半角スペース除去、異体字統一
    s = name.replace(' ', '').replace('\u3000', '')
    s = s.replace('﨑', '崎').replace('髙', '高')
    return s

def to_int(val):
    try:
        return int(val)
    except:
        return 0

def to_float(val):
    try:
        return float(val)
    except:
        return 0.0

def fetch_parsed(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='ignore')
    tr_th_m = re.search(r'<tr[^>]*>(.*?)</tr>', html, re.S)
    ths = [re.sub(r'<[^>]+>', '', th).strip() for th in re.findall(r'<th[^>]*>(.*?)</th>', tr_th_m.group(1), re.S)]
    rows = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S):
        tds = [re.sub(r'<[^>]+>', '', td).strip() for td in re.findall(r'<td[^>]*>(.*?)</td>', r, re.S)]
        if tds and len(tds) == len(ths):
            rows.append(dict(zip(ths, tds)))
    return ths, rows

def main():
    print('Fetching data from baseball-data.com...')
    _, h1 = fetch_parsed(URLS['h1'])
    _, p1 = fetch_parsed(URLS['p1'])
    _, h7 = fetch_parsed(URLS['h7'])
    _, p7 = fetch_parsed(URLS['p7'])

    # 1軍リーグ全体平均の算出
    tot_h_pa = sum(to_int(r['打席数']) for r in h1)
    tot_ab   = sum(to_int(r['打数']) for r in h1)
    tot_h    = sum(to_int(r['安打']) for r in h1)
    tot_tb   = sum(to_int(r['塁打']) for r in h1)
    tot_bb   = sum(to_int(r['四球']) for r in h1)
    tot_hbp  = sum(to_int(r['死球']) for r in h1)
    tot_sf   = sum(to_int(r['犠飛']) for r in h1)

    lg_obp = (tot_h + tot_bb + tot_hbp) / (tot_ab + tot_bb + tot_hbp + tot_sf)
    lg_slg = tot_tb / tot_ab
    lg_ops = lg_obp + lg_slg

    tot_p_bf  = sum(to_int(r['打者']) for r in p1)
    tot_p_k   = sum(to_int(r['奪三振']) for r in p1)
    tot_p_bb  = sum(to_int(r['与四球']) for r in p1)
    lg_k_pct  = tot_p_k / tot_p_bf * 100
    lg_bb_pct = tot_p_bb / tot_p_bf * 100
    lg_kbb_pct = (tot_p_k - tot_p_bb) / tot_p_bf * 100

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

    # 指名マップ作成
    draft_map_hitter = {}
    draft_map_pitcher = {}
    for d in DRAFT_PICKS:
        nkey = normalize_name(d['player'])
        if d['role'] == 'hitter':
            draft_map_hitter[nkey] = d
        else:
            draft_map_pitcher[nkey] = d

    # 全新人王有資格野手 (107名) 指標算出
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
        tb_bb_hbp = tb + bb + hbp

        is_hanshin = (team == '阪神')
        draft_info = draft_map_hitter.get(nkey) if is_hanshin else None

        rookie_hitters.append({
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
            'tb_bb_hbp': tb_bb_hbp,
            'obp': round(obp, 3) if pa > 0 else None,
            'slg': round(slg, 3) if pa > 0 else None,
            'ops': round(ops, 3) if pa > 0 else None,
            'ops_plus': round(ops_plus, 1) if ops_plus is not None else None,
            'points': pa,
        })

    # 野手ランキング計算
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

    # 全新人王有資格投手 (139名) 指標算出
    rookie_pitchers = []
    for r in p7:
        name_raw = r['選手名'].replace('\u3000', ' ')
        nkey = normalize_name(name_raw)
        team = r['チーム']
        bf = to_int(r['打者'])
        g  = to_int(r['試合'])
        w  = to_int(r['勝利'])
        l  = to_int(r['敗北'])
        sv = to_int(r['セlブ'])
        hld = to_int(r['ホlルド'])
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
        kbb_plus = (100 * kbb_pct / lg_kbb_pct) if bf > 0 else None

        is_hanshin = (team == '阪神')
        draft_info = draft_map_pitcher.get(nkey) if is_hanshin else None

        rookie_pitchers.append({
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

    # 投手ランキング計算
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

    # ドラフトチーム集計
    owners_order = ['おならぶーぶぶ', 'パパパパパパパパパパワー', '毛玉おやぢ', 'ケツからぼたもち', 'あッチょんぶりけ']
    teams_summary = []
    h_by_nkey = {x['nkey']: x for x in rookie_hitters if x['is_hanshin']}
    p_by_nkey = {x['nkey']: x for x in rookie_pitchers if x['is_hanshin']}

    drafted_players = []
    for d in DRAFT_PICKS:
        nkey = normalize_name(d['player'])
        if d['role'] == 'hitter':
            pdata = h_by_nkey[nkey]
        else:
            pdata = p_by_nkey[nkey]
        drafted_players.append({'role': d['role'], **pdata})

    for owner in owners_order:
        picks = [p for p in drafted_players if p['owner'] == owner]
        picks_sorted = sorted(picks, key=lambda x: x['points'], reverse=True)
        tot_pts = sum(p['points'] for p in picks)
        teams_summary.append({
            'owner': owner,
            'total_points': tot_pts,
            'picks': picks_sorted
        })
    teams_summary.sort(key=lambda x: x['total_points'], reverse=True)
    for idx, t in enumerate(teams_summary, 1):
        t['rank'] = idx

    # 保存用JSON構築
    output_data = {
        'league_avg': league_avg,
        'counts': {
            'rookie_hitters_total': len(rookie_hitters),
            'rookie_hitters_active': len(h_active),
            'rookie_hitters_20pa': len(h_20),
            'rookie_pitchers_total': len(rookie_pitchers),
            'rookie_pitchers_active': len(p_active),
            'rookie_pitchers_30bf': len(p_30),
            'hanshin_hitters': len(h_hanshin),
            'hanshin_pitchers': len(p_hanshin),
        },
        'teams_summary': teams_summary,
        'drafted_players': drafted_players,
        'hanshin_hitters': sorted(h_hanshin, key=lambda x: (x['pa'], x['tb_bb']), reverse=True),
        'hanshin_pitchers': sorted(p_hanshin, key=lambda x: x['bf'], reverse=True),
        'rookie_hitters_all': rookie_hitters,
        'rookie_pitchers_by_bf': sorted(rookie_pitchers, key=lambda x: x['bf'], reverse=True),
        'rookie_pitchers_top_kbb': sorted(p_30, key=lambda x: x['kbb_pct'], reverse=True),
        'rookie_hitters_top_ops': sorted(h_20, key=lambda x: x['ops_plus'], reverse=True),
    }

    out_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(out_dir, 'game_result.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f'Saved {json_path}')

    html_path = os.path.join(out_dir, 'index.html')
    generate_html(output_data, html_path)
    print(f'Saved {html_path}')

def generate_html(data, html_path):
    la = data['league_avg']
    cnt = data['counts']
    teams = data['teams_summary']
    drafted_p = [p for p in data['drafted_players'] if p['role'] == 'pitcher']
    drafted_h = [p for p in data['drafted_players'] if p['role'] == 'hitter']

    # 散布図用データ準備
    # 投手: BF>=30 の72名（阪神は全登板ありを含む）
    scatter_p_other = []
    scatter_p_hanshin_undrafted = []
    scatter_p_hanshin_drafted = []
    for p in data['rookie_pitchers_by_bf']:
        if p['bf'] == 0:
            continue
        if not p['is_hanshin'] and p['bf'] < 30:
            continue
        pt = {
            'x': p['bf'],
            'y': p['kbb_plus'],
            'name': p['name'],
            'team': p['team'],
            'kbb_pct': p['kbb_pct'],
            'k_bb': p['k_bb'],
            'era': p['era'],
            'ip': p['ip'],
            'owner': p['owner'] or '未指名',
            'bf_rank': p['bf_rank'],
            'kbb_pct_rank_30': p['kbb_pct_rank_30'],
        }
        if p['is_drafted']:
            scatter_p_hanshin_drafted.append(pt)
        elif p['is_hanshin']:
            scatter_p_hanshin_undrafted.append(pt)
        else:
            scatter_p_other.append(pt)

    # 野手: PA>=20 の43名（阪神はPA>0全てを含む）
    scatter_h_other = []
    scatter_h_hanshin_undrafted = []
    scatter_h_hanshin_drafted = []
    for h in data['rookie_hitters_all']:
        if h['pa'] == 0:
            continue
        if not h['is_hanshin'] and h['pa'] < 20:
            continue
        pt = {
            'pa': h['pa'],
            'tb_bb': h['tb_bb'],
            'y': h['ops_plus'],
            'name': h['name'],
            'team': h['team'],
            'ops': h['ops'],
            'avg': h['avg'],
            'tb': h['tb'],
            'bb': h['bb'],
            'owner': h['owner'] or '未指名',
            'pa_rank': h['pa_rank'],
            'ops_plus_rank_20': h['ops_plus_rank_20'],
        }
        if h['is_drafted']:
            scatter_h_hanshin_drafted.append(pt)
        elif h['is_hanshin']:
            scatter_h_hanshin_undrafted.append(pt)
        else:
            scatter_h_other.append(pt)

    # 12球団投手トップ15 (BF順) + 阪神指名投手
    p_top15 = data['rookie_pitchers_by_bf'][:15]
    p_top_ids = {x['nkey'] for x in p_top15}
    p_compare = list(p_top15)
    for x in data['hanshin_pitchers']:
        if x['is_drafted'] and x['nkey'] not in p_top_ids:
            p_compare.append(x)

    # 12球団野手トップ15 (PA順) + 阪神指名野手
    h_top15 = data['rookie_hitters_all'][:15]
    h_top_ids = {x['nkey'] for x in h_top15}
    h_compare = list(h_top15)
    for x in data['hanshin_hitters']:
        if x['is_drafted'] and x['nkey'] not in h_top_ids:
            h_compare.append(x)

    # HTMLパーツ生成ヘルパー
    def render_pitcher_draft_rows():
        rows_html = []
        for p in sorted(drafted_p, key=lambda x: x['points'], reverse=True):
            kbb_p_badge = 'text-emerald-400 font-black' if p['kbb_plus'] >= 100 else 'text-rose-400 font-bold'
            rank30_str = f"{p['kbb_pct_rank_30']}位 / {cnt['rookie_pitchers_30bf']}人" if p['kbb_pct_rank_30'] else '-'
            rows_html.append(f"""
            <tr class="hover:bg-gray-800/50 transition">
              <td class="py-3 px-3 text-center text-gray-400 font-bold">#{p['draft_order']}</td>
              <td class="py-3 px-3 font-semibold text-white">{p['owner']}</td>
              <td class="py-3 px-3 font-bold text-yellow-300">{p['name']}</td>
              <td class="py-3 px-3 text-right font-num text-xl text-yellow-400">{p['bf']} <span class="text-xs font-sans text-gray-500">pt</span></td>
              <td class="py-3 px-3 text-right font-bold text-blue-300">{p['k_bb']:+d} <span class="text-xs text-gray-500">({p['k']}K-{p['bb']}BB)</span></td>
              <td class="py-3 px-3 text-right font-bold text-white">{p['kbb_pct']:.2f}%</td>
              <td class="py-3 px-3 text-right font-num text-xl {kbb_p_badge}">{p['kbb_plus']:.1f}</td>
              <td class="py-3 px-3 text-center text-xs"><span class="px-2 py-0.5 rounded bg-gray-800 text-gray-200">{p['bf_rank']}位 / {cnt['rookie_pitchers_total']}人</span></td>
              <td class="py-3 px-3 text-center text-xs"><span class="px-2 py-0.5 rounded bg-blue-950/60 text-blue-200 border border-blue-800/50">{rank30_str}</span></td>
              <td class="py-3 px-3 text-center text-xs text-yellow-300/90">量:{p['hanshin_bf_rank']}位 / 質:{p['hanshin_kbb_plus_rank']}位 <span class="text-gray-500">(全{cnt['hanshin_pitchers']}人)</span></td>
            </tr>""")
        return ''.join(rows_html)

    def render_hitter_draft_rows():
        rows_html = []
        for h in sorted(drafted_h, key=lambda x: x['points'], reverse=True):
            ops_str = f"{h['ops']:.3f}" if h['ops'] is not None else '-'
            opsp_str = f"{h['ops_plus']:.1f}" if h['ops_plus'] is not None else '-'
            opsp_cls = 'text-emerald-400 font-black' if (h['ops_plus'] is not None and h['ops_plus'] >= 100) else ('text-rose-400 font-bold' if h['ops_plus'] is not None else 'text-gray-500')
            rank20_str = f"{h['ops_plus_rank_20']}位 / {cnt['rookie_hitters_20pa']}人" if h['ops_plus_rank_20'] else ('対象外(20打席未満)' if h['pa'] > 0 else '出場なし')
            h_qual_rank = f"{h['hanshin_ops_plus_rank']}位" if h['hanshin_ops_plus_rank'] else '-'
            rows_html.append(f"""
            <tr class="hover:bg-gray-800/50 transition">
              <td class="py-3 px-3 text-center text-gray-400 font-bold">#{h['draft_order']}</td>
              <td class="py-3 px-3 font-semibold text-white">{h['owner']}</td>
              <td class="py-3 px-3 font-bold text-yellow-300">{h['name']} <span class="text-xs font-normal text-gray-400">({h['pos']})</span></td>
              <td class="py-3 px-3 text-right font-num text-xl text-yellow-400">{h['pa']} <span class="text-xs font-sans text-gray-500">pt</span></td>
              <td class="py-3 px-3 text-right font-bold text-orange-300">{h['tb_bb']} <span class="text-xs text-gray-500">({h['tb']}塁打+{h['bb']}四球)</span></td>
              <td class="py-3 px-3 text-right font-bold text-white">{ops_str}</td>
              <td class="py-3 px-3 text-right font-num text-xl {opsp_cls}">{opsp_str}</td>
              <td class="py-3 px-3 text-center text-xs"><span class="px-2 py-0.5 rounded bg-gray-800 text-gray-200">{h['pa_rank']}位 / {cnt['rookie_hitters_total']}人</span></td>
              <td class="py-3 px-3 text-center text-xs"><span class="px-2 py-0.5 rounded bg-orange-950/60 text-orange-200 border border-orange-800/50">{rank20_str}</span></td>
              <td class="py-3 px-3 text-center text-xs text-yellow-300/90">量:{h['hanshin_pa_rank']}位 / 質:{h_qual_rank} <span class="text-gray-500">(全{cnt['hanshin_hitters']}人)</span></td>
            </tr>""")
        return ''.join(rows_html)

    def render_hanshin_pitchers():
        rows = []
        for p in data['hanshin_pitchers']:
            badge = f'<span class="px-2 py-0.5 text-xs rounded bg-yellow-400 text-black font-bold">指名 ({p["owner"]})</span>' if p['is_drafted'] else '<span class="px-2 py-0.5 text-xs rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60">未指名</span>'
            kbb_pct = f"{p['kbb_pct']:.2f}%" if p['kbb_pct'] is not None else '-'
            kbb_plus = f"{p['kbb_plus']:.1f}" if p['kbb_plus'] is not None else '-'
            kbb_cls = 'text-emerald-400 font-bold' if (p['kbb_plus'] and p['kbb_plus'] >= 100) else 'text-gray-400'
            r30 = f"{p['kbb_pct_rank_30']}位" if p['kbb_pct_rank_30'] else '-'
            row_bg = 'bg-yellow-950/15' if p['is_drafted'] else ''
            rows.append(f"""
            <tr class="hover:bg-gray-800/40 {row_bg}">
              <td class="py-2.5 px-3 text-center text-xs text-gray-400">{p['hanshin_bf_rank']}</td>
              <td class="py-2.5 px-3 font-bold text-white">{p['name']}</td>
              <td class="py-2.5 px-3">{badge}</td>
              <td class="py-2.5 px-3 text-right font-bold text-yellow-400">{p['bf']}</td>
              <td class="py-2.5 px-3 text-right text-xs text-gray-300">{p['ip']}</td>
              <td class="py-2.5 px-3 text-right text-xs text-gray-300">{p['era']}</td>
              <td class="py-2.5 px-3 text-right font-semibold text-blue-300">{p['k_bb']:+d}</td>
              <td class="py-2.5 px-3 text-right text-white">{kbb_pct}</td>
              <td class="py-2.5 px-3 text-right {kbb_cls}">{kbb_plus}</td>
              <td class="py-2.5 px-3 text-center text-xs text-gray-300">{p['bf_rank']}位 / {r30}</td>
            </tr>""")
        return ''.join(rows)

    def render_hanshin_hitters():
        rows = []
        for h in data['hanshin_hitters']:
            badge = f'<span class="px-2 py-0.5 text-xs rounded bg-yellow-400 text-black font-bold">指名 ({h["owner"]})</span>' if h['is_drafted'] else '<span class="px-2 py-0.5 text-xs rounded bg-cyan-950 text-cyan-300 border border-cyan-700/60">未指名</span>'
            ops_s = f"{h['ops']:.3f}" if h['ops'] is not None else '-'
            opsp_s = f"{h['ops_plus']:.1f}" if h['ops_plus'] is not None else '-'
            opsp_cls = 'text-emerald-400 font-bold' if (h['ops_plus'] is not None and h['ops_plus'] >= 100) else 'text-gray-400'
            r20 = f"{h['ops_plus_rank_20']}位" if h['ops_plus_rank_20'] else '-'
            row_bg = 'bg-yellow-950/15' if h['is_drafted'] else ''
            rows.append(f"""
            <tr class="hover:bg-gray-800/40 {row_bg}">
              <td class="py-2.5 px-3 text-center text-xs text-gray-400">{h['hanshin_pa_rank']}</td>
              <td class="py-2.5 px-3 font-bold text-white">{h['name']}</td>
              <td class="py-2.5 px-3">{badge}</td>
              <td class="py-2.5 px-3 text-right font-bold text-yellow-400">{h['pa']}</td>
              <td class="py-2.5 px-3 text-right font-semibold text-orange-300">{h['tb_bb']}</td>
              <td class="py-2.5 px-3 text-right text-xs text-gray-300">{h['avg']}</td>
              <td class="py-2.5 px-3 text-right text-white">{ops_s}</td>
              <td class="py-2.5 px-3 text-right {opsp_cls}">{opsp_s}</td>
              <td class="py-2.5 px-3 text-center text-xs text-gray-300">{h['pa_rank']}位 / {r20}</td>
            </tr>""")
        return ''.join(rows)

    def render_12team_pitchers():
        rows = []
        for p in p_compare:
            is_t = p['is_hanshin']
            row_cls = 'bg-yellow-950/30 border-l-4 border-yellow-400' if p['is_drafted'] else ('bg-cyan-950/20 border-l-4 border-cyan-400' if is_t else '')
            tag = f' <span class="text-xs text-yellow-300 font-bold">★{p["owner"]}</span>' if p['is_drafted'] else (' <span class="text-xs text-cyan-300">(阪神未指名)</span>' if is_t else '')
            kbb_cls = 'text-emerald-400 font-bold' if (p['kbb_plus'] and p['kbb_plus'] >= 100) else 'text-gray-300'
            r30 = f"{p['kbb_pct_rank_30']}位" if p['kbb_pct_rank_30'] else '-'
            rows.append(f"""
            <tr class="hover:bg-gray-800/40 {row_cls}">
              <td class="py-2 px-3 text-center font-bold text-gray-300">{p['bf_rank']}位</td>
              <td class="py-2 px-3 font-bold text-white">{p['name']}{tag}</td>
              <td class="py-2 px-3 text-xs text-gray-300">{p['team']}</td>
              <td class="py-2 px-3 text-right font-bold text-yellow-400">{p['bf']}</td>
              <td class="py-2 px-3 text-right text-xs text-gray-300">{p['ip']}</td>
              <td class="py-2 px-3 text-right text-xs text-gray-300">{p['era']}</td>
              <td class="py-2 px-3 text-right text-blue-300 font-semibold">{p['k_bb']:+d}</td>
              <td class="py-2 px-3 text-right">{p['kbb_pct']:.2f}%</td>
              <td class="py-2 px-3 text-right {kbb_cls}">{p['kbb_plus']:.1f}</td>
              <td class="py-2 px-3 text-center text-xs text-gray-300">{r30}</td>
            </tr>""")
        return ''.join(rows)

    def render_12team_hitters():
        rows = []
        for h in h_compare:
            is_t = h['is_hanshin']
            row_cls = 'bg-yellow-950/30 border-l-4 border-yellow-400' if h['is_drafted'] else ('bg-cyan-950/20 border-l-4 border-cyan-400' if is_t else '')
            tag = f' <span class="text-xs text-yellow-300 font-bold">★{h["owner"]}</span>' if h['is_drafted'] else (' <span class="text-xs text-cyan-300">(阪神未指名)</span>' if is_t else '')
            ops_s = f"{h['ops']:.3f}" if h['ops'] is not None else '-'
            opsp_s = f"{h['ops_plus']:.1f}" if h['ops_plus'] is not None else '-'
            opsp_cls = 'text-emerald-400 font-bold' if (h['ops_plus'] is not None and h['ops_plus'] >= 100) else 'text-gray-300'
            r20 = f"{h['ops_plus_rank_20']}位" if h['ops_plus_rank_20'] else '-'
            rows.append(f"""
            <tr class="hover:bg-gray-800/40 {row_cls}">
              <td class="py-2 px-3 text-center font-bold text-gray-300">{h['pa_rank']}位</td>
              <td class="py-2 px-3 font-bold text-white">{h['name']}{tag}</td>
              <td class="py-2 px-3 text-xs text-gray-300">{h['team']}</td>
              <td class="py-2 px-3 text-right font-bold text-yellow-400">{h['pa']}</td>
              <td class="py-2 px-3 text-right font-semibold text-orange-300">{h['tb_bb']}</td>
              <td class="py-2 px-3 text-right text-xs text-gray-300">{h['avg']}</td>
              <td class="py-2 px-3 text-right">{ops_s}</td>
              <td class="py-2 px-3 text-right {opsp_cls}">{opsp_s}</td>
              <td class="py-2 px-3 text-center text-xs text-gray-300">{r20}</td>
            </tr>""")
        return ''.join(rows)

    def render_team_cards():
        badges = [
            ('Champion 1st', 'gold-gradient text-black', '優勝', 'border-2 border-yellow-400/80 bg-gradient-to-b from-yellow-950/40 to-gray-900 md:order-2 md:-translate-y-2', 'tigers-yellow text-5xl'),
            ('2nd Place', 'silver-gradient text-black', f'準優勝 (差: -{teams[0]["total_points"] - teams[1]["total_points"]}pt)', 'border border-gray-700 bg-gray-900 md:order-1', 'text-gray-100 text-4xl'),
            ('3rd Place', 'bronze-gradient text-white', '第3位', 'border border-gray-700 bg-gray-900 md:order-3', 'text-amber-500 text-4xl'),
            ('4th Place', 'bg-gray-700 text-gray-200', f'第4位 (3位差: -{teams[2]["total_points"] - teams[3]["total_points"]}pt)', 'border border-gray-800 bg-gray-900/80 md:order-4', 'text-gray-300 text-3xl'),
            ('5th Place', 'bg-gray-800 text-gray-400', '第5位', 'border border-gray-800 bg-gray-900/80 md:order-5', 'text-gray-300 text-3xl'),
        ]
        cards = []
        for idx, t in enumerate(teams):
            b_title, b_cls, sub_txt, card_cls, pts_cls = badges[idx]
            p1, p2 = t['picks'][0], t['picks'][1]
            def qual_txt(p):
                if p['role'] == 'pitcher':
                    return f"K-BB+ {p['kbb_plus']:.1f} / {p['kbb_pct']:.1f}%"
                else:
                    return f"OPS+ {p['ops_plus']:.1f}" if p['ops_plus'] is not None else "出場なし"
            cards.append(f"""
            <div class="relative rounded-2xl p-5 flex flex-col justify-between shadow-xl {card_cls}">
              <div class="absolute -top-3 left-1/2 -translate-x-1/2 {b_cls} font-black text-xs px-3 py-0.5 rounded-full shadow-md whitespace-nowrap">
                {b_title}
              </div>
              <div>
                <div class="text-xs text-yellow-400/80 font-bold mb-1 mt-1">{sub_txt}</div>
                <div class="text-lg font-black text-white truncate" title="{t['owner']}">{t['owner']}</div>
                <div class="font-black font-num my-1 {pts_cls}">{t['total_points']} <span class="text-base font-normal text-gray-400">pt</span></div>
              </div>
              <div class="text-xs space-y-2 pt-3 border-t border-gray-800 text-gray-300">
                <div>
                  <div class="flex justify-between font-bold"><span>{p1['name']} ({p1['pos'][:1]})</span><span class="text-yellow-400">{p1['points']} pt</span></div>
                  <div class="text-[11px] text-gray-400 text-right">{qual_txt(p1)}</div>
                </div>
                <div>
                  <div class="flex justify-between font-bold"><span>{p2['name']} ({p2['pos'][:1]})</span><span class="text-yellow-400">{p2['points']} pt</span></div>
                  <div class="text-[11px] text-gray-400 text-right">{qual_txt(p2)}</div>
                </div>
              </div>
            </div>""")
        return ''.join(cards)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>阪神 新人王有資格者ドラフト｜量×質＆全新人立ち位置ダッシュボード</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;600;700;900&family=Teko:wght@600;700&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Noto Sans JP', sans-serif; background-color: #0b0d11; color: #f3f4f6; }}
    .font-num {{ font-family: 'Teko', sans-serif; letter-spacing: 0.04em; }}
    .tigers-yellow {{ color: #ffe200; }}
    .gold-gradient {{ background: linear-gradient(135deg, #ffd700 0%, #b8860b 100%); }}
    .silver-gradient {{ background: linear-gradient(135deg, #e0e0e0 0%, #8a9ba8 100%); }}
    .bronze-gradient {{ background: linear-gradient(135deg, #cd7f32 0%, #8b4513 100%); }}
  </style>
</head>
<body class="p-4 md:p-8 min-h-screen">
  <div class="max-w-7xl mx-auto space-y-10">

    <!-- Header -->
    <header class="text-center py-6 border-b border-gray-800">
      <div class="inline-block px-3 py-1 mb-2 text-xs font-bold tracking-wider uppercase bg-yellow-400 text-black rounded-full">
        Hanshin Tigers Rookie Draft Analytics
      </div>
      <h1 class="text-3xl md:text-5xl font-black tracking-tight text-white mb-3">
        新人王有資格者ドラフト <span class="tigers-yellow">量 × 質＆全体立ち位置</span>
      </h1>
      <p class="text-xs md:text-sm text-gray-400 max-w-4xl mx-auto leading-relaxed">
        独自ルール（1軍起用量：投手=対戦打者 / 野手=打席数）に加え、1軍リーグ平均を100としたセイバー指標で「質と量」を分析。<br>
        <span class="text-gray-300 font-semibold">【1軍平均基準値】</span>
        投手 ({la['pitcher_count']}名・{la['total_bf']:,}打者)：K% <span class="text-blue-300">{la['lg_k_pct']}%</span> / BB% <span class="text-blue-300">{la['lg_bb_pct']}%</span> / <span class="text-yellow-300 font-bold">K-BB% {la['lg_kbb_pct']}% (= K-BB+ 100)</span>
        ｜ 野手 ({la['hitter_count']}名・{la['total_pa']:,}打席)：出塁率 <span class="text-orange-300">{la['lg_obp']:.3f}</span> / 長打率 <span class="text-orange-300">{la['lg_slg']:.3f}</span> / <span class="text-yellow-300 font-bold">OPS {la['lg_ops']:.3f} (= OPS+ 100)</span>
      </p>
    </header>

    <!-- Section 1: Draft Ranking & Team Summary -->
    <section class="space-y-6">
      <h2 class="text-xl font-bold flex items-center gap-2 text-yellow-400">
        <span>1. ドラフト最終順位 ＆ チーム別「量×質」サマリー</span>
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        {render_team_cards()}
      </div>
      <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg">
        <h3 class="text-base font-bold text-white mb-3">指名者別 獲得ポイント内訳（独自ルール）</h3>
        <div class="relative h-60">
          <canvas id="userChart"></canvas>
        </div>
      </div>
    </section>

    <!-- Section 2: Drafted 10 Players Quality x Quantity & Rankings -->
    <section class="space-y-6">
      <h2 class="text-xl font-bold flex items-center gap-2 text-yellow-400">
        <span>2. 指名10選手の「量 × 質」詳細＆新人王有資格者内ランキング</span>
      </h2>

      <!-- Pitchers -->
      <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
        <div class="px-5 py-3.5 bg-blue-950/30 border-b border-gray-800 flex flex-wrap items-center justify-between gap-2">
          <h3 class="text-base font-bold text-blue-300">⚾ 投手編（指名4名）｜ 量：対戦打者・K-BB実数 ／ 質：K-BB%・K-BB+</h3>
          <span class="text-xs text-gray-400">K-BB+ = 100 × (選手K-BB% / 1軍平均 {la['lg_kbb_pct']}%)</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm text-gray-300 whitespace-nowrap">
            <thead class="bg-gray-950 text-xs text-gray-400 border-b border-gray-800">
              <tr>
                <th class="py-2.5 px-3 text-center">指名順</th>
                <th class="py-2.5 px-3">指名者</th>
                <th class="py-2.5 px-3">選手名</th>
                <th class="py-2.5 px-3 text-right">対戦打者(pt)</th>
                <th class="py-2.5 px-3 text-right">K-BB (実数)</th>
                <th class="py-2.5 px-3 text-right">K-BB%</th>
                <th class="py-2.5 px-3 text-right">K-BB+</th>
                <th class="py-2.5 px-3 text-center">12球団新人 量順位</th>
                <th class="py-2.5 px-3 text-center">12球団新人 質順位(30打者以上)</th>
                <th class="py-2.5 px-3 text-center">阪神新人内順位</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-800/60">
              {render_pitcher_draft_rows()}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Hitters -->
      <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
        <div class="px-5 py-3.5 bg-orange-950/30 border-b border-gray-800 flex flex-wrap items-center justify-between gap-2">
          <h3 class="text-base font-bold text-orange-300">🏏 野手編（指名6名）｜ 量：打席数・塁打＋四球 ／ 質：OPS・OPS+</h3>
          <span class="text-xs text-gray-400">OPS+ = 100 × (OBP/{la['lg_obp']:.3f} + SLG/{la['lg_slg']:.3f} - 1)</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm text-gray-300 whitespace-nowrap">
            <thead class="bg-gray-950 text-xs text-gray-400 border-b border-gray-800">
              <tr>
                <th class="py-2.5 px-3 text-center">指名順</th>
                <th class="py-2.5 px-3">指名者</th>
                <th class="py-2.5 px-3">選手名</th>
                <th class="py-2.5 px-3 text-right">打席数(pt)</th>
                <th class="py-2.5 px-3 text-right">塁打＋四球</th>
                <th class="py-2.5 px-3 text-right">OPS</th>
                <th class="py-2.5 px-3 text-right">OPS+</th>
                <th class="py-2.5 px-3 text-center">12球団新人 量順位</th>
                <th class="py-2.5 px-3 text-center">12球団新人 質順位(20打席以上)</th>
                <th class="py-2.5 px-3 text-center">阪神新人内順位</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-800/60">
              {render_hitter_draft_rows()}
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- Section 3: 4-Quadrant Scatter Matrices -->
    <section class="space-y-4">
      <h2 class="text-xl font-bold flex items-center gap-2 text-yellow-400">
        <span>3. 全新人王有資格者「質 × 量」4象限ポジショニングマップ</span>
      </h2>
      <p class="text-xs text-gray-400">
        右上に行くほど「起用量が多く（量）、1軍平均を大きく上回るパフォーマンス（質）」を発揮した選手です。黄色＝阪神指名選手、水色＝阪神未指名選手、グレー＝他球団の新人王有資格者。
      </p>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Pitcher Scatter -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg">
          <div class="flex items-center justify-between mb-3">
            <h3 class="text-base font-bold text-blue-300">投手：対戦打者数（量）× K-BB+（質）</h3>
            <span class="text-[11px] text-gray-400">対象：30打者以上(72名)＋阪神全登板</span>
          </div>
          <div class="relative h-80">
            <canvas id="pitcherScatter"></canvas>
          </div>
        </div>

        <!-- Hitter Scatter -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl p-5 shadow-lg">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h3 class="text-base font-bold text-orange-300">野手：<span id="hitterXLabel">打席数</span>（量）× OPS+（質）</h3>
            <div class="inline-flex rounded-lg bg-gray-950 p-0.5 border border-gray-800 text-xs">
              <button id="btnHitterPA" onclick="switchHitterX('pa')" class="px-2.5 py-1 rounded-md bg-yellow-400 text-black font-bold transition">横軸：打席数</button>
              <button id="btnHitterTBBB" onclick="switchHitterX('tb_bb')" class="px-2.5 py-1 rounded-md text-gray-400 hover:text-white transition">横軸：塁打＋四球</button>
            </div>
          </div>
          <div class="relative h-80">
            <canvas id="hitterScatter"></canvas>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 4: Hanshin All 23 Rookie-Eligible Players -->
    <section class="space-y-4">
      <h2 class="text-xl font-bold flex items-center gap-2 text-yellow-400">
        <span>4. 阪神 新人王有資格者 全{cnt['hanshin_pitchers'] + cnt['hanshin_hitters']}名 完全序列（指名 vs 未指名「隠れMVP」検証）</span>
      </h2>
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <!-- Hanshin Pitchers -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
            <h3 class="text-sm font-bold text-blue-300">阪神 投手有資格者（全{cnt['hanshin_pitchers']}名）</h3>
            <span class="text-xs text-cyan-300">注目：神宮(K-BB+ 174.5)・石黒(106.3)が未指名</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-3 text-center">虎内</th>
                  <th class="py-2 px-3">選手名</th>
                  <th class="py-2 px-3">指名状況</th>
                  <th class="py-2 px-3 text-right">打者(pt)</th>
                  <th class="py-2 px-3 text-right">投球回</th>
                  <th class="py-2 px-3 text-right">防御率</th>
                  <th class="py-2 px-3 text-right">K-BB</th>
                  <th class="py-2 px-3 text-right">K-BB%</th>
                  <th class="py-2 px-3 text-right">K-BB+</th>
                  <th class="py-2 px-3 text-center">12球団 量/質</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60">
                {render_hanshin_pitchers()}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Hanshin Hitters -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
            <h3 class="text-sm font-bold text-orange-300">阪神 野手有資格者（全{cnt['hanshin_hitters']}名）</h3>
            <span class="text-xs text-cyan-300">注目：福島圭音（154打席 / 塁打+四球49 / OPS+77.5）が虎内1位で未指名</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-3 text-center">虎内</th>
                  <th class="py-2 px-3">選手名</th>
                  <th class="py-2 px-3">指名状況</th>
                  <th class="py-2 px-3 text-right">打席(pt)</th>
                  <th class="py-2 px-3 text-right">塁打+四球</th>
                  <th class="py-2 px-3 text-right">打率</th>
                  <th class="py-2 px-3 text-right">OPS</th>
                  <th class="py-2 px-3 text-right">OPS+</th>
                  <th class="py-2 px-3 text-center">12球団 量/質</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60">
                {render_hanshin_hitters()}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 5: 12-Team Top 15 Comparison -->
    <section class="space-y-4">
      <h2 class="text-xl font-bold flex items-center gap-2 text-yellow-400">
        <span>5. 12球団 全新人王有資格者 トップ15 ＆ 阪神指名選手の立ち位置</span>
      </h2>
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <!-- 12-team Pitchers -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
            <h3 class="text-sm font-bold text-blue-300">12球団 新人王有資格投手（対戦打者Top15＋阪神指名選手）</h3>
            <span class="text-xs text-gray-400">全{cnt['rookie_pitchers_total']}名中</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-3 text-center">打者順</th>
                  <th class="py-2 px-3">選手名</th>
                  <th class="py-2 px-3">球団</th>
                  <th class="py-2 px-3 text-right">打者</th>
                  <th class="py-2 px-3 text-right">投球回</th>
                  <th class="py-2 px-3 text-right">防御率</th>
                  <th class="py-2 px-3 text-right">K-BB</th>
                  <th class="py-2 px-3 text-right">K-BB%</th>
                  <th class="py-2 px-3 text-right">K-BB+</th>
                  <th class="py-2 px-3 text-center">質順(30BF以上)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60">
                {render_12team_pitchers()}
              </tbody>
            </table>
          </div>
        </div>

        <!-- 12-team Hitters -->
        <div class="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 bg-gray-950 border-b border-gray-800 flex justify-between items-center">
            <h3 class="text-sm font-bold text-orange-300">12球団 新人王有資格野手（打席数Top15＋阪神指名選手）</h3>
            <span class="text-xs text-gray-400">全{cnt['rookie_hitters_total']}名中</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs text-gray-300 whitespace-nowrap">
              <thead class="bg-gray-950/60 text-gray-400 border-b border-gray-800">
                <tr>
                  <th class="py-2 px-3 text-center">打席順</th>
                  <th class="py-2 px-3">選手名</th>
                  <th class="py-2 px-3">球団</th>
                  <th class="py-2 px-3 text-right">打席</th>
                  <th class="py-2 px-3 text-right">塁打+四球</th>
                  <th class="py-2 px-3 text-right">打率</th>
                  <th class="py-2 px-3 text-right">OPS</th>
                  <th class="py-2 px-3 text-right">OPS+</th>
                  <th class="py-2 px-3 text-center">質順(20PA以上)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-800/60">
                {render_12team_hitters()}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <footer class="text-center text-xs text-gray-600 py-4 border-t border-gray-800">
      出典：プロ野球データFreak（tpa-1 / ip3-1 / tpa-7 / ip3-7）1軍公式戦成績より集計
    </footer>
  </div>

  <script>
    // 1. チーム別積み上げグラフ
    const teamsData = {json.dumps([{'owner': t['owner'], 'p1': t['picks'][0]['points'], 'p2': t['picks'][1]['points'], 'n1': t['picks'][0]['name'], 'n2': t['picks'][1]['name']} for t in teams], ensure_ascii=False)};
    new Chart(document.getElementById('userChart').getContext('2d'), {{
      type: 'bar',
      data: {{
        labels: teamsData.map(t => t.owner),
        datasets: [
          {{ label: '主力指名選手', data: teamsData.map(t => t.p1), backgroundColor: '#ffe200', borderRadius: 4 }},
          {{ label: 'もう1名の指名選手', data: teamsData.map(t => t.p2), backgroundColor: '#f97316', borderRadius: 4 }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ labels: {{ color: '#d1d5db' }} }},
          tooltip: {{
            callbacks: {{
              afterLabel: (ctx) => {{
                const t = teamsData[ctx.dataIndex];
                return ctx.datasetIndex === 0 ? `${{t.n1}}: ${{t.p1}}pt` : `${{t.n2}}: ${{t.p2}}pt`;
              }}
            }}
          }}
        }},
        scales: {{
          x: {{ stacked: true, ticks: {{ color: '#d1d5db' }}, grid: {{ color: '#1f2937' }} }},
          y: {{ stacked: true, ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#1f2937' }}, title: {{ display: true, text: '合計ポイント (pt)', color: '#9ca3af' }} }}
        }}
      }}
    }});

    // 平均ライン描画プラグイン (y = 100)
    const avgLinePlugin = {{
      id: 'avgLine',
      beforeDatasetsDraw(chart) {{
        const {{ ctx, chartArea: {{ left, right }}, scales: {{ y }} }} = chart;
        if (!y) return;
        const yPos = y.getPixelForValue(100);
        if (yPos < chart.chartArea.top || yPos > chart.chartArea.bottom) return;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([6, 4]);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(52, 211, 153, 0.7)';
        ctx.moveTo(left, yPos);
        ctx.lineTo(right, yPos);
        ctx.stroke();
        ctx.fillStyle = 'rgba(52, 211, 153, 0.9)';
        ctx.font = '11px "Noto Sans JP", sans-serif';
        ctx.fillText('1軍平均 (100)', left + 6, yPos - 6);
        ctx.restore();
      }}
    }};

    // 2. 投手散布図
    const pOther = {json.dumps(scatter_p_other, ensure_ascii=False)};
    const pHanshinUndrafted = {json.dumps(scatter_p_hanshin_undrafted, ensure_ascii=False)};
    const pHanshinDrafted = {json.dumps(scatter_p_hanshin_drafted, ensure_ascii=False)};

    new Chart(document.getElementById('pitcherScatter').getContext('2d'), {{
      type: 'scatter',
      data: {{
        datasets: [
          {{
            label: '他球団新人 (30打者以上)',
            data: pOther,
            backgroundColor: 'rgba(156, 163, 175, 0.45)',
            borderColor: 'rgba(156, 163, 175, 0.7)',
            pointRadius: 5,
            pointHoverRadius: 7
          }},
          {{
            label: '阪神・未指名新人',
            data: pHanshinUndrafted,
            backgroundColor: 'rgba(34, 211, 238, 0.85)',
            borderColor: '#06b6d4',
            pointRadius: 7,
            pointHoverRadius: 9
          }},
          {{
            label: '阪神・ドラフト指名選手',
            data: pHanshinDrafted,
            backgroundColor: '#ffe200',
            borderColor: '#ffffff',
            borderWidth: 2,
            pointRadius: 9,
            pointHoverRadius: 11
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ labels: {{ color: '#d1d5db', font: {{ size: 11 }} }} }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => {{
                const d = ctx.raw;
                return [
                  `${{d.name}} (${{d.team}}) [${{d.owner}}]`,
                  `対戦打者: ${{d.x}} (${{d.bf_rank}}位) / 投球回: ${{d.ip}} / 防御率: ${{d.era}}`,
                  `K-BB+: ${{d.y}} / K-BB%: ${{d.kbb_pct}}% / K-BB実数: ${{d.k_bb}}`
                ];
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            title: {{ display: true, text: '対戦打者数（量）', color: '#9ca3af' }},
            ticks: {{ color: '#9ca3af' }},
            grid: {{ color: '#1f2937' }}
          }},
          y: {{
            title: {{ display: true, text: 'K-BB+（質：100=1軍平均）', color: '#9ca3af' }},
            ticks: {{ color: '#9ca3af' }},
            grid: {{ color: '#1f2937' }}
          }}
        }}
      }},
      plugins: [avgLinePlugin]
    }});

    // 3. 野手散布図（横軸切替対応）
    const hOtherRaw = {json.dumps(scatter_h_other, ensure_ascii=False)};
    const hHanshinUndraftedRaw = {json.dumps(scatter_h_hanshin_undrafted, ensure_ascii=False)};
    const hHanshinDraftedRaw = {json.dumps(scatter_h_hanshin_drafted, ensure_ascii=False)};

    function mapHitterPoints(arr, xKey) {{
      return arr.map(d => ({{ ...d, x: d[xKey] }}));
    }}

    const hitterChart = new Chart(document.getElementById('hitterScatter').getContext('2d'), {{
      type: 'scatter',
      data: {{
        datasets: [
          {{
            label: '他球団新人 (20打席以上)',
            data: mapHitterPoints(hOtherRaw, 'pa'),
            backgroundColor: 'rgba(156, 163, 175, 0.45)',
            borderColor: 'rgba(156, 163, 175, 0.7)',
            pointRadius: 5,
            pointHoverRadius: 7
          }},
          {{
            label: '阪神・未指名新人',
            data: mapHitterPoints(hHanshinUndraftedRaw, 'pa'),
            backgroundColor: 'rgba(34, 211, 238, 0.85)',
            borderColor: '#06b6d4',
            pointRadius: 7,
            pointHoverRadius: 9
          }},
          {{
            label: '阪神・ドラフト指名選手',
            data: mapHitterPoints(hHanshinDraftedRaw, 'pa'),
            backgroundColor: '#ffe200',
            borderColor: '#ffffff',
            borderWidth: 2,
            pointRadius: 9,
            pointHoverRadius: 11
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ labels: {{ color: '#d1d5db', font: {{ size: 11 }} }} }},
          tooltip: {{
            callbacks: {{
              label: (ctx) => {{
                const d = ctx.raw;
                return [
                  `${{d.name}} (${{d.team}}) [${{d.owner}}]`,
                  `打席数: ${{d.pa}} (${{d.pa_rank}}位) / 塁打+四球: ${{d.tb_bb}} (${{d.tb}}+${{d.bb}})`,
                  `OPS+: ${{d.y}} / OPS: ${{d.ops?.toFixed(3)}} / 打率: ${{d.avg}}`
                ];
              }}
            }}
          }}
        }},
        scales: {{
          x: {{
            title: {{ display: true, text: '打席数（量）', color: '#9ca3af' }},
            ticks: {{ color: '#9ca3af' }},
            grid: {{ color: '#1f2937' }}
          }},
          y: {{
            title: {{ display: true, text: 'OPS+（質：100=1軍平均）', color: '#9ca3af' }},
            ticks: {{ color: '#9ca3af' }},
            grid: {{ color: '#1f2937' }}
          }}
        }}
      }},
      plugins: [avgLinePlugin]
    }});

    function switchHitterX(mode) {{
      hitterChart.data.datasets[0].data = mapHitterPoints(hOtherRaw, mode);
      hitterChart.data.datasets[1].data = mapHitterPoints(hHanshinUndraftedRaw, mode);
      hitterChart.data.datasets[2].data = mapHitterPoints(hHanshinDraftedRaw, mode);
      const labelTxt = mode === 'pa' ? '打席数' : '塁打＋四球';
      document.getElementById('hitterXLabel').textContent = labelTxt;
      hitterChart.options.scales.x.title.text = `${{labelTxt}}（量）`;
      hitterChart.update();

      const btnPA = document.getElementById('btnHitterPA');
      const btnTBBB = document.getElementById('btnHitterTBBB');
      if (mode === 'pa') {{
        btnPA.className = 'px-2.5 py-1 rounded-md bg-yellow-400 text-black font-bold transition';
        btnTBBB.className = 'px-2.5 py-1 rounded-md text-gray-400 hover:text-white transition';
      }} else {{
        btnTBBB.className = 'px-2.5 py-1 rounded-md bg-yellow-400 text-black font-bold transition';
        btnPA.className = 'px-2.5 py-1 rounded-md text-gray-400 hover:text-white transition';
      }}
    }}
  </script>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

if __name__ == '__main__':
    main()
