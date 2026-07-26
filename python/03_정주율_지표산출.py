# -*- coding: utf-8 -*-
"""
[03] 인구 대비 청년 이동률(정주율) 지표 산출

분모 : 주민등록연앙인구 (KOSIS DT_1B040M5 / DT_1B040M5_1, 시도·5세연령별)
분자 : 시도간 이동자수 (KOSIS DT_1B26003)

※ 두 통계표의 행정구역 코드 체계가 서로 달라(인구표 26=울산, 이동표 26=부산)
   코드가 아닌 '시도 명칭'을 기준으로 결합한다.

핵심 논점
  같은 청년 집단을 두고 '시·도'라는 자로 재느냐 '5극3특 권역'이라는 자로 재느냐에 따라
  유출 규모가 얼마나 달라지는가.
"""
import json, os, sys, io
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
pd.set_option('display.width', 250)
pd.set_option('display.unicode.east_asian_width', True)

BASE = r"c:\Users\admin\Downloads\지역대학연구"
RAW = os.path.join(BASE, "데이터", "원자료")
OUT = os.path.join(BASE, "데이터", "가공")

# 인구표 코드 → 표준 약칭
POP_CODE = {'11': '서울', '21': '부산', '22': '대구', '23': '인천', '24': '광주',
            '25': '대전', '26': '울산', '29': '세종', '31': '경기', '32': '강원',
            '33': '충북', '34': '충남', '35': '전북', '36': '전남', '37': '경북',
            '38': '경남', '39': '제주'}
REGION = {'서울': '수도권', '인천': '수도권', '경기': '수도권',
          '대전': '충청권', '세종': '충청권', '충북': '충청권', '충남': '충청권',
          '광주': '광주·전남권', '전남': '광주·전남권',
          '대구': '대구·경북권', '경북': '대구·경북권',
          '부산': '부산·울산·경남권', '울산': '부산·울산·경남권', '경남': '부산·울산·경남권',
          '강원': '강원특별자치도', '전북': '전북특별자치도', '제주': '제주특별자치도'}

# ── 인구 적재 ──
prow = []
for y in range(2015, 2026):
    for r in json.load(open(os.path.join(RAW, f"KOSIS_연앙인구_시도_{y}.json"), encoding='utf-8')):
        if r['C1'] == '00':
            continue
        prow.append({'year': y, '시도': POP_CODE[r['C1']], 'age': r['C3'],
                     'pop': pd.to_numeric(r['DT'], errors='coerce')})
pop = pd.DataFrame(prow)
assert pop['시도'].nunique() == 17, "시도 수 오류"
print(f"연앙인구 적재: {len(pop):,}행, 시도 {pop['시도'].nunique()}개")

# ── 이동 적재 ──
m = pd.read_parquet(os.path.join(OUT, "이동_시도격자.parquet"))
m = m[~m.is_within_sido]

AGE = '130'; AGE_LABEL = '25-29세'
mm = m[m.age == AGE]
pp = pop[pop.age == AGE][['year', '시도', 'pop']]

# ── 시도 기준 ──
sido_out = mm.groupby(['year', 'orig_nm']).n.sum().rename('시도기준_전출')
sido_in = mm.groupby(['year', 'dest_nm']).n.sum().rename('시도기준_전입')
# ── 권역 기준 (권역 경계를 넘는 이동만) ──
cr = mm[mm.is_cross_region]
reg_out = cr.groupby(['year', 'orig_nm']).n.sum().rename('권역기준_전출')
reg_in = cr.groupby(['year', 'dest_nm']).n.sum().rename('권역기준_전입')

t = pd.concat([sido_out, sido_in, reg_out, reg_in], axis=1).fillna(0).reset_index()
t.columns = ['year', '시도'] + list(t.columns[2:])
t = t.merge(pp, on=['year', '시도'], how='left')
t['권역'] = t['시도'].map(REGION)
assert t['pop'].notna().all(), "인구 결합 실패"

t['시도기준_순이동'] = t['시도기준_전입'] - t['시도기준_전출']
t['권역기준_순이동'] = t['권역기준_전입'] - t['권역기준_전출']
for c in ['시도기준_전출', '권역기준_전출', '시도기준_순이동', '권역기준_순이동']:
    t[c + '률(‰)'] = t[c] / t['pop'] * 1000

t.to_csv(os.path.join(OUT, f"정주율지표_시도별_{AGE_LABEL}.csv"), index=False, encoding='utf-8-sig')

# ─────────────────────────────────────────
print("\n" + "=" * 110)
print(f"[표] 2025년 시·도별 청년({AGE_LABEL}) 유출 — 자(尺)를 바꾸면 얼마나 달라지는가")
print("=" * 110)
y25 = t[t.year == 2025].copy()
y25['과대계상분'] = y25['시도기준_전출'] - y25['권역기준_전출']
y25['과대계상률(%)'] = (y25['과대계상분'] / y25['시도기준_전출'] * 100)
show = y25[['권역', '시도', 'pop', '시도기준_전출', '권역기준_전출', '과대계상분', '과대계상률(%)',
            '시도기준_전출률(‰)', '권역기준_전출률(‰)']].sort_values(['권역', '과대계상률(%)'], ascending=[True, False])
show.columns = ['권역', '시도', '연앙인구', '시도기준전출', '권역기준전출', '과대계상', '과대계상률(%)',
                '시도기준전출률(‰)', '권역기준전출률(‰)']
print(show.round(1).to_string(index=False))

# ─────────────────────────────────────────
print("\n" + "=" * 110)
print(f"[표] 권역 단위 집계 — 2025년 ({AGE_LABEL})")
print("=" * 110)
g = y25.groupby('권역').agg(
    연앙인구=('pop', 'sum'),
    시도기준전출합=('시도기준_전출', 'sum'),
    권역기준전출=('권역기준_전출', 'sum'),
    시도기준순이동합=('시도기준_순이동', 'sum'),
    권역기준순이동=('권역기준_순이동', 'sum'),
).reset_index()
g['과대계상'] = g['시도기준전출합'] - g['권역기준전출']
g['과대계상률(%)'] = g['과대계상'] / g['시도기준전출합'] * 100
g['시도기준전출률(‰)'] = g['시도기준전출합'] / g['연앙인구'] * 1000
g['권역기준전출률(‰)'] = g['권역기준전출'] / g['연앙인구'] * 1000
g = g.sort_values('과대계상률(%)', ascending=False)
print(g.round(1).to_string(index=False))
g.to_csv(os.path.join(OUT, "권역단위_유출률비교_2025.csv"), index=False, encoding='utf-8-sig')

# ─────────────────────────────────────────
print("\n" + "=" * 110)
print(f"[표] 전국 추세: 시·도 기준 청년 전출 중 권역 내부 이동 비중 ({AGE_LABEL})")
print("=" * 110)
tr = t.groupby('year').agg(시도기준전출=('시도기준_전출', 'sum'),
                           권역기준전출=('권역기준_전출', 'sum'),
                           연앙인구=('pop', 'sum')).reset_index()
tr['권역내이동'] = tr['시도기준전출'] - tr['권역기준전출']
tr['과대계상률(%)'] = tr['권역내이동'] / tr['시도기준전출'] * 100
tr['시도기준전출률(‰)'] = tr['시도기준전출'] / tr['연앙인구'] * 1000
tr['권역기준전출률(‰)'] = tr['권역기준전출'] / tr['연앙인구'] * 1000
print(tr.round(1).to_string(index=False))
tr.to_csv(os.path.join(OUT, "전국추세_유출률비교.csv"), index=False, encoding='utf-8-sig')

print("\n산출물: 데이터/가공/ 에 저장 완료")
