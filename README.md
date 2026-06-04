# ISMS-P 증적 자동 점검 도구

ISMS-P(정보보호 및 개인정보보호 관리체계) 인증 준비 시 제출해야 하는 증적 파일을 자동으로 분석하고, 각 항목의 적합 여부를 판단해주는 도구입니다.

## 주요 기능

- **증적 파일 업로드** — PDF, DOCX, XLSX 형식 지원
- **자동 적합 판단** — 코사인 유사도 기반 가이드라인 부합도 계산 + GPT LLM 최종 판정
- **판정 결과 제공** — 적합 / 부분 적합 / 부적합 3단계 판정 및 상세 근거
- **보완 권고사항** — 부적합·부분 적합 항목에 대한 구체적인 보완 가이드
- **점검 내역 관리** — 이전 점검 결과 히스토리 저장 및 조회
- **PDF 보고서 출력** — 전체 결과 보고서 PDF 다운로드

## 기술 스택

| 구분 | 기술 |
|------|------|
| Front-end | React, Vite, Electron |
| Back-end | FastAPI, Uvicorn |
| 파싱 | Docling (PDF·DOCX·PPTX), openpyxl (XLSX), PyMuPDF |
| 청킹 | Docling HybridChunker |
| 임베딩 모델 | BGE-M3 (BAAI/bge-m3) |
| 유사도 계산 | Cosine Similarity (NumPy) |
| 데이터베이스 | Supabase (PostgreSQL, pgvector) |
| 판단 모델 | GPT-4o-mini (OpenAI API) |

## 프로젝트 구조

```
KISIA/
├── frontend/          # React + Vite + Electron 앱
│   └── src/
│       ├── pages/     # 페이지 컴포넌트
│       ├── components/
│       ├── api/
│       └── utils/
├── backend/           # FastAPI 서버
│   ├── routers/       # API 라우터 (upload, analyze)
│   ├── services/      # 핵심 서비스 (llm, similarity, db)
│   └── user_upload/   # 파싱·청킹·임베딩 모듈
│       ├── parshing/
│       ├── chunking/
│       ├── embedding/
│       └── db/
└── README.md
```

## 실행 방법

### 백엔드

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 데스크톱 앱 (Electron)

```bash
cd frontend
npm run electron:dev
```

## 환경 변수 설정

`backend/.env` 파일을 생성하고 아래 값을 설정하세요.

```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
SUPABASE_ANON_KEY=your_anon_key
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

## 판정 기준

| 판정 | 기준 |
|------|------|
| ✅ 적합 | 가이드라인 부합도 75% 이상 |
| ⚠️ 부분 적합 | 60% 이상 ~ 75% 미만 |
| ❌ 부적합 | 60% 미만 |

※ 최종 판정은 유사도 점수를 참고하여 LLM이 증적 내용을 직접 검토 후 결정합니다.
