# 웹페이지 (GitHub Pages) 배포 안내

이 폴더(`docs/`)에는 연구를 한눈에 보여주는 **모바일 최적화 단일 페이지**가 들어 있습니다.

- `index.html` — 페이지 본체 (자체 완결형, 외부 리소스는 Google Fonts만 사용)
- `.nojekyll` — GitHub Pages가 파일을 그대로 서빙하도록 하는 표시 파일

## GitHub Pages로 올리는 법

### 방법 A) 저장소 설정에서 /docs 지정 (가장 쉬움)
1. 이 프로젝트를 GitHub 저장소로 push
   ```
   git init
   git add .
   git commit -m "지역대학 동반성장 연구 웹페이지"
   git branch -M main
   git remote add origin https://github.com/<사용자명>/<저장소명>.git
   git push -u origin main
   ```
2. GitHub 저장소 → **Settings → Pages**
3. **Source: Deploy from a branch** 선택
4. **Branch: main / 폴더: /docs** 선택 후 Save
5. 1~2분 뒤 `https://<사용자명>.github.io/<저장소명>/` 에서 공개됨

### 방법 B) docs 내용을 저장소 루트로 올리기
`index.html`을 저장소 최상위에 두고, Settings → Pages에서 Branch: main / 폴더: **/(root)** 선택.

### 방법 C) index.html만 별도 저장소로
`index.html` 한 파일만 새 저장소에 올려도 됩니다(자체 완결형).

## 특징
- **모바일 최적화**: 세로 스크롤형 내러티브, 반응형 레이아웃
- **라이트/다크 테마**: 시스템 설정 자동 감지 + 우상단 ◐ 버튼으로 전환
- **근거 기반**: 모든 수치는 통계청 원자료 산출값, 하단에 전체 출처 명기
- **웹폰트**: Noto Serif KR(제목)·Noto Sans KR(본문) — 인터넷 연결 시 자동 로드, 실패해도 시스템 폰트로 표시

## 수정하려면
`index.html` 상단 `<style>`에서 색상(`--blue`, `--red` 등)이나 폰트를, 하단 `<script>`의 `DATA` 객체에서 수치를 바꾸면 됩니다. 단, **수치는 검증된 원자료 산출값**이므로 임의로 바꾸지 마세요.
