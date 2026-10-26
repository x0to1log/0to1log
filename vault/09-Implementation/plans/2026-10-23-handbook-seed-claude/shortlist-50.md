# Handbook seed shortlist — 상위 50 (A 방식 사전 표시)

> 기준: 거름망 accept + 뉴스 등장 편수 순. 기존 핸드북 용어(published/draft/archived)와 겹치거나, 표 안에서 같은 개념이거나,
> 버전 붙은 모델명·일반 IT 용어·틈새 제품은 x. 바꾸고 싶은 칸만 o↔x로 고쳐 주세요. 원본 표: [[candidates]]
> `W` = warmup 30개 (승인 순서대로 앞 30개)

- 승인 **50** / 제외 17 (순위 1~67 검토)
- 카테고리 편중: math-statistics가 0개 — 뉴스 등장이 적은 분야라 필요하면 시드 목록(2번 표)에서 보충

| 순위 | ok | W | term | category | 편수 | 이유 |
|---|---|---|---|---|---|---|
| 1 | o | W | Open-Weight Model | llm-genai | 49 | 49편, 우리 뉴스 최다 등장. 기존 open-source LLM과 구분되는 개념(가중치 공개 ≠ 오픈소스) |
| 2 | o | W | Red Teaming | safety-ethics | 17 | 17편. #25 AI Red Teaming을 흡수. 시범에서 Opus 거절(cyber) → Sonnet 또는 sol 대체 |
| 3 | o | W | Vision-Language-Action Model | llm-genai | 15 | 15편, 로보틱스 기사 핵심 용어 |
| 4 | o | W | Sandboxing | safety-ethics | 15 | 15편. 에이전트 실행 격리 개념. #57 Sandbox 흡수 |
| 5 | o | W | Multi-Token Prediction | llm-genai | 13 | 13편, 최근 모델 발표에 반복 등장 |
| 6 | o | W | Mamba (SSM) | deep-learning | 13 | 13편. 용어명은 'State Space Model (Mamba)'로 생성 권장 (모델명보다 계열 개념이 오래감) |
| 7 | o | W | World Model | deep-learning | 12 | 12편 |
| 8 | x |  | Data Center | infra-hardware | 12 | 기존 draft 'AI datacentre'와 중복 (철자 차이로 거름망 통과) |
| 9 | o | W | Embodied AI | llm-genai | 12 | 12편 |
| 10 | o | W | Foundation Model | llm-genai | 10 | 10편. 기존 Frontier Model(draft)과 다른 개념 |
| 11 | o | W | Flow Matching | deep-learning | 9 | 9편, 생성 모델 핵심 기법 |
| 12 | o | W | AI Accelerator | infra-hardware | 9 | 9편. GPU·NPU를 묶는 상위 개념 |
| 13 | o | W | Digital Watermarking | safety-ethics | 9 | 9편. #38 C2PA와 함께 콘텐츠 출처 묶음 |
| 14 | o | W | Formal Verification | cs-fundamentals | 8 | 8편 |
| 15 | o | W | Human-in-the-Loop | llm-genai | 8 | 8편 |
| 16 | o | W | SGLang | products-platforms | 7 | 7편, 서빙 프레임워크 (vLLM 옆자리). 시범 용어 |
| 17 | o | W | Reward Shaping | ml-fundamentals | 7 | 7편 |
| 18 | o | W | Tokenization | llm-genai | 7 | 7편. 기존 Token과 다른 '과정' 개념. #22 Tokenizer 흡수 |
| 19 | o | W | Text-to-Speech | deep-learning | 7 | 7편 |
| 20 | x |  | Agent Orchestration | llm-genai | 7 | 기존 multi-agent system·Agentic workflows와 대부분 겹침 |
| 21 | o | W | Speech Recognition | deep-learning | 7 | 7편. #42 Automatic Speech Recognition 흡수 (별칭 ASR) |
| 22 | x |  | Tokenizer | llm-genai | 7 | #18 Tokenization에 포함 |
| 23 | o | W | Access Control | safety-ethics | 6 | 6편. 에이전트 권한 문맥에서 자주 등장 |
| 24 | x |  | API | cs-fundamentals | 6 | 너무 일반적 (AI 핸드북 범위 밖) |
| 25 | x |  | AI Red Teaming | safety-ethics | 6 | #2 Red Teaming에 포함 |
| 26 | o | W | Linear Attention | deep-learning | 6 | 6편 |
| 27 | o | W | AI Gateway | infra-hardware | 6 | 6편 |
| 28 | o | W | Knowledge Graph | data-engineering | 6 | 6편 |
| 29 | o | W | Catastrophic Forgetting | ml-fundamentals | 6 | 6편 |
| 30 | o | W | Self-Distillation | deep-learning | 6 | 6편. 기존 Model Distillation과 다른 세부 기법 |
| 31 | o | W | Diffusion Language Model | llm-genai | 6 | 6편 |
| 32 | o | W | Word Error Rate | ml-fundamentals | 6 | 6편, 음성 모델 평가 지표 |
| 33 | x |  | Cloud Computing | infra-hardware | 5 | 일반 IT 용어 (AI 핸드북 범위 밖) |
| 34 | o | W | Credit Assignment | ml-fundamentals | 5 | 5편, 강화학습 기초 |
| 35 | x |  | Benchmark | ml-fundamentals | 5 | 기존 Evals와 겹침 |
| 36 | x |  | Multimodal Learning | deep-learning | 5 | 기존 Multimodal Model과 겹침 |
| 37 | o | W | Reward Hacking | safety-ethics | 5 | 5편 |
| 38 | o | W | C2PA | safety-ethics | 5 | 5편. #13과 묶음 |
| 39 | o |  | Continual Learning | ml-fundamentals | 5 | 5편 |
| 40 | o |  | Kubernetes | infra-hardware | 5 | 5편, 시드 목록에도 있음 (ML 서빙 인프라) |
| 41 | o |  | Application-Specific Integrated Circuit | infra-hardware | 5 | 5편. 용어명은 'ASIC'(별칭 Application-Specific Integrated Circuit) 권장 |
| 42 | x |  | Automatic Speech Recognition | deep-learning | 5 | #21 Speech Recognition에 포함 |
| 43 | o |  | Information Retrieval | cs-fundamentals | 5 | 5편. 기존 BM25·Vector Search·RAG의 상위 개념 |
| 44 | o |  | Diffusion Transformer | deep-learning | 5 | 5편 |
| 45 | x |  | Computer-Use Agent | llm-genai | 5 | 기존 Computer Use와 겹침 |
| 46 | o |  | GRPO | llm-genai | 5 | 5편, 추론 모델 학습 기법 |
| 47 | o |  | AI Governance | safety-ethics | 5 | 5편 |
| 48 | o |  | Visual Question Answering | deep-learning | 5 | 5편 |
| 49 | x |  | LocalAI | products-platforms | 5 | 틈새 제품, 오래 남을 항목 아님 |
| 50 | o |  | Optical Character Recognition | deep-learning | 5 | 5편 |
| 51 | x |  | Multi-Cloud Computing | infra-hardware | 5 | 일반 IT 용어 |
| 52 | o |  | Pass@k | ml-fundamentals | 4 | 4편, 코드 생성 평가 지표 |
| 53 | x |  | Cosign | products-platforms | 4 | 틈새 도구 |
| 54 | o |  | LiteLLM | products-platforms | 4 | 4편, 시드 목록에도 있음 |
| 55 | x |  | Local Inference | infra-hardware | 4 | 기존 on-device AI·edge deployment와 겹침 |
| 56 | o |  | High-Bandwidth Memory | infra-hardware | 4 | 4편. 용어명은 'HBM'(별칭 High-Bandwidth Memory) 권장 |
| 57 | x |  | Sandbox | cs-fundamentals | 4 | #4 Sandboxing에 포함 |
| 58 | o |  | Text-to-Video Generation | deep-learning | 4 | 4편 |
| 59 | o |  | Point Cloud | deep-learning | 4 | 4편 |
| 60 | o |  | NCCL | products-platforms | 4 | 4편, 분산 학습 통신 라이브러리 |
| 61 | o |  | LLM-as-a-Judge | llm-genai | 4 | 4편. 기존 Evals와 구분되는 평가 방식 |
| 62 | x |  | Virtual Machine | infra-hardware | 4 | 일반 IT 용어 |
| 63 | o |  | Test-Time Adaptation | ml-fundamentals | 4 | 4편. 기존 Test-Time Compute와 다른 개념 |
| 64 | o |  | On-Policy Distillation | llm-genai | 4 | 4편 |
| 65 | o |  | Out-of-Distribution Generalization | ml-fundamentals | 4 | 4편 |
| 66 | x |  | Vulnerability Scanning | safety-ethics | 4 | 일반 보안 도구 (Supply-chain attack 등 기존 항목으로 충분) |
| 67 | o |  | Zero-Shot Learning | ml-fundamentals | 4 | 4편 |
