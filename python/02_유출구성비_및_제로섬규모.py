# -*- coding: utf-8 -*-
"""
[02] 시·도별 청년 전출의 행선지 구성 + 권역 내 제로섬 이동 규모

핵심 논점
  (A) 시·도 기준으로 '역외 유출'로 집계되는 청년 이동 중 권역 내부 이동의 비중
  (B) 각 시·도를 떠난 청년이 어디로 갔는가 — 권역 내 / 권역 밖
  (C) 권역 내부 이동은 정의상 권역 전체 순증이 0이다(제로섬).
      시·도 단위 성과평가는 이 제로섬 이동을 '성과'로 계상한다. 그 규모를 측정한다.

원자료: 통계청,「국내인구이동통계」DT_1B26003 (2015~2025, 성별 계)
"""
import os, sys, io
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
pd.set_option('display.width', 250)
pd.set_option('display.unicode.east_asian_width', True)

BASE = r"c:\Users\admin\Downloads\지역대학연구"
OUT = os.path.join(BASE, "데이터", "가공")

m = pd.read_parquet(os.path.join(OUT, "이동_시도격자.parquet"))
AGE = '130'          # 25-29세
AGE_LABEL = '25-29세'

d = m[(m.age == AGE) & (~m.is_within_sido)].copy()

# ─────────────────────────────────────────────
# (B) 시·도별 전출 행선지 구성 — 2025년
# ─────────────────────────────────────────────
print("=" * 88)
print(f"[B] 시·도별 청년({AGE_LABEL}) 전출자의 행선지 구성 — 2025년")
print("=" * 88)

y = 2025
dy = d[d.year == y]
g = dy.groupby(['orig_nm', 'orig_reg']).apply(
    lambda x: pd.Series({
        '총전출': x.n.sum(),
        '권역내로': x.loc[x.is_within_region, 'n'].sum(),
        '권역밖으로': x.loc[x.is_cross_region, 'n'].sum(),
    }), include_groups=False).reset_index()
g['권역내비중(%)'] = (g['권역내로'] / g['총전출'] * 100).round(1)
g = g.rename(columns={'orig_nm': '시도', 'orig_reg': '권역'})
g = g.sort_values(['권역', '권역내비중(%)'], ascending=[True, False])
print(g.to_string(index=False))
g.to_csv(os.path.join(OUT, f"시도별_전출행선지구성_{y}.csv"), index=False, encoding='utf-8-sig')

# ─────────────────────────────────────────────
# (C) 권역 내 제로섬 이동 규모 — 연도별
#     권역 내부 총이동량 = 시·도 단위 평가에서는 '전입 성과'로 잡히지만
#     권역 전체로는 순증이 0인 이동
# ─────────────────────────────────────────────
print("\n" + "=" * 88)
print(f"[C] 권역 내부 이동 규모 — 시·도 단위 평가가 '성과'로 계상하나 권역 순증은 0 ({AGE_LABEL})")
print("=" * 88)

z = d.groupby(['year', 'orig_reg']).apply(
    lambda x: pd.Series({'권역내이동': x.loc[x.is_within_region, 'n'].sum()}),
    include_groups=False).reset_index()
z = z.rename(columns={'orig_reg': '권역', 'year': '연도'})
piv = z.pivot(index='연도', columns='권역', values='권역내이동').fillna(0).astype(int)
piv['합계'] = piv.sum(axis=1)
print(piv.to_string())
piv.to_csv(os.path.join(OUT, "권역내_이동규모_연도별.csv"), encoding='utf-8-sig')

# ─────────────────────────────────────────────
# (C-2) 권역별 내부이동 대 권역외유출 — 2025년
# ─────────────────────────────────────────────
print("\n" + "=" * 88)
print(f"[C-2] 권역별: 내부 재배치 vs 권역 밖 순유출 — 2025년 ({AGE_LABEL})")
print("=" * 88)

rows = []
for reg in sorted(d.orig_reg.unique()):
    dr = dy[(dy.orig_reg == reg)]
    within = dr.loc[dr.is_within_region, 'n'].sum()
    out = dr.loc[dr.is_cross_region, 'n'].sum()
    inn = dy.loc[(dy.dest_reg == reg) & (dy.is_cross_region), 'n'].sum()
    n_sido = d[d.orig_reg == reg].orig_nm.nunique()
    rows.append({'권역': reg, '구성시도수': n_sido,
                 '권역내부이동': int(within),
                 '권역밖전출': int(out), '권역밖전입': int(inn),
                 '권역순이동': int(inn - out)})
c2 = pd.DataFrame(rows).sort_values('권역내부이동', ascending=False)
c2['내부이동/권역밖전출(%)'] = (c2['권역내부이동'] / c2['권역밖전출'] * 100).round(1)
print(c2.to_string(index=False))
c2.to_csv(os.path.join(OUT, f"권역별_내부이동대외부유출_{y}.csv"), index=False, encoding='utf-8-sig')

# ─────────────────────────────────────────────
# (D) 대구·경북권 상세 — 발표용 사례
# ─────────────────────────────────────────────
print("\n" + "=" * 88)
print(f"[D] 대구·경북권 내부 흐름 상세 ({AGE_LABEL})")
print("=" * 88)
dk = d[(d.orig_reg == '대구·경북권') & (d.dest_reg == '대구·경북권')]
flow = dk.groupby(['year', 'orig_nm', 'dest_nm']).n.sum().reset_index()
fp = flow.pivot_table(index='year', columns=['orig_nm', 'dest_nm'], values='n').astype(int)
print(fp.to_string())
fp.to_csv(os.path.join(OUT, "대경권_내부흐름.csv"), encoding='utf-8-sig')

print("\n[해석용] 2025년 경북 전출자의 행선지 상위 5개")
gb = dy[dy.orig_nm == '경북'].nlargest(5, 'n')[['dest_nm', 'dest_reg', 'n']]
gb['비중(%)'] = (gb.n / dy[dy.orig_nm == '경북'].n.sum() * 100).round(1)
print(gb.to_string(index=False))
