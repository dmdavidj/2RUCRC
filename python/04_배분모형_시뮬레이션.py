# -*- coding: utf-8 -*-
"""
[04] 성과인센티브 4,000억 원 배분모형 설계 및 시뮬레이션

■ 배경(원문 근거)
  - 앵커 추진방안(교육부, 2026.4.2): 약 4,000억 원을 성과평가 인센티브로 활용,
    '25년 사업 평가로 '26년 예산 차등지원. 평가항목은 ①예산 나눠먹기 ②소통 ③학생·인재 고려.
    → 현행 지표에는 '청년이 실제로 지역에 남았는가'를 재는 결과지표가 없다.
  - 2026년 고등교육 재정지원계획(교육부, 2026.2): 시·도별 RISE 추진 1조 5,618.35억 중
    '성과평가 환류 4,000억' 명시.

■ 모형 설계 (지표 교체형)
  현행 시·도 배분 골대는 유지하되, 차등의 '기준'만 교체한다.
  단, 배분 총액은 4,000억으로 고정하고 시·도별 몫만 재계산한다.

  [현행 가정] 시·도 기준 순유입(전입-전출)이 클수록 '정주 성과'로 보상
             → 광역시가 도(道)에서 청년을 흡수하는 것도 성과로 계상됨(제로섬)

  [제안 지표] '권역 정주 기여도 지수(RCI: Regional Contribution Index)'
     RCI_i = w1·(권역 순유지율) + w2·(권역 정주 개선도)
       · 권역 순유지율   = 권역경계를 넘는 순이동 / 연앙인구  (권역 내부 이동은 분자에서 중립화)
       · 권역 정주 개선도 = 최근 3년 권역기준 전출률의 개선(감소) 폭
     → 권역 내부의 제로섬 이동은 성과에서 빠지므로 '뺏어먹기'가 보상되지 않는다.

  [3특 보정] 강원·전북·제주는 권역=시도라 '권역 내부 이동' 개념이 없다.
     이들에게는 권역 순유지율을 그대로 적용하되, 광역시-도 간 흡수효과가 없어
     구조적으로 불리하지 않도록 동일 지표(인구정규화 순유지율)로 공정 비교된다.

원자료: 데이터/가공/정주율지표_시도별_25-29세.csv (03단계 산출물)
        모든 수치는 KOSIS 원자료에서 산출된 값이며 임의 생성분 없음.
"""
import os, sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
pd.set_option('display.width', 260)
pd.set_option('display.unicode.east_asian_width', True)

BASE = r"c:\Users\admin\Downloads\지역대학연구"
OUT = os.path.join(BASE, "데이터", "가공")

TOTAL = 4000.0  # 억원 (성과평가 환류 총액)

t = pd.read_csv(os.path.join(OUT, "정주율지표_시도별_25-29세.csv"))

# 최근 3년(2023~2025) 평균으로 지표 안정화
def window(df, y0, y1):
    return df[(df.year >= y0) & (df.year <= y1)]

# ── 지표 재료: 시도별 인구·순이동(시도기준/권역기준) 3년 평균 ──
w = window(t, 2023, 2025).groupby(['시도', '권역']).agg(
    pop=('pop', 'mean'),
    시도순=('시도기준_순이동', 'mean'),
    권역순=('권역기준_순이동', 'mean'),
    권역전출=('권역기준_전출', 'mean'),
).reset_index()

# ── 개선도: (2015~2017 평균 권역전출률) - (2023~2025 평균 권역전출률), + 이면 개선 ──
base = window(t, 2015, 2017).groupby('시도').apply(
    lambda x: (x['권역기준_전출'].sum() / x['pop'].sum() * 1000), include_groups=False
).rename('권역전출률_기준')
recent = window(t, 2023, 2025).groupby('시도').apply(
    lambda x: (x['권역기준_전출'].sum() / x['pop'].sum() * 1000), include_groups=False
).rename('권역전출률_최근')
imp = pd.concat([base, recent], axis=1).reset_index()
imp['정주개선도'] = imp['권역전출률_기준'] - imp['권역전출률_최근']  # +면 전출률 감소=개선
w = w.merge(imp[['시도', '정주개선도']], on='시도', how='left')

# ── 지표 정규화 (min-max, 0~1) : '상대 성과'를 성과배분 몫으로 환산 ──
def mm(s):
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else s * 0 + 0.5

w['권역순유지율'] = w['권역순'] / w['pop'] * 1000   # 인구정규화
w['z_순유지'] = mm(w['권역순유지율'])
w['z_개선'] = mm(w['정주개선도'])

W1, W2 = 0.7, 0.3
w['RCI'] = W1 * w['z_순유지'] + W2 * w['z_개선']            # 제안 성과지수(0~1)

# ── 현행(가정) 지표: 시도기준 순유입의 인구정규화 ──
w['현행지표_시도순유입률'] = w['시도순'] / w['pop'] * 1000
w['z_현행'] = mm(w['현행지표_시도순유입률'])                 # 현행 성과지수(0~1)

# ── 배분구조: 기본배분(청년인구 비례) + 성과배분(성과지수 비례) ──
#    실제 국고보조 인센티브가 '기준수요 + 성과'로 구성되는 점을 반영.
#    ALPHA = 기본배분 비중. 두 시나리오(현행/제안)에 동일 구조를 적용하여
#    '지표 교체' 효과만 분리한다.
ALPHA = 0.5
w['인구비중'] = w['pop'] / w['pop'].sum()

def allocate(score_col):
    perf_share = w[score_col] / w[score_col].sum()
    return TOTAL * (ALPHA * w['인구비중'] + (1 - ALPHA) * perf_share)

w['배분_현행'] = allocate('z_현행')
w['배분_제안'] = allocate('RCI')
w['증감'] = w['배분_제안'] - w['배분_현행']
w['증감률(%)'] = w['증감'] / w['배분_현행'] * 100

w = w.sort_values('증감', ascending=False)

show = w[['권역', '시도', 'pop', '현행지표_시도순유입률', '권역순유지율', '정주개선도',
          'RCI', '배분_현행', '배분_제안', '증감', '증감률(%)']].copy()
show.columns = ['권역', '시도', '연앙인구', '현행지표(‰)', '권역순유지율(‰)', '정주개선도(‰p)',
                'RCI지수', '현행배분(억)', '제안배분(억)', '증감(억)', '증감률(%)']

print("=" * 130)
print("[표] 성과인센티브 4,000억 재배분 — 현행(시도 순유입) vs 제안(권역 정주기여 RCI), 25-29세, 2023~2025 평균")
print("=" * 130)
print(show.round(2).to_string(index=False))

print("\n검증: 배분 합계  현행 =", round(w['배분_현행'].sum(), 1), " / 제안 =", round(w['배분_제안'].sum(), 1))

# ── 권역별 요약 ──
print("\n" + "=" * 90)
print("[표] 권역별 배분 변화 요약")
print("=" * 90)
reg = w.groupby('권역').agg(시도수=('시도', 'count'),
                          현행배분=('배분_현행', 'sum'),
                          제안배분=('배분_제안', 'sum')).reset_index()
reg['증감'] = reg['제안배분'] - reg['현행배분']
reg = reg.sort_values('증감', ascending=False)
print(reg.round(1).to_string(index=False))

# ── 대구·경북권 상세 (발표용) ──
print("\n" + "=" * 90)
print("[사례] 대구·경북권: 지표를 바꾸면 대구와 경북의 몫이 어떻게 달라지는가")
print("=" * 90)
dk = show[show['권역'] == '대구·경북권']
print(dk.round(2).to_string(index=False))

show.to_csv(os.path.join(OUT, "배분시뮬레이션_결과.csv"), index=False, encoding='utf-8-sig')
reg.to_csv(os.path.join(OUT, "배분시뮬레이션_권역요약.csv"), index=False, encoding='utf-8-sig')

# ── 민감도 분석: 기본배분비중 ALPHA, 지표가중 W1을 흔들어 결론 안정성 확인 ──
print("\n" + "=" * 90)
print("[민감도] 파라미터를 바꿔도 '대구 감액·경북 증액' 방향이 유지되는가")
print("=" * 90)
sens = []
for a in [0.3, 0.5, 0.7]:
    for w1 in [0.5, 0.7, 0.9]:
        rci = w1 * w['z_순유지'] + (1 - w1) * w['z_개선']
        perf = rci / rci.sum()
        cur = w['z_현행'] / w['z_현행'].sum()
        alloc_p = TOTAL * (a * w['인구비중'] + (1 - a) * perf)
        alloc_c = TOTAL * (a * w['인구비중'] + (1 - a) * cur)
        d = (alloc_p - alloc_c)
        d.index = w['시도'].values
        sens.append({'ALPHA': a, 'W1': w1,
                     '대구_증감': round(d['대구'], 1), '경북_증감': round(d['경북'], 1),
                     '세종_증감': round(d['세종'], 1), '전남_증감': round(d['전남'], 1)})
sens = pd.DataFrame(sens)
print(sens.to_string(index=False))
sens.to_csv(os.path.join(OUT, "배분시뮬레이션_민감도.csv"), index=False, encoding='utf-8-sig')

print("\n산출물: 배분시뮬레이션_결과.csv / _권역요약.csv / _민감도.csv")
