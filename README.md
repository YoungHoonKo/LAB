# AI-Based Emotional Relief Package Optimization

<div align="center">

### LLM-Based Emotional Index Analysis for Personalized Relief Kits

**재난·질병·응급 상황에서 대학생의 심리적 안정을 지원하기 위한  
LLM 기반 감성지수 분석 및 맞춤형 물품 패키지 추천 시스템**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LLM](https://img.shields.io/badge/LLM-GPT%20%7C%20Gemini%20%7C%20Qwen-green)
![Status](https://img.shields.io/badge/Status-In%20Progress-orange)
![Research](https://img.shields.io/badge/Research-Human%20Centered%20AI-red)

</div>

---

## Overview

본 프로젝트는 **재난·질병·응급 상황에서 불안, 우울, 공포, 스트레스 등 부정적 감정으로 학업과 일상에 어려움을 겪는 대학생을 지원하기 위한 AI 기반 심리 안정 물품 추천 시스템** 연구입니다.

기존 재난 지원 체계가 식량, 의약품, 생필품과 같은 **물리적 지원 중심**이었다면, 본 연구는 **심리적 안정(Emotional Stability)** 또한 응급 상황에서 중요한 요소라는 문제의식에서 출발합니다.

본 연구는 **거대언어모델(LLM, Large Language Model)** 을 활용하여 물품 사용 후 기대되는 정신적·심리적 효과를 분석하고, 이를 **감성지수(Emotional Index)** 로 정량화하여 사용자 맞춤형 물품 패키지를 추천합니다.

---

## Why This Research?

대학생들은 재난, 질병, 시험 기간, 심리적 위기 상황에서 높은 수준의 스트레스와 불안을 경험할 수 있습니다.

그러나 현재 대부분의 지원은:

- 물리적 건강 중심
- 일률적인 지원 체계
- 개인 감정 상태 반영 부족

이라는 한계를 가지고 있습니다.

본 연구는 다음 질문에서 시작되었습니다.

> **“사람마다 심리적으로 도움이 되는 물품이 다르다면, AI가 개인에게 맞는 안정 키트를 추천할 수 있을까?”**

---

## Research Goal

본 연구의 핵심 목적은 다음과 같습니다.

1. **LLM 기반 물품 감성 효과 분석**
2. **감성지수(Emotional Index) 정량화**
3. **사용자 맞춤형 심리 안정 키트 추천**
4. **실제 대학생 대상 실험 검증**
5. **재난 지원 및 감성 추천 시스템 확장 가능성 탐색**

---

## Core Concept

### Emotional Index

감성지수란 사용자가 특정 물품을 사용한 후 경험하는 **정신적·심리적 효과를 정량화한 지표**입니다.

예를 들어:

| Item | Expected Effect | Emotional Factor |
|:---:|:---:|:---:|
| Stress Ball | 긴장 완화 | 불안 감소, 스트레스 완화 |
| Aroma Oil | 감각 안정 | 심리 안정, 이완감 |
| Herbal Tea | 진정 효과 | 편안함, 수면 보조 |
| Positive Message Card | 정서적 지지 | 위로, 희망감 |
| Coloring Kit | 표현 활동 | 몰입, 감정 해소 |

본 연구는 이러한 효과를 **텍스트 데이터 + LLM 분석**을 통해 수치화합니다.

---

## System Architecture

```text
Naver Blog / Review Data
              ↓
      Web Crawling
              ↓
      Text Preprocessing
              ↓
   LLM Sentiment Analysis
              ↓
 Emotional Index Generation
              ↓
 Personalized Kit Recommendation
              ↓
      User Evaluation
              ↓
     Model Validation
```

---

## Research Pipeline

### 1. Product Candidate Extraction

네이버 블로그 리뷰 데이터를 크롤링하여 **심리 안정에 도움을 준다고 언급된 제품 후보군**을 추출합니다.

예시:

- 아로마 오일
- 스트레스볼
- 허브티
- 긍정 카드
- 루틴 체크 카드
- 초콜릿

블로그 후기 예시:

> “시험기간에 스트레스 완화에 도움이 되었다.”  
> “향을 맡으면 마음이 차분해졌다.”

---

### 2. LLM-Based Sentiment Analysis

수집된 리뷰 데이터를 기반으로 LLM이 감성 효과를 분석합니다.

분석 항목:

- 감정 분류(Label)
- 심리적 효과 추론
- 감성 근거 문장 추출
- 신뢰도 점수 계산
- 감성지수 생성

Example Output:

```json
{
  "item": "aroma_oil",
  "label": "psychological_stability",
  "reason": "사용자가 긴장 완화와 안정감을 반복적으로 언급함",
  "confidence": 0.91
}
```

---

### 3. Personalized Package Recommendation

사용자의 현재 감정 상태를 기반으로 최적의 물품 패키지를 추천합니다.

Example:

```text
Input:
"시험 스트레스가 너무 심해요"

Recommended Package:
✔ Stress Ball
✔ Chamomile Tea
✔ Aroma Oil
✔ Positive Message Card
✔ Routine Check Card
```

---

### 4. Real-World Validation

추천 시스템의 타당성을 검증하기 위해 실제 대학생 대상 실험을 진행합니다.

#### Experimental Procedure

1. 참여자 감정 상태 사전 조사
2. 맞춤형 물품 패키지 제작
3. 대학생 20~30명 대상 배포
4. 사용 후 설문조사
5. 실제 감성 효과 평가
6. LLM 예측 결과와 비교 검증

---

## Current Progress

### Completed

- [x] 프로젝트 기획
- [x] 사이트 구조 설계
- [x] 제품군 정의
- [x] 네이버 블로그 크롤링
- [x] 브랜드 후보군 추출
- [x] 감성 분석 구조 설계

### In Progress

- [ ] 사이트 개발
- [ ] 키트 제작
- [ ] 대학생 대상 배포
- [ ] 설문조사 진행
- [ ] 감성지수 검증
- [ ] 포스터 제작

---

## Timeline

| Week | Task |
|---|---|
| 1주차 (4/29 ~ 5/6) | 사이트 디자인 / 브랜드 추출 |
| 2주차 (5/6 ~ 5/13) | 프로토타입 제작 / 제품 주문 |
| 3주차 (5/13 ~ 5/20) | 설문조사 설계 |
| 4주차 (5/20 ~ 5/27) | 키트 배포 |
| 5주차 (5/27 ~ 6/3) | 감성 분석 및 모델 개선 |
| 6주차 (6/3 ~ 6/10) | 기말고사 시즌 |
| 7주차 (6/10 ~ 6/17) | 결과 분석 |
| 8주차 (6/17 ~ 6/24) | 발표 및 포스터 제작 |

---

## Evaluation Metrics

| Metric | Description |
|:---:|:---:|
| User Satisfaction | 추천 만족도 |
| Emotional Relief Score | 심리 안정 효과 |
| Prediction Accuracy | AI 예측 정확도 |
| Package Suitability | 추천 적합성 |
| Practicality | 실제 적용 가능성 |

---

## Tech Stack

### AI / Data Analysis

- Python
- Pandas
- NumPy
- Scikit-learn
- LLM API
- NLP
- Sentiment Analysis

### Data Collection

- Naver Blog Search API
- Web Crawling
- BeautifulSoup

### Environment

- Jupyter Notebook
- GitHub
- macOS

---

## Project Structure

```text
project-root/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── survey/
│
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_sentiment_analysis.ipynb
│   ├── 03_emotional_index.ipynb
│   └── 04_package_recommendation.ipynb
│
├── src/
│   ├── crawler.py
│   ├── sentiment_analyzer.py
│   ├── emotional_index.py
│   └── recommender.py
│
├── results/
│   ├── figures/
│   ├── reports/
│   └── evaluation/
│
└── README.md
```

---

## Research Significance

### AI-Based Emotional Support

LLM 기반 자연어 처리 기술을 활용하여 심리 안정 지원에 적용합니다.

### Personalized Humanitarian Aid

사용자별 맞춤형 심리 안정 키트를 제공합니다.

### Preventive Mental Care

고스트레스군 사용자의 심리 악화를 예방할 수 있습니다.

### Industrial Scalability

향후 다음 분야로 확장 가능합니다.

- Mental Wellness
- Emotional Commerce
- Recommendation Systems
- Disaster Relief Technology

---

## Future Work

- 임베딩 기반 추천 시스템 적용
- 실시간 감정 분석
- 멀티모달 감정 분석
- 사용자군 확장
- 재난 상황별 동적 키트 최적화

---

## Researchers

**고영훈 (Younghoon Ko)**  
Undergraduate Research Assistant  
Department of Software Convergence

**김현진**  
Undergraduate Research Assistant  
Department of Software Convergence

---

## Vision

> **Technology should not only support survival, but also protect emotional stability.**

AI 기술을 통해 재난·질병·응급 상황에서 인간의 심리적 안정과 존엄을 지원하는 것을 목표로 합니다.
