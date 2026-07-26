# -*- coding: utf-8 -*-
"""
[01] 원자료 검증 및 5극3특 권역 재집계

원자료 : 데이터/원자료/KOSIS_DT_1B26003_YYYY.json
         통계청,「국내인구이동통계」, 전출지/전입지(시도)/성/연령(5세)별 이동자수
         (성별=계, 연령=전체, 2015~2025년, KOSIS 공유서비스 OpenAPI로 수집)

이 스크립트는 원자료를 가공만 하며, 어떤 수치도 임의로 생성하지 않는다.
"""
import json, os, sys, io
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
pd.set_option('display.width', 200)
pd.set_option('display.unicode.east_asian_width', True)

BASE = r"c:\Users\admin\Downloads\지역대학연구"
RAW = os.path.join(BASE, "데이터", "원자료")
OUT = os.path.join(BASE, "데이터", "가공")
os.makedirs(OUT, exist_ok=True)

# ─────────────────────────────────────────────
# 5극3특 권역 구분
#   출처: 김상태(2025.11.21), "'5극3특', 초광역 협력 기반의 새로운 균형성장 전략",
#         대한민국 정책브리핑.
#         "수도권, 충청권, 광주·전남권, 대구·경북권, 부산·울산·경남권의 5대 초광역권과
#          제주, 강원, 전북의 3대 특별자치도"
# ─────────────────────────────────────────────
REGION = {
    '11': '수도권',        # 서울특별시
    '28': '수도권',        # 인천광역시
    '41': '수도권',        # 경기도
    '30': '충청권',        # 대전광역시
    '36': '충청권',        # 세종특별자치시
    '43': '충청권',        # 충청북도
    '44': '충청권',        # 충청남도
    '29': '광주·전남권',   # 광주광역시
    '46': '광주·전남권',   # 전라남도
    '27': '대구·경북권',   # 대구광역시
    '47': '대구·경북권',   # 경상북도
    '26': '부산·울산·경남권',  # 부산광역시
    '31': '부산·울산·경남권',  # 울산광역시
    '48': '부산·울산·경남권',  # 경상남도
    '51': '강원특별자치도',
    '52': '전북특별자치도',
    '50': '제주특별자치도',
}
SIDO_NM = {
    '11': '서울', '26': '부산', '27': '대구', '28': '인천', '29': '광주',
    '30': '대전', '31': '울산', '36': '세종', '41': '경기', '43': '충북',
    '44': '충남', '46': '전남', '47': '경북', '48': '경남', '50': '제주',
    '51': '강원', '52': '전북',
}
AGE_NM = {'000': '계', '120': '20-24세', '130': '25-29세', '150': '30-34세'}

# ─────────────────────────────────────────────
# 1. 적재
# ─────────────────────────────────────────────
rows = []
for y in range(2015, 2026):
    fp = os.path.join(RAW, f"KOSIS_DT_1B26003_{y}.json")
    with open(fp, encoding='utf-8') as f:
        for r in json.load(f):
            rows.append({
                'year': int(r['PRD_DE']),
                'orig': r['C1'], 'dest': r['C2'],
                'age': r['C4'],
                'n': pd.to_numeric(r.get('DT'), errors='coerce'),
            })
df = pd.DataFrame(rows)
print(f"적재: {len(df):,}행  / 연도 {df.year.min()}~{df.year.max()}")
print(f"결측(DT) : {df.n.isna().sum():,}건")

# ─────────────────────────────────────────────
# 2. 정합성 검증 — 전국(00) 합계와 시도 합계 일치 여부
#    C1='00'(전출지 전국) & C2='00'(전입지 전국) = 총이동자수
# ─────────────────────────────────────────────
print("\n" + "=" * 72)
print("[검증] 원자료 내적 정합성")
print("=" * 72)
chk = []
for y in sorted(df.year.unique()):
    d = df[(df.year == y) & (df.age == '000')]
    total_reported = d[(d.orig == '00') & (d.dest == '00')].n.sum()
    # 시도×시도 (전국 제외) 합 = 시도내이동 + 시도간이동 = 총이동
    grid = d[(d.orig != '00') & (d.dest != '00')].n.sum()
    chk.append({'연도': y, '전국계(보고값)': total_reported, '시도격자합': grid,
                '차이': total_reported - grid})
chk = pd.DataFrame(chk)
print(chk.to_string(index=False))
assert (chk['차이'].abs() < 1).all(), "정합성 불일치 — 원자료 재확인 필요"
print("→ 전국 보고값과 시도 격자 합계가 일치한다. 원자료 정합성 확인.")

# ─────────────────────────────────────────────
# 3. 시도간 이동만 추출 (전국행 제외, 시도내 이동 제외)
# ─────────────────────────────────────────────
m = df[(df.orig != '00') & (df.dest != '00')].copy()
m['orig_nm'] = m.orig.map(SIDO_NM)
m['dest_nm'] = m.dest.map(SIDO_NM)
m['orig_reg'] = m.orig.map(REGION)
m['dest_reg'] = m.dest.map(REGION)
m['is_within_sido'] = m.orig == m.dest
m['is_within_region'] = (~m.is_within_sido) & (m.orig_reg == m.dest_reg)
m['is_cross_region'] = m.orig_reg != m.dest_reg

assert m.orig_reg.notna().all() and m.dest_reg.notna().all(), "권역 매핑 누락"
print(f"\n시도 격자 레코드: {len(m):,}행 (17×17×연령18×연도11 = {17*17*18*11:,})")

m.to_parquet(os.path.join(OUT, "이동_시도격자.parquet"), index=False)

# ─────────────────────────────────────────────
# 4. 핵심 지표 ①
#    시·도 경계 기준 '역외 유출'로 집계되는 이동 중,
#    5극3특 권역 기준으로는 '권역 내 이동'인 비중
# ─────────────────────────────────────────────
print("\n" + "=" * 72)
print("[핵심지표 ①] 시·도 기준 역외유출 중 권역 내부 이동이 차지하는 비중")
print("=" * 72)

def share_within_region(age_code):
    d = m[(m.age == age_code) & (~m.is_within_sido)]
    g = d.groupby('year').apply(
        lambda x: pd.Series({
            '시도간총이동': x.n.sum(),
            '권역내이동': x.loc[x.is_within_region, 'n'].sum(),
            '권역간이동': x.loc[x.is_cross_region, 'n'].sum(),
        }), include_groups=False)
    g['권역내비중(%)'] = g['권역내이동'] / g['시도간총이동'] * 100
    return g

for code in ['120', '130', '150', '000']:
    g = share_within_region(code)
    print(f"\n── 연령 {AGE_NM[code]} ──")
    print(g.round(1).to_string())

# ─────────────────────────────────────────────
# 5. 핵심 지표 ②
#    권역 내부에서 각 시·도의 순이동 (= '권역 내 인재 이동' 구조)
# ─────────────────────────────────────────────
print("\n" + "=" * 72)
print("[핵심지표 ②] 권역 '내부' 이동만 놓고 본 시·도별 순이동 (25-29세)")
print("=" * 72)

d = m[(m.age == '130') & (m.is_within_region)]
inflow = d.groupby(['year', 'dest_nm']).n.sum().rename('권역내전입')
outflow = d.groupby(['year', 'orig_nm']).n.sum().rename('권역내전출')
net = pd.concat([inflow, outflow], axis=1).fillna(0)
net['권역내순이동'] = net['권역내전입'] - net['권역내전출']
net.index.names = ['연도', '시도']
net = net.reset_index()
net['권역'] = net['시도'].map({v: REGION[k] for k, v in SIDO_NM.items()})

recent = net[net.연도 == 2025].sort_values('권역내순이동', ascending=False)
print("\n[2025년] 권역 내부 이동 기준 시·도별 순이동 (25-29세)")
print(recent[['권역', '시도', '권역내전입', '권역내전출', '권역내순이동']].to_string(index=False))

net.to_csv(os.path.join(OUT, "권역내_순이동_시도별.csv"), index=False, encoding='utf-8-sig')

# ─────────────────────────────────────────────
# 6. 핵심 지표 ③
#    시·도 단위 순이동 vs 권역 단위 순이동 (같은 사람, 다른 자[尺])
# ─────────────────────────────────────────────
print("\n" + "=" * 72)
print("[핵심지표 ③] 같은 해, 같은 사람 — 자를 바꾸면 결과가 달라지는가 (25-29세, 2025년)")
print("=" * 72)

d = m[(m.age == '130') & (~m.is_within_sido)]

# 시도 기준
sido_in = d.groupby('dest_nm').n.sum()
sido_out = d.groupby('orig_nm').n.sum()
sido_net = (sido_in - sido_out).rename('시도기준_순이동')

# 권역 기준 (권역 경계를 넘는 이동만)
dc = d[d.is_cross_region]
reg_in = dc.groupby('dest_reg').n.sum()
reg_out = dc.groupby('orig_reg').n.sum()
reg_net = (reg_in - reg_out).rename('권역기준_순이동')

cmp = pd.DataFrame({'시도': list(SIDO_NM.values())})
cmp['권역'] = cmp['시도'].map({v: REGION[k] for k, v in SIDO_NM.items()})
cmp = cmp.merge(sido_net.rename_axis('시도').reset_index(), on='시도', how='left')
cmp = cmp.merge(reg_net.rename_axis('권역').reset_index(), on='권역', how='left')
cmp = cmp.sort_values(['권역', '시도'])
print(cmp.to_string(index=False))

cmp.to_csv(os.path.join(OUT, "시도vs권역_순이동비교_2025.csv"), index=False, encoding='utf-8-sig')

print("\n" + "=" * 72)
print("산출물 저장 완료:")
print("  데이터/가공/이동_시도격자.parquet")
print("  데이터/가공/권역내_순이동_시도별.csv")
print("  데이터/가공/시도vs권역_순이동비교_2025.csv")
print("=" * 72)
