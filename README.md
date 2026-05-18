# AI-Based Emotional Relief Package Optimization

> 재난·질병·응급 상황에서 대학생의 심리적 안정을 지원하기 위한  
> **LLM 기반 감성지수 분석 및 맞춤형 물품 패키지 추천 시스템**

---

## 1. Project Overview

본 프로젝트는 재난·질병·응급 상황에서 불안, 우울, 공포, 스트레스 등 부정적 감정으로 학업과 일상에 어려움을 겪는 대학생을 지원하기 위해 기획된 연구입니다.

기존의 재난 지원 체계가 식량, 의약품, 생필품 등 물리적 지원에 집중했다면, 본 연구는 위기 상황에서 개인의 **심리적 안정** 또한 중요한 지원 요소라고 보고, 사용자의 감정 상태에 맞는 물품 패키지를 추천하는 AI 시스템을 설계합니다.

본 연구는 거대언어모델(LLM, Large Language Model)을 활용하여 물품 사용 후 기대되는 정신적·심리적 효과를 분석하고, 이를 **감성지수(Emotional Index)** 로 정량화하여 사용자 맞춤형 물품 패키지를 구성하는 것을 목표로 합니다.

---

## 2. Research Purpose

본 연구의 핵심 목적은 다음과 같습니다.

1. 재난·질병·응급 상황에서 대학생의 심리적 안정을 지원하는 물품 패키지 구성
2. LLM을 활용한 물품별 감성 효과 분석
3. 사용자 상황에 따른 맞춤형 패키지 추천 시스템 설계
4. 실제 사용자 평가를 통한 감성지수 분석 결과 검증
5. 향후 재난 지원, 심리 안정 서비스, 마케팅 분야로의 확장 가능성 탐색

---

## 3. Core Concept

### Emotional Index

감성지수란 사용자가 특정 물품을 사용한 후 느끼는 정신적·심리적 효과를 정량화한 지표입니다.

예를 들어, 스트레스볼은 긴장 완화와 불안 감소 효과를 가질 수 있고, 허브티는 안정감과 수면 보조 효과를 제공할 수 있습니다. 본 연구는 이러한 감성 효과를 텍스트 데이터와 LLM 분석을 통해 수치화합니다.

|         Item          | Expected Effect |     Emotional Factor     |
| :-------------------: | :-------------: | :----------------------: |
|      Stress Ball      |    긴장 완화    | 불안 감소, 스트레스 완화 |
|       Aroma Oil       |    감각 안정    |    심리 안정, 이완감     |
|      Herbal Tea       |    진정 효과    |    편안함, 수면 보조     |
| Positive Message Card |   정서적 지지   |       위로, 희망감       |
|     Coloring Kit      |    표현 활동    |     몰입, 감정 해소      |

---

## 4. Research Pipeline

```text
User / Review Data Collection
        ↓
Text Preprocessing
        ↓
LLM-Based Sentiment Analysis
        ↓
Emotional Index Calculation
        ↓
Personalized Package Recommendation
        ↓
User Evaluation
        ↓
Comparison & Validation
```

---

## 5. Methodology

### 5.1 Data Collection

물품별 사용자 경험과 감성 반응을 분석하기 위해 온라인 리뷰, 블로그 텍스트, 사용자 평가 데이터를 수집합니다.

수집 대상 물품 예시는 다음과 같습니다.

- 스트레스볼
- 긍정 메시지 카드
- 아로마 오일
- 허브티
- 루틴 체크 카드
- 색칠하기 키트
- 핫팩
- 위로 메시지 카드

---

### 5.2 LLM-Based Sentiment Analysis

수집된 텍스트를 LLM을 활용하여 분석합니다.

분석 항목은 다음과 같습니다.

- 감정 분류
- 심리적 효과 추론
- 감성 근거 문장 추출
- 신뢰도 점수 산출
- 물품별 감성지수 계산

예시 출력 구조는 다음과 같습니다.

```json
{
  "item": "aroma_oil",
  "label": "psychological_stability",
  "reason": "사용자가 긴장 완화와 안정감을 반복적으로 언급함",
  "evidence": [
    "향을 맡으면 마음이 차분해진다",
    "시험 기간 스트레스 완화에 도움이 되었다"
  ],
  "confidence": 0.91
}
```

---

### 5.3 Package Recommendation

사용자의 감정 상태와 물품별 감성지수를 바탕으로 최적의 물품 조합을 추천합니다.

예시:

```text
User Type: 시험 스트레스가 높은 대학생

Recommended Package:
- Stress Ball
- Chamomile Tea
- Positive Message Card
- Aroma Oil
- Routine Check Card
```

---

## 6. Experiment Design

본 연구는 실제 일반 대학생 30명을 대상으로 물품 패키지를 제공한 후, 제품별 감성 효과를 평가합니다.

실험 절차는 다음과 같습니다.

1. 참여자 감정 상태 사전 조사
2. 맞춤형 물품 패키지 제공
3. 물품 사용 후 감성 효과 평가
4. LLM 기반 감성지수 결과와 사용자 평가 비교
5. 머신러닝 기반 분석 및 검증

---

## 7. Evaluation Metrics

본 연구에서는 다음 지표를 활용하여 시스템의 효과를 평가합니다.

|         Metric         |            Description             |
| :--------------------: | :--------------------------------: |
|   User Satisfaction    |  추천 패키지에 대한 사용자 만족도  |
| Emotional Relief Score |       사용 후 심리 안정 효과       |
|  Prediction Accuracy   | LLM 감성지수와 실제 평가 간 일치도 |
|  Package Suitability   |  사용자 상황과 추천 물품의 적합성  |
|      Practicality      |  실제 재난·응급 상황 적용 가능성   |

---

## 8. Tech Stack

### AI / Data Analysis

- Python
- Pandas
- NumPy
- Scikit-learn
- LLM API
- Natural Language Processing
- Sentiment Analysis

### Data Collection

- Naver Blog Search API
- Web Crawling
- BeautifulSoup
- CSV Dataset

### Development Environment

- Jupyter Notebook
- macOS
- GitHub

---

## 9. Project Structure

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

## 10. Research Significance

본 연구의 의의는 다음과 같습니다.

### 1. AI-Based Emotional Support

LLM 기반 자연어 처리 기술을 활용하여 물품의 감성 효과를 분석하고, 심리적 안정 지원에 적용합니다.

### 2. Personalized Relief Package

사용자의 감정 상태와 상황에 따라 맞춤형 물품 패키지를 구성함으로써 응급 상황에서 신속한 의사결정을 지원합니다.

### 3. Preventive Mental Care

고스트레스군 사용자의 심리적 악화를 예방하고, 정서적 안정에 도움을 줄 수 있는 보조적 지원 체계를 제안합니다.

### 4. Industrial Scalability

본 연구의 방법론은 재난 지원뿐 아니라 웰니스 서비스, 개인화 추천 시스템, 마케팅, 감성 커머스 분야로 확장될 수 있습니다.

---

## 11. Future Work

향후 연구 방향은 다음과 같습니다.

- 사용자 감정 상태 기반 실시간 추천 시스템 개발
- 물품별 감성지수 데이터베이스 구축
- 대학생 외 다양한 사용자군으로 실험 대상 확장
- 재난 상황별 패키지 최적화 알고리즘 고도화
- 텍스트, 설문, 생체신호를 결합한 멀티모달 감정 분석 적용

---

## 12. Researcher

**Younghoon Ko**  
Undergraduate Research Assistant  
Human-Centered AI Research  
Department of Software Convergence

### Research Interests

- Human-Centered AI
- Natural Language Processing
- Sentiment Analysis
- Recommendation Systems
- Disaster Relief Technology
- Data Science

---

## 13. Vision

> Technology should not only support survival, but also protect emotional stability.

본 프로젝트는 AI 기술을 통해 재난·질병·응급 상황에서 인간의 심리적 안정과 존엄을 지원하는 것을 목표로 합니다.
