# Handbook seed candidates — review table

> 생성: `backend/scripts/mine_handbook_candidates.py` · 뉴스 370편 · 계획 [[2026-10-23-handbook-seed-claude]]
> 표시 열 `ok`에 승인(o) / 제외(x)를 적어 주세요. 비워 두면 미검토.

- 후보(남은 것): **1475** — 뉴스 2편 이상 283, 뉴스 1편 636, 기존 시드 목록만 556
- 제외: 이미 핸드북에 있음 107, 범위 밖 0, 형태 필터 52

## 1. 뉴스에 2편 이상 나온 용어 (우선)

`비슷` = 이 표 안에서 같은 개념일 수 있는 후보의 # (하나만 승인하거나 합치기).

| # | ok | term | 한국어 | category | 편수 | 최근 | source | gate | 비슷 |
|---|---|---|---|---|---|---|---|---|---|
| 1 |  | Open-Weight Model | 가중치 공개 모델 | llm-genai | 49 | 2026-10-21 | news+seed | accept | #164 |
| 2 |  | Red Teaming | 레드팀 테스트 | safety-ethics | 17 | 2026-09-20 | news+seed | accept | #25 |
| 3 |  | Vision-Language-Action Model | 시각-언어-행동 모델 | llm-genai | 15 | 2026-10-19 | news+seed | accept |  |
| 4 |  | Sandboxing | 샌드박싱 | safety-ethics | 15 | 2026-10-16 | news | accept | #57 |
| 5 |  | Multi-Token Prediction | 다중 토큰 예측 | llm-genai | 13 | 2026-10-22 | news | accept |  |
| 6 |  | Mamba (SSM) | 맘바 상태 공간 모델 | deep-learning | 13 | 2026-08-13 | news | accept |  |
| 7 |  | World Model | 세계 모델 | deep-learning | 12 | 2026-10-23 | news | accept |  |
| 8 |  | Data Center | 데이터 센터 | infra-hardware | 12 | 2026-10-12 | news | accept |  |
| 9 |  | Embodied AI | 체화 인공지능 | llm-genai | 12 | 2026-09-20 | news | accept |  |
| 10 |  | Foundation Model | 파운데이션 모델 | llm-genai | 10 | 2026-10-22 | news+seed | accept | #232 |
| 11 |  | Flow Matching | 플로 매칭 | deep-learning | 9 | 2026-10-19 | news+seed | accept |  |
| 12 |  | AI Accelerator | AI 가속기 | infra-hardware | 9 | 2026-10-12 | news | accept |  |
| 13 |  | Digital Watermarking | 디지털 워터마킹 | safety-ethics | 9 | 2026-09-25 | news | accept | #157 |
| 14 |  | Formal Verification | 형식 검증 | cs-fundamentals | 8 | 2026-10-20 | news | accept |  |
| 15 |  | Human-in-the-Loop | 인간 참여형 | llm-genai | 8 | 2026-09-12 | news+seed | accept |  |
| 16 |  | SGLang | SGLang | products-platforms | 7 | 2026-10-20 | news+seed | accept |  |
| 17 |  | Reward Shaping | 보상 형성 | ml-fundamentals | 7 | 2026-10-15 | news | accept |  |
| 18 |  | Tokenization | 토큰화 | llm-genai | 7 | 2026-10-14 | news | accept | #22 |
| 19 |  | Text-to-Speech | 음성 합성 | deep-learning | 7 | 2026-09-24 | news | accept |  |
| 20 |  | Agent Orchestration | 에이전트 오케스트레이션 | llm-genai | 7 | 2026-09-11 | news+seed | accept | #224, #275 |
| 21 |  | Speech Recognition | 음성 인식 | deep-learning | 7 | 2026-08-22 | news | accept | #42 |
| 22 |  | Tokenizer | 토크나이저 | llm-genai | 7 | 2026-08-20 | news | accept | #18 |
| 23 |  | Access Control | 접근 제어 | safety-ethics | 6 | 2026-10-24 | news | accept |  |
| 24 |  | API | 응용 프로그래밍 인터페이스 | cs-fundamentals | 6 | 2026-10-21 | news | accept | #210 |
| 25 |  | AI Red Teaming | AI 레드팀 테스트 | safety-ethics | 6 | 2026-10-17 | news | accept | #2 |
| 26 |  | Linear Attention | 선형 어텐션 | deep-learning | 6 | 2026-10-16 | news | accept |  |
| 27 |  | AI Gateway | AI 게이트웨이 | infra-hardware | 6 | 2026-10-15 | news | accept |  |
| 28 |  | Knowledge Graph | 지식 그래프 | data-engineering | 6 | 2026-09-19 | news | accept |  |
| 29 |  | Catastrophic Forgetting | 파국적 망각 | ml-fundamentals | 6 | 2026-09-10 | news | accept |  |
| 30 |  | Self-Distillation | 자기 증류 | deep-learning | 6 | 2026-08-15 | news | accept |  |
| 31 |  | Diffusion Language Model | 확산 언어 모델 | llm-genai | 6 | 2026-05-22 | news | accept |  |
| 32 |  | Word Error Rate | 단어 오류율 | ml-fundamentals | 6 | 2026-04-13 | news | accept |  |
| 33 |  | Cloud Computing | 클라우드 컴퓨팅 | infra-hardware | 5 | 2026-10-22 | news | accept | #51, #89 |
| 34 |  | Credit Assignment | 공로 할당 | ml-fundamentals | 5 | 2026-10-22 | news | accept |  |
| 35 |  | Benchmark | 벤치마크 | ml-fundamentals | 5 | 2026-10-21 | news | accept | #276 |
| 36 |  | Multimodal Learning | 다중 모달 학습 | deep-learning | 5 | 2026-10-21 | news | accept | #248 |
| 37 |  | Reward Hacking | 보상 해킹 | safety-ethics | 5 | 2026-10-18 | news+seed | accept |  |
| 38 |  | C2PA | C2PA | safety-ethics | 5 | 2026-09-24 | news+seed | accept |  |
| 39 |  | Continual Learning | 연속 학습 | ml-fundamentals | 5 | 2026-09-23 | news | accept |  |
| 40 |  | Kubernetes | 쿠버네티스 | infra-hardware | 5 | 2026-08-22 | news+seed | accept |  |
| 41 |  | Application-Specific Integrated Circuit | 주문형 반도체 | infra-hardware | 5 | 2026-08-09 | news | accept |  |
| 42 |  | Automatic Speech Recognition | 자동 음성 인식 | deep-learning | 5 | 2026-07-30 | news | accept | #21 |
| 43 |  | Information Retrieval | 정보 검색 | cs-fundamentals | 5 | 2026-07-30 | news | accept |  |
| 44 |  | Diffusion Transformer | 확산 트랜스포머 | deep-learning | 5 | 2026-07-29 | news+seed | accept |  |
| 45 |  | Computer-Use Agent | 컴퓨터 사용 에이전트 | llm-genai | 5 | 2026-07-27 | news | accept | #275 |
| 46 |  | GRPO | GRPO | llm-genai | 5 | 2026-07-22 | news | accept |  |
| 47 |  | AI Governance | AI 거버넌스 | safety-ethics | 5 | 2026-07-20 | news+seed | accept |  |
| 48 |  | Visual Question Answering | 시각 질의응답 | deep-learning | 5 | 2026-07-14 | news | accept |  |
| 49 |  | LocalAI | LocalAI | products-platforms | 5 | 2026-07-03 | news | accept |  |
| 50 |  | Optical Character Recognition | 광학 문자 인식 | deep-learning | 5 | 2026-06-21 | news | accept |  |
| 51 |  | Multi-Cloud Computing | 멀티클라우드 컴퓨팅 | infra-hardware | 5 | 2026-05-04 | news | accept | #33, #154 |
| 52 |  | Pass@k | Pass@k | ml-fundamentals | 4 | 2026-10-24 | news | accept |  |
| 53 |  | Cosign |  | products-platforms | 4 | 2026-10-15 | news | accept |  |
| 54 |  | LiteLLM | LiteLLM | products-platforms | 4 | 2026-10-15 | news+seed | accept |  |
| 55 |  | Local Inference | 로컬 추론 | infra-hardware | 4 | 2026-10-15 | news | accept |  |
| 56 |  | High-Bandwidth Memory | 고대역폭 메모리 | infra-hardware | 4 | 2026-10-12 | news+seed | accept |  |
| 57 |  | Sandbox | 샌드박스 | cs-fundamentals | 4 | 2026-09-27 | news | accept | #4 |
| 58 |  | Text-to-Video Generation | 텍스트-비디오 생성 | deep-learning | 4 | 2026-09-25 | news | accept | #183 |
| 59 |  | Point Cloud | 점군 | deep-learning | 4 | 2026-09-21 | news | accept |  |
| 60 |  | NCCL | NCCL | products-platforms | 4 | 2026-09-20 | news+seed | accept |  |
| 61 |  | LLM-as-a-Judge | LLM 평가자 | llm-genai | 4 | 2026-09-19 | news+seed | accept |  |
| 62 |  | Virtual Machine | 가상 머신 | infra-hardware | 4 | 2026-09-12 | news | accept |  |
| 63 |  | Test-Time Adaptation | 테스트 시점 적응 | ml-fundamentals | 4 | 2026-08-08 | news | accept |  |
| 64 |  | On-Policy Distillation | 온폴리시 증류 | llm-genai | 4 | 2026-07-27 | news | accept |  |
| 65 |  | Out-of-Distribution Generalization | 분포 외 일반화 | ml-fundamentals | 4 | 2026-07-24 | news | accept |  |
| 66 |  | Vulnerability Scanning | 취약점 스캐닝 | safety-ethics | 4 | 2026-07-18 | news | accept |  |
| 67 |  | Zero-Shot Learning | 제로샷 학습 | ml-fundamentals | 4 | 2026-07-14 | news | accept |  |
| 68 |  | Deepfake | 딥페이크 | safety-ethics | 4 | 2026-07-13 | news+seed | accept |  |
| 69 |  | Browser Automation | 브라우저 자동화 | cs-fundamentals | 4 | 2026-07-11 | news | accept |  |
| 70 |  | Self-Supervised Learning | 자기 지도 학습 | ml-fundamentals | 4 | 2026-07-10 | news+seed | accept |  |
| 71 |  | Computer Vision | 컴퓨터 비전 | deep-learning | 4 | 2026-07-02 | news | accept |  |
| 72 |  | TensorRT-LLM | TensorRT-LLM | products-platforms | 4 | 2026-06-14 | news+seed | accept | #107, #260 |
| 73 |  | Edge Computing | 엣지 컴퓨팅 | infra-hardware | 4 | 2026-06-06 | news | accept | #280 |
| 74 |  | Signal-to-Noise Ratio | 신호 대 잡음비 | math-statistics | 4 | 2026-05-26 | news | accept |  |
| 75 |  | NVLink-C2C | NVLink-C2C | infra-hardware | 4 | 2026-05-19 | news | accept | #104 |
| 76 |  | WebSocket | 웹소켓 | cs-fundamentals | 4 | 2026-05-11 | news+seed | accept |  |
| 77 |  | Vector Quantization | 벡터 양자화 | deep-learning | 4 | 2026-03-29 | news+seed | accept |  |
| 78 |  | Dense Retrieval | 밀집 검색 | data-engineering | 3 | 2026-10-22 | news | accept |  |
| 79 |  | Sparse Reward | 희소 보상 | ml-fundamentals | 3 | 2026-10-22 | news | accept |  |
| 80 |  | Text-to-Image Generation | 텍스트-이미지 생성 | deep-learning | 3 | 2026-10-21 | news | accept |  |
| 81 |  | Software Vulnerability | 소프트웨어 취약점 | safety-ethics | 3 | 2026-10-18 | news | accept |  |
| 82 |  | Episodic Memory | 일화 기억 | llm-genai | 3 | 2026-10-16 | news | accept |  |
| 83 |  | Voice Cloning | 음성 복제 | deep-learning | 3 | 2026-09-24 | news | accept |  |
| 84 |  | Neural Processing Unit | 신경망 처리 장치 | infra-hardware | 3 | 2026-09-22 | news | accept |  |
| 85 |  | JAX | JAX | products-platforms | 3 | 2026-09-20 | news | accept |  |
| 86 |  | Bradley–Terry Model | 브래들리-테리 모형 | math-statistics | 3 | 2026-09-19 | news | accept |  |
| 87 |  | Jailbreak | 탈옥 | safety-ethics | 3 | 2026-09-19 | news+seed | accept |  |
| 88 |  | Perplexity | 퍼플렉서티 | math-statistics | 3 | 2026-09-19 | news | accept |  |
| 89 |  | Private Cloud Compute | 비공개 클라우드 컴퓨팅 | products-platforms | 3 | 2026-09-15 | news | accept | #33 |
| 90 |  | AI Safety Evaluation | AI 안전성 평가 | safety-ethics | 3 | 2026-09-13 | news | accept | #270 |
| 91 |  | Optimal Transport | 최적 수송 | math-statistics | 3 | 2026-09-12 | news | accept |  |
| 92 |  | Trusted Execution Environment | 신뢰 실행 환경 | infra-hardware | 3 | 2026-09-10 | news | accept |  |
| 93 |  | Machine Unlearning | 머신 언러닝 | ml-fundamentals | 3 | 2026-08-23 | news | accept |  |
| 94 |  | Embedding Model | 임베딩 모델 | llm-genai | 3 | 2026-08-22 | news+seed | accept | #201, #252, #257 |
| 95 |  | Bits per Byte | 바이트당 비트 수 | math-statistics | 3 | 2026-08-20 | news | accept |  |
| 96 |  | Data Provenance | 데이터 출처 추적 | data-engineering | 3 | 2026-08-20 | news+seed | accept |  |
| 97 |  | GPU Kernel | GPU 커널 | infra-hardware | 3 | 2026-08-20 | news | accept |  |
| 98 |  | Policy Gradient | 정책 경사 | ml-fundamentals | 3 | 2026-08-20 | news | accept |  |
| 99 |  | OpenRouter |  | products-platforms | 3 | 2026-08-18 | news+seed | accept |  |
| 100 |  | Variational Autoencoder | 변분 오토인코더 | deep-learning | 3 | 2026-08-09 | news+seed | accept |  |
| 101 |  | Token Pruning | 토큰 가지치기 | llm-genai | 3 | 2026-08-01 | news | accept |  |
| 102 |  | Sparse Attention | 희소 어텐션 | deep-learning | 3 | 2026-07-24 | news | accept |  |
| 103 |  | CodeQL |  | products-platforms | 3 | 2026-07-22 | news | accept |  |
| 104 |  | NVLink | NVLink | infra-hardware | 3 | 2026-07-21 | news+seed | accept | #75 |
| 105 |  | Matryoshka Representation Learning | 마트료시카 표현 학습 | deep-learning | 3 | 2026-07-10 | news | accept |  |
| 106 |  | Singular Value Decomposition | 특이값 분해 | math-statistics | 3 | 2026-07-08 | news+seed | accept |  |
| 107 |  | Tensor Processing Unit | 텐서 처리 장치 | infra-hardware | 3 | 2026-07-05 | news+seed | accept | #72 |
| 108 |  | Data Residency | 데이터 레지던시 | data-engineering | 3 | 2026-06-29 | news | accept |  |
| 109 |  | Process Reward Model | 과정 보상 모델 | llm-genai | 3 | 2026-06-27 | news+seed | accept |  |
| 110 |  | Multi-Head Latent Attention | 다중 헤드 잠재 어텐션 | deep-learning | 3 | 2026-06-17 | news | accept |  |
| 111 |  | 3D Reconstruction | 3차원 재구성 | deep-learning | 3 | 2026-06-16 | news | accept |  |
| 112 |  | Object Detection | 객체 탐지 | deep-learning | 3 | 2026-06-15 | news+seed | accept |  |
| 113 |  | Zero-day vulnerability | 제로데이 취약점 | safety-ethics | 3 | 2026-06-08 | news | accept |  |
| 114 |  | Contrastive Learning | 대조 학습 | deep-learning | 3 | 2026-06-07 | news+seed | accept |  |
| 115 |  | Straight-Through Estimator | 직통 추정기 | deep-learning | 3 | 2026-06-03 | news | accept |  |
| 116 |  | Claude Code | Claude Code | products-platforms | 3 | 2026-05-30 | news+seed | accept |  |
| 117 |  | AI Coding Agent | AI 코딩 에이전트 | llm-genai | 3 | 2026-05-28 | news | accept | #275 |
| 118 |  | ROCm | ROCm | infra-hardware | 3 | 2026-05-24 | news+seed | accept |  |
| 119 |  | End-to-End Encryption | 종단 간 암호화 | safety-ethics | 3 | 2026-05-21 | news | accept |  |
| 120 |  | Heterogeneous Computing | 이종 컴퓨팅 | infra-hardware | 3 | 2026-05-19 | news | accept |  |
| 121 |  | EU AI Act | EU 인공지능법 | safety-ethics | 3 | 2026-05-10 | news+seed | accept |  |
| 122 |  | Zero-Trust Security | 제로 트러스트 보안 | safety-ethics | 3 | 2026-05-06 | news | accept |  |
| 123 |  | MLX |  | products-platforms | 2 | 2026-10-24 | news+seed | accept |  |
| 124 |  | Lean 4 |  | products-platforms | 2 | 2026-10-20 | news | accept |  |
| 125 |  | Regression Testing | 회귀 테스트 | cs-fundamentals | 2 | 2026-10-20 | news | accept | #267 |
| 126 |  | Time-Series Forecasting | 시계열 예측 | ml-fundamentals | 2 | 2026-10-19 | news | accept |  |
| 127 |  | Distributed Inference | 분산 추론 | infra-hardware | 2 | 2026-10-18 | news | accept |  |
| 128 |  | Sliding-Window Attention | 슬라이딩 윈도우 어텐션 | deep-learning | 2 | 2026-10-17 | news | accept |  |
| 129 |  | Residual Stream | 잔차 스트림 | deep-learning | 2 | 2026-10-16 | news | accept |  |
| 130 |  | Application Programming Interface | 응용 프로그래밍 인터페이스 | cs-fundamentals | 2 | 2026-10-15 | news | accept |  |
| 131 |  | Closed-Loop Control | 폐루프 제어 | cs-fundamentals | 2 | 2026-10-15 | news | accept |  |
| 132 |  | llama.cpp |  | products-platforms | 2 | 2026-10-14 | news+seed | accept |  |
| 133 |  | Convolutional Neural Network | 합성곱 신경망 | deep-learning | 2 | 2026-09-27 | news+seed | accept |  |
| 134 |  | FinOps | 클라우드 재무 운영 | infra-hardware | 2 | 2026-09-27 | news | accept |  |
| 135 |  | CPU | CPU | infra-hardware | 2 | 2026-09-26 | news | accept |  |
| 136 |  | Data Lineage | 데이터 계보 | data-engineering | 2 | 2026-09-26 | news+seed | accept |  |
| 137 |  | ONNX | ONNX | products-platforms | 2 | 2026-09-26 | news+seed | accept |  |
| 138 |  | Sim-to-Real Transfer | 시뮬레이션-현실 전이 | infra-hardware | 2 | 2026-09-25 | news | accept |  |
| 139 |  | Continued Pretraining | 지속 사전 학습 | llm-genai | 2 | 2026-09-23 | news | accept | #261 |
| 140 |  | Data labeling | 데이터 라벨링 | ml-fundamentals | 2 | 2026-09-23 | news | accept |  |
| 141 |  | Network Egress Filtering | 네트워크 송신 필터링 | cs-fundamentals | 2 | 2026-09-21 | news | accept |  |
| 142 |  | OpenAI Agents SDK |  | products-platforms | 2 | 2026-09-21 | news+seed | accept |  |
| 143 |  | Computational Imaging | 전산 이미징 | deep-learning | 2 | 2026-09-20 | news | accept |  |
| 144 |  | Curriculum Learning | 커리큘럼 학습 | ml-fundamentals | 2 | 2026-09-20 | news+seed | accept |  |
| 145 |  | RoCE | RoCE | cs-fundamentals | 2 | 2026-09-20 | news | accept |  |
| 146 |  | App Intents | 앱 인텐트 | products-platforms | 2 | 2026-09-15 | news | accept |  |
| 147 |  | Brier Score | 브라이어 점수 | math-statistics | 2 | 2026-09-15 | news | accept |  |
| 148 |  | Attention Sink | 어텐션 싱크 | deep-learning | 2 | 2026-09-14 | news | accept |  |
| 149 |  | CUDA Graph |  | infra-hardware | 2 | 2026-09-13 | news | accept |  |
| 150 |  | Confidential Computing | 기밀 컴퓨팅 | infra-hardware | 2 | 2026-09-12 | news | accept |  |
| 151 |  | System Card | 시스템 카드 | safety-ethics | 2 | 2026-09-12 | news+seed | accept |  |
| 152 |  | On-Policy Learning | 온폴리시 학습 | ml-fundamentals | 2 | 2026-09-10 | news | accept |  |
| 153 |  | Mechanistic Interpretability | 기계론적 해석 가능성 | llm-genai | 2 | 2026-09-08 | news | accept |  |
| 154 |  | Multi-Cloud | 멀티클라우드 | infra-hardware | 2 | 2026-09-08 | news | accept | #51 |
| 155 |  | Gemma | 젬마 | products-platforms | 2 | 2026-08-22 | news | accept | #263 |
| 156 |  | Conformal Prediction | 컨포멀 예측 | ml-fundamentals | 2 | 2026-08-21 | news | accept |  |
| 157 |  | AI Watermarking | AI 워터마킹 | safety-ethics | 2 | 2026-08-16 | news | accept | #13 |
| 158 |  | Beam Search | 빔 탐색 | ml-fundamentals | 2 | 2026-08-16 | news+seed | accept |  |
| 159 |  | Prompt Engineering | 프롬프트 엔지니어링 | llm-genai | 2 | 2026-08-16 | news+seed | accept | #206 |
| 160 |  | Adversarial Attack | 적대적 공격 | safety-ethics | 2 | 2026-08-15 | news+seed | accept |  |
| 161 |  | 3D Gaussian Splatting | 3차원 가우시안 스플래팅 | deep-learning | 2 | 2026-08-10 | news | accept |  |
| 162 |  | Ray | Ray | products-platforms | 2 | 2026-08-08 | news | accept |  |
| 163 |  | Advantage Function | 어드밴티지 함수 | ml-fundamentals | 2 | 2026-08-07 | news | accept |  |
| 164 |  | Model Weights | 모델 가중치 | deep-learning | 2 | 2026-08-01 | news | accept | #1, #236 |
| 165 |  | Incident response | 사고 대응 | safety-ethics | 2 | 2026-07-31 | news+seed | accept |  |
| 166 |  | Recall@k | 재현율@k | ml-fundamentals | 2 | 2026-07-30 | news | accept |  |
| 167 |  | Abstract Syntax Tree | 추상 구문 트리 | cs-fundamentals | 2 | 2026-07-27 | news | accept |  |
| 168 |  | Hypernetwork | 하이퍼네트워크 | deep-learning | 2 | 2026-07-24 | news | accept |  |
| 169 |  | Scaling Laws | 스케일링 법칙 | llm-genai | 2 | 2026-07-24 | news | accept |  |
| 170 |  | Static Analysis | 정적 분석 | cs-fundamentals | 2 | 2026-07-22 | news | accept |  |
| 171 |  | Zero-shot transfer | 제로샷 전이 | ml-fundamentals | 2 | 2026-07-22 | news | accept |  |
| 172 |  | Data Processing Unit | 데이터 처리 장치 | infra-hardware | 2 | 2026-07-21 | news | accept |  |
| 173 |  | Data Poisoning | 데이터 포이즈닝 | safety-ethics | 2 | 2026-07-20 | news+seed | accept |  |
| 174 |  | Compiler | 컴파일러 | cs-fundamentals | 2 | 2026-07-17 | news | accept |  |
| 175 |  | Constrained Decoding | 제약 디코딩 | llm-genai | 2 | 2026-07-17 | news+seed | accept |  |
| 176 |  | AI Coding Assistant | AI 코딩 보조 도구 | llm-genai | 2 | 2026-07-16 | news | accept |  |
| 177 |  | CLIP | CLIP | deep-learning | 2 | 2026-07-14 | news | accept |  |
| 178 |  | Image Inpainting | 이미지 인페인팅 | deep-learning | 2 | 2026-07-13 | news | accept |  |
| 179 |  | Open-Source Model | 오픈소스 모델 | llm-genai | 2 | 2026-07-13 | news+seed | accept |  |
| 180 |  | KV cache compression | KV 캐시 압축 | deep-learning | 2 | 2026-07-12 | news | accept |  |
| 181 |  | MLOps | MLOps | infra-hardware | 2 | 2026-07-12 | news | accept |  |
| 182 |  | Instruction Tuning | 지시문 튜닝 | llm-genai | 2 | 2026-07-07 | news+seed | accept |  |
| 183 |  | Video generation | 동영상 생성 | deep-learning | 2 | 2026-07-01 | news | accept | #58 |
| 184 |  | Spatial Reasoning | 공간 추론 | llm-genai | 2 | 2026-06-30 | news | accept |  |
| 185 |  | SARIF |  | safety-ethics | 2 | 2026-06-28 | news | accept |  |
| 186 |  | Self-Consistency | 자기 일관성 | llm-genai | 2 | 2026-06-28 | news+seed | accept |  |
| 187 |  | Imitation Learning | 모방 학습 | ml-fundamentals | 2 | 2026-06-25 | news | accept |  |
| 188 |  | AlphaFold | 알파폴드 | products-platforms | 2 | 2026-06-22 | news | accept |  |
| 189 |  | Fréchet Inception Distance | 프레셰 인셉션 거리 | deep-learning | 2 | 2026-06-22 | news | accept |  |
| 190 |  | Digital twin | 디지털 트윈 | cs-fundamentals | 2 | 2026-06-19 | news | accept |  |
| 191 |  | NVIDIA Dynamo | NVIDIA Dynamo | products-platforms | 2 | 2026-06-18 | news | accept |  |
| 192 |  | Zero-shot classification | 제로샷 분류 | ml-fundamentals | 2 | 2026-06-17 | news | accept |  |
| 193 |  | Evidence Lower Bound | 증거 하한 | math-statistics | 2 | 2026-06-12 | news | accept |  |
| 194 |  | Data Parallelism | 데이터 병렬화 | infra-hardware | 2 | 2026-06-11 | news+seed | accept |  |
| 195 |  | Distributed Training | 분산 학습 | infra-hardware | 2 | 2026-06-11 | news+seed | accept |  |
| 196 |  | Expert Parallelism | 전문가 병렬화 | infra-hardware | 2 | 2026-06-11 | news+seed | accept |  |
| 197 |  | Intermediate Representation | 중간 표현 | cs-fundamentals | 2 | 2026-06-11 | news | accept |  |
| 198 |  | Affordance | 어포던스 | deep-learning | 2 | 2026-06-07 | news | accept |  |
| 199 |  | Data Lakehouse | 데이터 레이크하우스 | data-engineering | 2 | 2026-06-06 | news | accept |  |
| 200 |  | Hadamard Transform | 하다마드 변환 | math-statistics | 2 | 2026-06-04 | news | accept |  |
| 201 |  | Multimodal Embedding | 멀티모달 임베딩 | llm-genai | 2 | 2026-05-28 | news | accept | #94, #248 |
| 202 |  | Shannon Capacity | 샤논 용량 | math-statistics | 2 | 2026-05-26 | news | accept |  |
| 203 |  | Microservices | 마이크로서비스 | cs-fundamentals | 2 | 2026-05-20 | news | accept |  |
| 204 |  | CI/CD | 지속적 통합 및 지속적 제공 | cs-fundamentals | 2 | 2026-05-18 | news | accept |  |
| 205 |  | QLoRA |  | llm-genai | 2 | 2026-05-03 | news | accept |  |
| 206 |  | promptfoo |  | products-platforms | 2 | 2026-05-02 | news | accept | #159, #256 |
| 207 |  | Visual Grounding | 시각적 그라운딩 | deep-learning | 2 | 2026-04-30 | news | accept |  |
| 208 |  | Federated Learning | 연합 학습 | ml-fundamentals | 2 | 2026-04-25 | news+seed | accept |  |
| 209 |  | Parameter-Efficient Fine-Tuning | 매개변수 효율적 미세 조정 | llm-genai | 2 | 2026-04-23 | news | accept |  |
| 210 |  | Responses API | Responses API | products-platforms | 2 | 2026-04-23 | news | accept | #24 |
| 211 |  | Chrome DevTools Protocol | Chrome DevTools 프로토콜 | products-platforms | 2 | 2026-04-20 | news | accept |  |
| 212 |  | Vulnerability discovery | 취약점 발견 | safety-ethics | 2 | 2026-04-15 | news | accept |  |
| 213 |  | Camera Pose Estimation | 카메라 자세 추정 | deep-learning | 2 | 2026-04-07 | news | accept |  |
| 214 |  | Speaker Diarization | 화자 분할 | deep-learning | 2 | 2026-04-06 | news | accept |  |
| 215 |  | Directed Acyclic Graph | 방향성 비순환 그래프 | cs-fundamentals | 2 | 2026-04-05 | news+seed | accept |  |
| 216 |  | Decoder-Only Transformer | 디코더 전용 트랜스포머 | deep-learning | 2 | 2026-04-04 | news | accept |  |
| 217 |  | State Space Model | 상태 공간 모델 | deep-learning | 2 | 2026-03-26 | news+seed | accept |  |
| 218 |  | GPT-5.5 | GPT-5.5 | products-platforms | 7 | 2026-05-24 | news | queue — Versioned model name; manual review should confirm whether i | #221, #234, #243 |
| 219 |  | Kimi K3 | Kimi K3 | products-platforms | 6 | 2026-07-29 | news | queue — Specific model release; manual review is needed to confirm i |  |
| 220 |  | Gemini 4 Argon | Gemini 4 Argon | products-platforms | 5 | 2026-10-19 | news | queue — Versioned model name; manual review is needed to confirm it  |  |
| 221 |  | GPT-5.6 | GPT-5.6 | products-platforms | 5 | 2026-07-31 | news | queue — Versioned model label; manual review is needed to confirm it | #218, #234, #243 |
| 222 |  | Nemotron 3 Super | Nemotron 3 Super | products-platforms | 5 | 2026-05-08 | news | queue — Specific model release; manual review should confirm whether |  |
| 223 |  | GLM-5.2 | GLM-5.2 | products-platforms | 3 | 2026-07-13 | news | queue — Versioned model name; manual review is needed to determine w |  |
| 224 |  | Model Orchestration | 모델 오케스트레이션 | llm-genai | 3 | 2026-06-29 | news | queue — Potentially useful umbrella phrase, but its boundaries and c | #20 |
| 225 |  | Agentic AI | 에이전트형 인공지능 | llm-genai | 3 | 2026-06-28 | news | queue — Broad umbrella phrase; manual review is needed to confirm it |  |
| 226 |  | Gemini 3.5 Flash | Gemini 3.5 Flash | products-platforms | 3 | 2026-05-24 | news | queue — Versioned model variant; manual review should confirm whethe | #272 |
| 227 |  | DeepSeek V4 | DeepSeek V4 | products-platforms | 3 | 2026-04-26 | news | queue — Versioned model-family name; manual review should confirm ca |  |
| 228 |  | Dynamic Resolution | 동적 해상도 | deep-learning | 3 | 2026-04-05 | news | queue — Descriptive phrase for multiple visual-input approaches; can |  |
| 229 |  | Mastra |  | products-platforms | 2 | 2026-10-17 | news+seed | queue — A specific agent framework; manual review should confirm its |  |
| 230 |  | Action Chunking | 행동 청킹 | llm-genai | 2 | 2026-10-15 | news | queue — Potentially valid technique, but its canonical scope and sta |  |
| 231 |  | Physical AI | 물리적 AI | llm-genai | 2 | 2026-09-25 | news | queue — Potentially useful umbrella phrase, but its scope and canoni |  |
| 232 |  | Foundation Models Framework | 파운데이션 모델 프레임워크 | products-platforms | 2 | 2026-09-15 | news | queue — Apple-specific framework; manual review can confirm whether  | #10 |
| 233 |  | Frontier AI | 프런티어 AI | llm-genai | 2 | 2026-09-13 | news | queue — Potentially valid umbrella phrase; review whether it is cano | #277 |
| 234 |  | GPT-6 Astra | GPT-6 Astra | products-platforms | 2 | 2026-09-13 | news | queue — Versioned model name; manual review should verify its status | #218, #221, #243 |
| 235 |  | Neocloud | 네오클라우드 | infra-hardware | 2 | 2026-08-19 | news | queue — Emerging industry label; manual review should confirm canoni |  |
| 236 |  | Fast Weights | 빠른 가중치 | deep-learning | 2 | 2026-07-19 | news | queue — Valid but specialized research concept; manual review is nee | #164 |
| 237 |  | Stable Audio 3 | Stable Audio 3 | products-platforms | 2 | 2026-07-12 | news | queue — Versioned product name; manual review should confirm its can |  |
| 238 |  | Claude Sonnet 5 | Claude Sonnet 5 | products-platforms | 2 | 2026-07-05 | news | queue — Versioned model name; manual review should confirm whether i |  |
| 239 |  | Claude Opus 4.8 | Claude Opus 4.8 | products-platforms | 2 | 2026-05-29 | news | queue — Version-specific model name; manual review is needed to dete | #242 |
| 240 |  | Multimodal Retrieval | 다중 모달 검색 | llm-genai | 2 | 2026-05-10 | news | queue — Potentially useful umbrella phrase, but its canonical scope  | #248 |
| 241 |  | Activation Steering | 활성값 조향 | llm-genai | 2 | 2026-05-05 | news | queue — Potentially valid model-steering method, but its canonical t |  |
| 242 |  | Claude Opus 4.7 | Claude Opus 4.7 | products-platforms | 2 | 2026-04-19 | news | queue — Versioned model release; manual review should determine whet | #239 |
| 243 |  | GPT-5.4 | GPT-5.4 | products-platforms | 2 | 2026-04-19 | news | queue — Versioned model release; manual review should determine whet | #218, #221, #234 |
| 244 |  | Mid-Fusion | 중간 융합 | deep-learning | 2 | 2026-04-05 | news | queue — Potentially valid multimodal architecture term, but its cano |  |
| 245 |  | Phi-4-reasoning-vision-15B | Phi-4-reasoning-vision-15B | products-platforms | 2 | 2026-04-05 | news | queue — Specific versioned model; manual review should assess whethe |  |
| 246 |  | Model Routing | 모델 라우팅 | llm-genai | 19 | 2026-09-23 | news | reject — Duplicate of existing Model Router; both refer to selecting  | #281 |
| 247 |  | Attention Mechanism | 어텐션 메커니즘 | deep-learning | 16 | 2026-09-26 | news | reject — Duplicate of the existing Attention entry. |  |
| 248 |  | Multimodal AI | 멀티모달 인공지능 | llm-genai | 15 | 2026-10-17 | news | reject — Broad umbrella phrase substantially overlaps the existing Mu | #36, #201, #240 |
| 249 |  | On-Device Inference | 온디바이스 추론 | infra-hardware | 11 | 2026-09-22 | news | reject — Substantially overlaps with existing on-device AI. |  |
| 250 |  | Autoregressive Model | 자기회귀 모델 | deep-learning | 9 | 2026-10-21 | news | reject — Duplicate of the existing AR (autoregressive) concept. | #264 |
| 251 |  | Inference Pricing | 추론 가격 | infra-hardware | 9 | 2026-09-23 | news | reject — Substantially overlaps with existing inference cost. |  |
| 252 |  | Vector Embedding | 벡터 임베딩 | llm-genai | 6 | 2026-07-10 | news | reject — Duplicate of Embedding. | #94 |
| 253 |  | Codex | Codex | products-platforms | 5 | 2026-08-15 | news | reject — Duplicate of the existing OpenAI Codex entry. |  |
| 254 |  | AI Hallucination | AI 환각 | llm-genai | 5 | 2026-06-29 | news | reject — Duplicate of existing Hallucination |  |
| 255 |  | Pipeline Parallelism | 파이프라인 병렬화 | infra-hardware | 4 | 2026-10-16 | news+seed | reject — A form of model parallelism, substantially covered by the ex |  |
| 256 |  | Chain-of-Thought Prompting | 사고 연쇄 프롬프팅 | llm-genai | 4 | 2026-06-09 | news | reject — Duplicate of CoT. | #206 |
| 257 |  | Rotary Positional Embedding | 회전 위치 임베딩 | deep-learning | 4 | 2026-05-21 | news | reject — Duplicate of the existing RoPE term. | #94 |
| 258 |  | AWS Trainium | AWS 트레이니엄 | products-platforms | 4 | 2026-04-22 | news | reject — Duplicate of existing Trainium. |  |
| 259 |  | Long-context language model | 장문맥 언어 모델 | llm-genai | 3 | 2026-10-17 | news | reject — Overlaps the existing Context Window concept and is not a cl |  |
| 260 |  | Tensor Parallelism | 텐서 병렬화 | infra-hardware | 3 | 2026-10-16 | news+seed | reject — A form of model parallelism, substantially covered by the ex | #72 |
| 261 |  | Pretraining | 사전 학습 | deep-learning | 3 | 2026-07-20 | news | reject — Duplicate of existing pre-training. | #139 |
| 262 |  | Cybersecurity | 사이버 보안 | safety-ethics | 3 | 2026-06-14 | news | reject — Too broad and generic for a standalone technical glossary en |  |
| 263 |  | Gemma 4 12B | Gemma 4 12B | products-platforms | 3 | 2026-06-07 | news | reject — Overly specific model variant; Gemma 4 is already listed. | #155 |
| 264 |  | Autoregressive Decoding | 자기회귀 디코딩 | llm-genai | 3 | 2026-04-23 | news | reject — Substantially overlaps the existing autoregressive (AR) conc | #250 |
| 265 |  | Long-Context Modeling | 장문맥 모델링 | llm-genai | 2 | 2026-10-23 | news | reject — Overlaps the existing Context Window concept and is not a cl |  |
| 266 |  | Muse Wonder | Muse Wonder | products-platforms | 2 | 2026-10-19 | news | reject — Appears to be a product-specific model name without enough e |  |
| 267 |  | A/B Testing | A/B 테스트 | cs-fundamentals | 2 | 2026-09-24 | news | reject — Duplicate of existing A/B Test. | #125 |
| 268 |  | GPT-6 Sol | GPT-6 Sol | products-platforms | 2 | 2026-09-23 | news | reject — Versioned model label without clear evidence of established, | #218, #221, #243 |
| 269 |  | Model Misalignment | 모델 정렬 불일치 | safety-ethics | 2 | 2026-09-20 | news | reject — Substantially overlaps with existing AI Alignment. |  |
| 270 |  | LLM Evaluation | 대규모 언어 모델 평가 | llm-genai | 2 | 2026-09-19 | news | reject — Overlaps existing Evals and evaluation-focused handbook term | #90 |
| 271 |  | Semiconductor | 반도체 | infra-hardware | 2 | 2026-09-09 | news | reject — Too generic as a standalone glossary term for this AI/CS han |  |
| 272 |  | Gemini 3.7 Flash | Gemini 3.7 Flash | products-platforms | 2 | 2026-08-20 | news | reject — Version-specific model variant; Gemini is already covered. | #226 |
| 273 |  | FlashAttention | FlashAttention | products-platforms | 2 | 2026-07-24 | news+seed | reject — Duplicate of the existing FlashAttention-4 entry's underlyin |  |
| 274 |  | AI Guardrails | AI 가드레일 | safety-ethics | 2 | 2026-07-23 | news | reject — Duplicate of the existing Guardrails concept. |  |
| 275 |  | LLM Agent | LLM 에이전트 | llm-genai | 2 | 2026-07-23 | news | reject — Overlaps the existing AI Agent concept; this is a model-spec | #20, #45, #117 |
| 276 |  | AI Benchmark | AI 벤치마크 | ml-fundamentals | 2 | 2026-07-11 | news | reject — Too generic as a glossary title; benchmark is a broad catego | #35 |
| 277 |  | Frontier AI model | 프런티어 AI 모델 | llm-genai | 2 | 2026-07-03 | news | reject — Overlaps the existing Frontier Model entry. | #233 |
| 278 |  | ETL | 추출·변환·적재 | data-engineering | 2 | 2026-06-19 | news+seed | reject — Duplicate of existing ETL (Extract, Transform, Load) |  |
| 279 |  | Simulation | 시뮬레이션 | cs-fundamentals | 2 | 2026-06-13 | news | reject — Too generic without a more specific technical concept |  |
| 280 |  | Edge AI | 엣지 AI | infra-hardware | 2 | 2026-06-05 | news | reject — Substantially overlaps the existing edge deployment and on-d | #73 |
| 281 |  | Inference Routing | 추론 라우팅 | infra-hardware | 2 | 2026-05-31 | news | reject — Substantially overlaps the existing Model Router concept. | #246 |
| 282 |  | Chain-of-Thought Reasoning | 연쇄 사고 추론 | llm-genai | 2 | 2026-05-26 | news | reject — Duplicate of the existing CoT term. |  |
| 283 |  | Muse Spark |  | products-platforms | 2 | 2026-04-10 | news | reject — Specific newly launched model without sufficient evidence of |  |

## 2. 기존 시드 목록에만 있는 용어 (카테고리별)

### cs-fundamentals (61)

| ok | term | type | note |
|---|---|---|---|
|  | Asynchronous I/O | system_workflow_pattern | non-blocking input-output pattern that lets programs do other work whi |
|  | Big O Notation | foundational_concept | asymptotic notation for upper-bound growth behavior |
|  | Binary Search | foundational_concept | logarithmic search algorithm over sorted data |
|  | Bloom Filter | protocol_format_data_structure | probabilistic structure for fast approximate set membership tests |
|  | Breadth-First Search | foundational_concept | graph traversal that expands level by level |
|  | Cache Invalidation | problem_failure_mode | challenge of keeping cached data synchronized with source of truth |
|  | Call Stack | foundational_concept | stack of active function frames during program execution |
|  | CAP Theorem | foundational_concept | tradeoff framework for consistency, availability, and partition tolera |
|  | Circuit Breaker | system_workflow_pattern | failure isolation pattern that stops repeated calls to unhealthy servi |
|  | Concurrency | foundational_concept | structuring work so multiple tasks can make progress together |
|  | Connection Pool | data_storage_indexing_system | reusable set of open connections for reducing setup overhead |
|  | Consensus Algorithm | foundational_concept | protocol for distributed nodes to agree on shared state |
|  | Cursor Pagination | system_workflow_pattern | pagination method that uses stable position markers instead of offsets |
|  | Deadlock | problem_failure_mode | state where tasks wait forever on each other’s locks or resources |
|  | Depth-First Search | foundational_concept | graph traversal that explores one path deeply before backtracking |
|  | Deserialization | foundational_concept | reconstructs structured objects from serialized data |
|  | DNS | protocol_format_data_structure | distributed naming system that resolves hostnames to addresses |
|  | Event Loop | foundational_concept | runtime mechanism that schedules callbacks and asynchronous tasks |
|  | Eventual Consistency | capability_feature_spec | replicas may temporarily diverge but converge over time |
|  | Exponential Backoff | system_workflow_pattern | retry strategy that increases wait time after repeated failures |
|  | Garbage Collection | system_workflow_pattern | runtime memory management that reclaims unreachable objects |
|  | Graph | protocol_format_data_structure | node-edge data structure for representing relationships |
|  | GraphQL | protocol_format_data_structure | query language and runtime for typed API access |
|  | gRPC | protocol_format_data_structure | high-performance RPC framework using Protocol Buffers and HTTP/2 |
|  | Hash Table | protocol_format_data_structure | key-value data structure optimized for fast lookup |
|  | Heap Memory | foundational_concept | dynamic memory region used for runtime allocation |
|  | HTTP | protocol_format_data_structure | request-response application protocol used by web APIs and services |
|  | HTTPS | protocol_format_data_structure | HTTP carried over TLS for encrypted transport |
|  | JSON | protocol_format_data_structure | lightweight structured data interchange format |
|  | Leader Election | system_workflow_pattern | process for choosing a coordinator node in a distributed system |
|  | Linked List | protocol_format_data_structure | node-based sequential data structure with explicit next references |
|  | LRU Cache | data_storage_indexing_system | cache eviction policy that removes the least recently accessed items |
|  | Memoization | system_workflow_pattern | optimization technique that caches repeated function results |
|  | Memory Leak | problem_failure_mode | memory usage keeps growing because allocations are not released |
|  | Mutex | foundational_concept | mutual exclusion primitive for protecting shared state |
|  | Pagination | capability_feature_spec | splitting large result sets into smaller pages |
|  | Parallelism | foundational_concept | running multiple computations at the same time on different resources |
|  | Priority Queue | protocol_format_data_structure | queue that removes items by priority rather than arrival order |
|  | Process | foundational_concept | isolated executing program with its own memory space |
|  | Queue | protocol_format_data_structure | first-in first-out data structure used in scheduling and work processi |
|  | Recursion | foundational_concept | function technique where a routine calls itself on smaller subproblems |
|  | Replication | system_workflow_pattern | copying state across nodes for durability and availability |
|  | REST API | protocol_format_data_structure | resource-oriented web API style built on HTTP semantics |
|  | Retry | system_workflow_pattern | re-attempting failed operations under controlled conditions |
|  | RPC | protocol_format_data_structure | invocation model that calls remote services like local functions |
|  | Serialization | foundational_concept | converts in-memory objects into transferable or storable representatio |
|  | Shortest Path | foundational_concept | algorithmic problem of finding the minimum-cost route through a graph |
|  | Socket | foundational_concept | endpoint abstraction for network communication between processes |
|  | Space Complexity | metric_benchmark | how memory usage grows as input size increases |
|  | Stack | protocol_format_data_structure | last-in first-out data structure used in parsing, execution, and trave |
|  | Strong Consistency | capability_feature_spec | reads always reflect the latest committed write |
|  | Synchronous I/O | system_workflow_pattern | blocking input-output pattern that waits for each operation to finish |
|  | TCP | protocol_format_data_structure | reliable ordered transport protocol for network communication |
|  | Thread | foundational_concept | independent execution path within a process |
|  | Time Complexity | metric_benchmark | how runtime grows as input size increases |
|  | Timeout | capability_feature_spec | maximum wait duration before an operation is treated as failed |
|  | TLS | protocol_format_data_structure | cryptographic protocol that secures communication channels |
|  | Topological Sort | foundational_concept | ordering of DAG nodes that respects dependency direction |
|  | Tree | protocol_format_data_structure | hierarchical data structure of parent-child relationships |
|  | Trie | protocol_format_data_structure | tree optimized for prefix matching over strings |
|  | URL | protocol_format_data_structure | specific kind of URI that includes location details |

### data-engineering (62)

| ok | term | type | note |
|---|---|---|---|
|  | Amazon Kinesis | product_platform_service | AWS managed streaming service for ingest and analytics |
|  | Amazon Redshift | product_platform_service | managed MPP data warehouse on AWS |
|  | Apache Airflow | product_platform_service | workflow orchestrator for scheduled DAG-based data pipelines |
|  | Apache Avro | protocol_format_data_structure | row-oriented serialization format with explicit schemas |
|  | Apache Beam | library_framework_sdk | portable unified API for batch and stream processing |
|  | Apache Flink | product_platform_service | stateful stream processing engine with event-time semantics |
|  | Apache Hudi | data_storage_indexing_system | incremental lake storage focused on upserts and streaming ingest |
|  | Apache Iceberg | data_storage_indexing_system | open table format for very large analytic datasets |
|  | Apache Kafka | product_platform_service | distributed event streaming platform for durable ordered logs |
|  | Apache Parquet | protocol_format_data_structure | columnar file format optimized for analytics |
|  | Apache Pulsar | product_platform_service | distributed messaging and streaming platform with segment storage |
|  | Apache Spark | product_platform_service | distributed compute engine for batch and streaming workloads |
|  | Backfill | system_workflow_pattern | recomputes or loads historical data for missing time ranges |
|  | BigQuery | product_platform_service | serverless cloud data warehouse from Google Cloud |
|  | ClickHouse | product_platform_service | columnar OLAP database for fast real-time analytics |
|  | Columnar Storage | foundational_concept | stores values by column to speed up analytical scans |
|  | Compaction | system_workflow_pattern | rewrites fragmented files into fewer larger files |
|  | Dagster | product_platform_service | asset-oriented orchestration platform for modern data stacks |
|  | Data Catalog | data_storage_indexing_system | searchable inventory of datasets, schemas, and owners |
|  | Data Contract | capability_feature_spec | explicit agreement on schema, semantics, and delivery expectations |
|  | Data Freshness | capability_feature_spec | how current a dataset is relative to expected arrival time |
|  | Data Lake | data_storage_indexing_system | raw and semi-structured storage layer for large-scale data |
|  | Data Mesh | system_workflow_pattern | domain-oriented operating model for decentralized data ownership |
|  | Data Observability | capability_feature_spec | monitoring discipline for freshness, volume, schema, and lineage healt |
|  | Data Quality Check | system_workflow_pattern | rule-based validation for freshness, completeness, and correctness |
|  | Data Warehouse | data_storage_indexing_system | centralized analytical store optimized for SQL and BI |
|  | dbt | library_framework_sdk | transformation framework for SQL-based analytics engineering |
|  | Dead Letter Queue | data_storage_indexing_system | queue or topic used to isolate failed records for later review |
|  | Debezium | product_platform_service | CDC platform that streams database changes into event pipelines |
|  | Deduplication | system_workflow_pattern | removes repeated records before or during downstream writes |
|  | Delta Lake | data_storage_indexing_system | table format adding ACID and schema enforcement to data lakes |
|  | ELT | system_workflow_pattern | loads raw data first and transforms it inside the warehouse |
|  | Event Streaming | system_workflow_pattern | continuous publication and consumption of ordered event logs |
|  | Exactly-Once Semantics | capability_feature_spec | guarantee that each record affects downstream state once |
|  | Feature Store | data_storage_indexing_system | system for serving consistent ML features online and offline |
|  | Full Refresh | system_workflow_pattern | rebuilds a derived table from scratch instead of incrementally |
|  | Google Cloud Pub/Sub | product_platform_service | managed messaging service for event-driven data pipelines |
|  | Great Expectations | product_platform_service | open-source framework for data quality assertions |
|  | Idempotency | foundational_concept | property that makes repeated pipeline runs safe |
|  | Incremental Model | system_workflow_pattern | transformation pattern that only processes new or changed records |
|  | Kafka Connect | product_platform_service | connector framework for moving data into and out of Kafka |
|  | Late-Arriving Data | problem_failure_mode | records show up after downstream windows or partitions closed |
|  | Materialized View | data_storage_indexing_system | persisted query result maintained for faster reads |
|  | Medallion Architecture | system_workflow_pattern | bronze-silver-gold layering for staged data refinement |
|  | Metastore | data_storage_indexing_system | catalog service that maps tables to storage locations and schemas |
|  | Natural Key | foundational_concept | business-origin identifier carried from the source system |
|  | NDJSON | protocol_format_data_structure | newline-delimited JSON format for streaming and append-only logs |
|  | OLAP | foundational_concept | analytical processing optimized for aggregates and exploration |
|  | OLTP | foundational_concept | transaction processing optimized for short write-heavy operations |
|  | OpenLineage | protocol_format_data_structure | open standard for emitting lineage metadata across data tools |
|  | Partitioning | capability_feature_spec | splits large datasets into smaller segments for scale and pruning |
|  | Prefect | product_platform_service | Python-first workflow orchestration with dynamic task execution |
|  | Schema Evolution | capability_feature_spec | controlled change of schemas without breaking downstream systems |
|  | Schema Registry | data_storage_indexing_system | central store for versioned event and message schemas |
|  | Slowly Changing Dimension | foundational_concept | dimension table pattern for tracking entity changes over time |
|  | Small Files Problem | problem_failure_mode | too many tiny files causing metadata and scan overhead |
|  | Snowflake | product_platform_service | cloud-native warehouse with decoupled compute and storage |
|  | Structured Streaming | system_workflow_pattern | incremental stream processing model in Apache Spark |
|  | Surrogate Key | foundational_concept | synthetic identifier used instead of business keys |
|  | Trino | product_platform_service | distributed SQL query engine across heterogeneous data sources |
|  | Upsert | system_workflow_pattern | insert-or-update write pattern used in mutable analytical tables |
|  | Watermark | capability_feature_spec | time threshold that bounds how late events may arrive |

### deep-learning (75)

| ok | term | type | note |
|---|---|---|---|
|  | Activation Function | foundational_concept | 신경망에 비선형성을 부여하는 기본 구성요소 |
|  | AdamW | training_optimization_method | 현대 딥러닝에서 널리 쓰이는 optimizer |
|  | Autoencoder | model_algorithm_family | 입력을 압축 후 복원하며 표현을 학습하는 모델 |
|  | Backpropagation | foundational_concept | 신경망 학습의 핵심 gradient 전달 원리 |
|  | Batch Normalization | training_optimization_method | 미니배치 통계로 학습을 안정화하는 대표 기법 |
|  | Batch Size | foundational_concept | 한 번의 파라미터 업데이트에 사용하는 샘플 수 |
|  | Bottleneck Layer | foundational_concept | 정보를 압축하는 중간 층 구조 |
|  | Contrastive Loss | training_optimization_method | 표현 간 거리 관계를 학습하는 손실 함수 |
|  | Cosine Annealing | training_optimization_method | 학습률을 cosine 곡선으로 줄이는 스케줄링 |
|  | Cross-Entropy Loss | training_optimization_method | 분류 문제에서 가장 널리 쓰이는 손실 함수 |
|  | CutMix | training_optimization_method | 이미지 패치를 섞는 대표적인 비전 증강 기법 |
|  | Denoising Diffusion Probabilistic Model | model_algorithm_family | 노이즈 제거 과정을 반복 학습하는 대표 diffusion 모델 |
|  | Dice Loss | training_optimization_method | segmentation에서 overlap 최적화에 자주 쓰이는 손실 |
|  | Domain Adaptation | training_optimization_method | 훈련 도메인과 배포 도메인 차이를 줄이는 기법 |
|  | Early Stopping | training_optimization_method | 검증 성능 악화 전에 학습을 멈추는 실전 기법 |
|  | EfficientNet | model_algorithm_family | 모델 폭·깊이·해상도를 함께 조절한 비전 모델 계열 |
|  | Epoch | foundational_concept | 전체 학습 데이터를 한 번 모두 순회하는 훈련 단위 |
|  | Feature Extractor | foundational_concept | 입력에서 유용한 중간 표현을 뽑아내는 네트워크 부분 |
|  | Feature Map | foundational_concept | CNN이 추출한 중간 표현을 설명하는 기본 개념 |
|  | Focal Loss | training_optimization_method | hard example에 가중치를 두는 분류 손실 함수 |
|  | Frechet Inception Distance | metric_benchmark | 생성 이미지 품질 평가의 대표 지표 |
|  | Global Average Pooling | foundational_concept | 공간 차원을 평균으로 축약하는 대표 pooling 방식 |
|  | Gradient Checkpointing | training_optimization_method | 메모리를 줄이기 위해 일부 활성값을 재계산하는 기법 |
|  | Gradient Clipping | training_optimization_method | 폭주하는 gradient를 제한하는 안정화 기법 |
|  | Gradient Descent | training_optimization_method | 손실을 줄이기 위한 가장 기본적인 최적화 절차 |
|  | Graph Neural Network | model_algorithm_family | 그래프 구조 데이터를 위한 신경망 계열 |
|  | He Initialization | training_optimization_method | ReLU 계열 네트워크에 자주 쓰이는 초기화 방법 |
|  | Huber Loss | training_optimization_method | 이상치에 덜 민감한 회귀 손실 함수 |
|  | Image Classification | capability_feature_spec | 단일 레이블 분류를 수행하는 대표 비전 태스크 |
|  | Image-to-Image Translation | capability_feature_spec | 한 이미지 도메인을 다른 도메인으로 변환하는 태스크 |
|  | Instance Segmentation | capability_feature_spec | 객체별 마스크를 예측하는 segmentation 태스크 |
|  | Intersection over Union | metric_benchmark | segmentation과 detection에서 핵심 겹침 지표 |
|  | Keypoint Detection | capability_feature_spec | 관절·랜드마크 좌표를 찾는 비전 태스크 |
|  | Label Smoothing | training_optimization_method | 과도한 확신을 줄여 일반화를 돕는 기법 |
|  | Layer Normalization | training_optimization_method | 시퀀스 모델과 Transformer에서 핵심이 되는 정규화 기법 |
|  | Learning Rate Scheduler | training_optimization_method | 학습률을 단계적으로 조정하는 훈련 기법 |
|  | Long Short-Term Memory | model_algorithm_family | 긴 의존성을 다루기 위한 대표 RNN 변형 |
|  | Loss Function | foundational_concept | 모델 예측 오차를 수치화해 최적화 대상으로 삼는 함수 |
|  | Mamba | model_algorithm_family | [2024+] state space model 계열의 대표 최신 구조 |
|  | Masked Autoencoder | model_algorithm_family | 입력 일부를 가리고 복원하면서 표현을 학습하는 비전 모델 |
|  | Masked Image Modeling | training_optimization_method | 가려진 이미지 패치를 복원하며 학습하는 자기지도 학습 방식 |
|  | Mean Average Precision | metric_benchmark | object detection 대표 평가 지표 |
|  | Mean Squared Error | training_optimization_method | 회귀와 복원 문제에서 기본이 되는 손실 함수 |
|  | Mini-Batch | foundational_concept | 전체 데이터셋 중 배치 학습에 사용하는 작은 부분집합 |
|  | Mixed Precision Training | training_optimization_method | FP16/BF16 등을 섞어 속도와 메모리를 최적화하는 기법 |
|  | Mixup | training_optimization_method | 샘플과 라벨을 선형 결합하는 데이터 증강 기법 |
|  | MobileNet | model_algorithm_family | 모바일/엣지 환경을 위한 경량 CNN 계열 |
|  | Neural Network | foundational_concept | 딥러닝 전반을 관통하는 가장 기본 개념 |
|  | Neural Radiance Field | model_algorithm_family | 3D 장면을 연속 함수로 표현하는 대표 모델 |
|  | Neural Rendering | capability_feature_spec | 신경망으로 시점/장면을 렌더링하는 태스크 축 |
|  | Parameter Sharing | foundational_concept | 여러 위치에서 같은 파라미터를 재사용하는 핵심 설계 원리 |
|  | Pooling | foundational_concept | 특징 맵을 축약해 계산량과 민감도를 조절하는 연산 |
|  | Positional Encoding | foundational_concept | 순서 정보를 모델에 주입하는 기본 방법 |
|  | Pruning | training_optimization_method | 불필요한 가중치나 채널을 제거하는 경량화 기법 |
|  | Receptive Field | foundational_concept | 뉴런이 입력에서 참조하는 범위를 나타내는 개념 |
|  | Recurrent Neural Network | model_algorithm_family | 순차 데이터를 다루는 고전적 신경망 계열 |
|  | Residual Connection | foundational_concept | 깊은 네트워크 학습을 가능하게 한 핵심 연결 구조 |
|  | ResNet | model_algorithm_family | residual connection 기반의 대표 비전 네트워크 |
|  | RMSProp | training_optimization_method | 적응형 학습률 기반 optimizer 계열 |
|  | Skip Connection | foundational_concept | 입력 정보를 후단에 직접 전달하는 연결 패턴 |
|  | Sparsity | foundational_concept | 희소한 가중치/활성화를 이용해 효율을 높이는 개념 |
|  | Stochastic Gradient Descent | training_optimization_method | 미니배치 기반의 대표 최적화 방식 |
|  | Super-Resolution | capability_feature_spec | 저해상도 이미지를 고해상도로 복원하는 태스크 |
|  | Swin Transformer | model_algorithm_family | window 기반 계층형 비전 Transformer |
|  | Top-1 Accuracy | metric_benchmark | 분류 태스크의 기본 정확도 지표 |
|  | Top-5 Accuracy | metric_benchmark | 이미지 분류에서 자주 쓰이는 완화형 정확도 지표 |
|  | Transfer Learning | training_optimization_method | 사전학습 모델을 다른 태스크에 재사용하는 대표 전략 |
|  | Triplet Loss | training_optimization_method | anchor-positive-negative 구조를 쓰는 metric learning 손실 |
|  | U-Net | model_algorithm_family | segmentation에서 가장 널리 쓰이는 encoder-decoder 구조 |
|  | VQ-VAE | model_algorithm_family | vector quantization을 latent 표현에 도입한 VAE 계열 |
|  | Warmup | training_optimization_method | 학습 초반 안정화를 위한 학습률 증가 전략 |
|  | Weight Decay | training_optimization_method | 모델 복잡도를 줄이는 대표 regularization 방식 |
|  | Weight Initialization | training_optimization_method | 학습 안정성을 좌우하는 초기화 전략의 상위 개념 |
|  | Xavier Initialization | training_optimization_method | 깊은 신경망 초기화의 대표 방법 |
|  | YOLO | model_algorithm_family | 실시간 object detection 대표 계열 |

### infra-hardware (57)

| ok | term | type | note |
|---|---|---|---|
|  | A100 | hardware_runtime_infra | 대규모 학습 인프라의 이전 세대 표준 GPU |
|  | Admission Control | system_workflow_pattern | 리소스 한도에 맞춰 요청 수용 여부를 결정하는 운영 패턴 |
|  | Autoscaling | system_workflow_pattern | 부하에 따라 인스턴스 수를 자동 조절하는 배포 패턴 |
|  | B200 | hardware_runtime_infra | [2025+] Blackwell 세대 대표 AI GPU |
|  | Backpressure | foundational_concept | 과부하 시 입력을 제한하거나 늦추는 제어 개념 |
|  | Blackwell GPU | hardware_runtime_infra | [2025+] NVIDIA 차세대 AI 가속기 아키텍처 |
|  | Blue-Green Deployment | system_workflow_pattern | 기존/신규 환경을 분리해 전환하는 배포 방식 |
|  | Canary Deployment | system_workflow_pattern | 일부 트래픽에만 새 버전을 먼저 노출하는 배포 방식 |
|  | Cold Start | problem_failure_mode | 새 인스턴스 초기화로 인해 지연이 커지는 현상 |
|  | Compute-Bound Workload | foundational_concept | 메모리보다 연산량이 성능을 좌우하는 워크로드 |
|  | Decode Step | system_workflow_pattern | 토큰을 하나씩 생성하며 반복되는 추론 단계 |
|  | DeepSpeed | library_framework_sdk | 대규모 분산 학습과 추론 최적화용 프레임워크 |
|  | Dynamic Batching | system_workflow_pattern | 들어오는 요청을 동적으로 묶어 처리하는 배치 전략 |
|  | Elastic Training | system_workflow_pattern | 가변적인 자원 환경에서도 학습을 지속하는 분산 학습 방식 |
|  | Fully Sharded Data Parallel | training_optimization_method | 파라미터·그래디언트·옵티마 상태를 샤딩하는 분산 학습 방식 |
|  | Gaudi | hardware_runtime_infra | Intel AI 가속기 제품군의 상위 개념 |
|  | Gaudi 3 | hardware_runtime_infra | [2024+] 최신 Intel AI 가속기 세대 |
|  | GGML | protocol_format_data_structure | 경량 로컬 inference 생태계에서 쓰이는 모델 포맷/런타임 축 |
|  | GPU Utilization | metric_benchmark | GPU 자원이 실제로 얼마나 활용되는지 보는 지표 |
|  | H100 | hardware_runtime_infra | 현대 AI 훈련·추론 인프라의 대표 GPU |
|  | H200 | hardware_runtime_infra | [2024+] H100 후속 고대역폭 메모리 GPU |
|  | HBM3e | hardware_runtime_infra | [2024+] 최신 AI 가속기용 고대역폭 메모리 세대 |
|  | Helm | hardware_runtime_infra | Kubernetes 애플리케이션 배포를 패키지로 관리하는 도구 |
|  | Inferentia | hardware_runtime_infra | AWS 추론 특화 AI 칩 제품군 |
|  | Inferentia2 | hardware_runtime_infra | AWS 추론 가속기의 최신 세대 |
|  | KServe | hardware_runtime_infra | Kubernetes 기반 모델 서빙 표준 프레임워크 |
|  | L40S | hardware_runtime_infra | 추론·멀티모달 워크로드에 자주 쓰이는 GPU |
|  | Load Balancing | system_workflow_pattern | 복수 인스턴스에 요청을 분산하는 기본 운영 패턴 |
|  | Megatron-LM | library_framework_sdk | 대규모 Transformer 분산 학습용 대표 프레임워크 |
|  | Memory Bandwidth | metric_benchmark | 메모리 계층의 데이터 이동 성능을 나타내는 지표 |
|  | Memory-Bound Workload | foundational_concept | 연산보다 메모리 병목이 성능을 좌우하는 워크로드 |
|  | Microbatching | system_workflow_pattern | 큰 작업을 작은 배치로 쪼개 메모리와 처리량을 조절하는 방식 |
|  | Model Sharding | system_workflow_pattern | 대형 모델 파라미터를 여러 장치에 분산하는 방식 |
|  | Multi-Instance GPU | hardware_runtime_infra | 하나의 GPU를 여러 인스턴스로 분할하는 기능 |
|  | NVSwitch | hardware_runtime_infra | 대규모 GPU 토폴로지 연결을 위한 스위치 계층 |
|  | ONNX Runtime | hardware_runtime_infra | ONNX 모델 실행용 고성능 런타임 |
|  | PCIe | hardware_runtime_infra | CPU-GPU 및 장치 간 연결의 기본 인터페이스 |
|  | Prefill | system_workflow_pattern | 입력 전체를 한 번 처리해 초기 상태를 만드는 추론 단계 |
|  | Prefill-Decode Disaggregation | system_workflow_pattern | [2025+] prefill과 decode를 다른 자원에 분리하는 서빙 구조 |
|  | Queueing Delay | metric_benchmark | 실행 전 대기열에서 소모되는 지연 시간 |
|  | Ray Serve | hardware_runtime_infra | 분산 Python 서비스와 모델 서빙 프레임워크 |
|  | Replica | foundational_concept | 같은 모델 서빙 인스턴스를 여러 개 운영하는 단위 |
|  | Rolling Deployment | system_workflow_pattern | 트래픽을 유지하며 버전을 점진 교체하는 배포 방식 |
|  | Service-Level Objective | foundational_concept | 운영에서 허용 가능한 성능 목표를 정의하는 개념 |
|  | Sharding | system_workflow_pattern | 모델이나 데이터를 여러 조각으로 나눠 배치하는 패턴 |
|  | Spot Instance | product_platform_service | 비용 절감을 위해 가변 가용성을 감수하는 클라우드 인스턴스 |
|  | T4 | hardware_runtime_infra | 경량 추론과 비용 효율형 배포에서 자주 쓰인 GPU |
|  | Tensor Core | hardware_runtime_infra | 행렬 연산을 가속하는 GPU 내부 전용 코어 |
|  | Text Generation Inference | hardware_runtime_infra | LLM 서빙용 Hugging Face 추론 서버 |
|  | Throughput | metric_benchmark | 단위 시간당 처리 가능한 작업량 |
|  | Tokens per Second | metric_benchmark | 추론 처리량을 나타내는 대표 지표 |
|  | TorchServe | hardware_runtime_infra | PyTorch 모델 배포용 서빙 프레임워크 |
|  | TPU v5e | hardware_runtime_infra | [2024+] Google의 비용 효율형 TPU 세대 |
|  | Unified Memory | hardware_runtime_infra | CPU와 GPU 메모리 접근을 통합적으로 다루는 모델 |
|  | Warm Pool | system_workflow_pattern | cold start를 줄이기 위해 미리 띄워두는 인스턴스 풀 |
|  | Weight Streaming | system_workflow_pattern | [2025+] 필요한 시점에 가중치를 읽어오는 서빙 최적화 방식 |
|  | ZeRO | training_optimization_method | optimizer state와 gradient를 분산하는 메모리 절감 기법 |

### llm-genai (51)

| ok | term | type | note |
|---|---|---|---|
|  | Adaptive RAG | retrieval_knowledge_system | 질문 난이도/유형에 따라 retrieval 전략을 바꾸는 RAG |
|  | Agent Planning | system_workflow_pattern | 작업 분해·순서화·의사결정을 포함한 계획 단계 |
|  | Agent2Agent | protocol_format_data_structure | [2025+] 에이전트 간 상호운용 프로토콜 흐름 |
|  | Arena-Hard | metric_benchmark | [2024+] frontier 모델 비교에 자주 쓰이는 eval 세트 |
|  | Chatbot | foundational_concept | 대화형 인터페이스로 사용자와 상호작용하는 가장 기본적인 AI 제품 형태 |
|  | Citation Grounding | capability_feature_spec | [2024+] 답변에 인용/출처 연결을 요구하는 기능 축 |
|  | Closed-Weight Model | model_algorithm_family | 가중치와 내부 학습 자산이 비공개인 상용 모델 계열 |
|  | Coding Agent | system_workflow_pattern | [2024+] 코드 생성·수정·테스트까지 수행하는 소프트웨어 작업형 에이전트 |
|  | Constitutional AI | training_optimization_method | Anthropic 계열 정렬 방법론 |
|  | Context Compression | system_workflow_pattern | 긴 컨텍스트를 축약해 추론 비용을 줄이는 패턴 |
|  | Context Summarization | system_workflow_pattern | 대화/문서 상태를 요약해 유지하는 패턴 |
|  | Conversational RAG | retrieval_knowledge_system | 대화 상태를 유지하며 검색하는 RAG 패턴 |
|  | Corrective RAG | retrieval_knowledge_system | [2024+] retrieval 품질을 교정하는 RAG 계열 |
|  | Deep Research | system_workflow_pattern | [2025+] 장시간 검색·읽기·종합을 수행하는 조사형 에이전트 워크플로우 |
|  | Guided Decoding | system_workflow_pattern | 출력 형식 제약을 걸어 decoding을 유도하는 방식 |
|  | Instruction Hierarchy | foundational_concept | [2024+] 시스템·개발자·사용자 지시 우선순위 개념 |
|  | JSON Mode | capability_feature_spec | [2024+] 구조화 응답 출력을 강제하는 기능 |
|  | Judge Model | model_algorithm_family | [2024+] pairwise/score 평가를 담당하는 judge 계열 |
|  | Kahneman-Tversky Optimization | training_optimization_method | [2024+] preference learning 변형 기법 |
|  | Knowledge Cutoff | capability_feature_spec | 사전학습 시점 이후 최신성 한계를 설명하는 스펙 |
|  | Long-Horizon Planning | system_workflow_pattern | [2025+] 다단계 장기 작업 계획 능력 |
|  | Majority Voting | system_workflow_pattern | 여러 응답 중 다수결로 최종 답을 정하는 집계 방식 |
|  | Memory-Augmented Agent | system_workflow_pattern | [2024+] 외부 메모리와 결합한 에이전트 구조 |
|  | Model Cascade | system_workflow_pattern | [2024+] 작은 모델→큰 모델 순차 승격 패턴 |
|  | MT-Bench | metric_benchmark | 대화형 LLM 평가에서 널리 쓰인 벤치마크 |
|  | Multi-Agent Coordination | system_workflow_pattern | 복수 에이전트의 역할 분담과 협업을 다루는 패턴 |
|  | Multi-Agent Debate | system_workflow_pattern | 복수 에이전트 토론으로 답을 개선하는 패턴 |
|  | Multimodal Agent | system_workflow_pattern | [2025+] 텍스트·이미지·오디오 입력을 혼합해 도구까지 사용하는 에이전트 패턴 |
|  | Nucleus Sampling | system_workflow_pattern | 누적 확률 상위 집합에서 토큰을 뽑는 sampling |
|  | Odds Ratio Preference Optimization | training_optimization_method | [2024+] preference optimization 계열 |
|  | Planner-Executor | system_workflow_pattern | 계획 단계와 실행 단계를 분리하는 에이전트 구조 |
|  | Preference Model | training_optimization_method | 선호 비교 데이터를 모델링하는 구성요소 |
|  | Preference Optimization | training_optimization_method | DPO류 방법을 묶어 설명하는 상위 용어 |
|  | Prompt Chaining | system_workflow_pattern | 여러 프롬프트 단계를 순차 연결하는 설계 |
|  | Prompt Template | protocol_format_data_structure | 반복 가능한 프롬프트 구조를 정의하는 템플릿 |
|  | Query Expansion | retrieval_knowledge_system | 질문을 확장/재작성해 검색 recall을 높이는 기법 |
|  | Query Routing | retrieval_knowledge_system | 질문 유형에 따라 검색/모델 경로를 나누는 패턴 |
|  | Real-Time Multimodal | capability_feature_spec | [2025+] 음성·텍스트·시각 입력을 실시간 스트림으로 처리하는 기능 축 |
|  | Reasoning Budget | capability_feature_spec | [2025+] 추론 품질과 지연·비용 사이에서 할당하는 계산 예산 개념 |
|  | Reasoning Tokens | capability_feature_spec | [2025+] 추론 전용 계산량을 설명할 때 자주 쓰이는 개념 |
|  | Reinforcement Learning from AI Feedback | training_optimization_method | [2024+] human label 대신 AI feedback을 쓰는 정렬 방식 |
|  | Self-RAG | retrieval_knowledge_system | [2024+] 검색 필요 여부를 모델이 스스로 판단하는 RAG |
|  | Simple Preference Optimization | training_optimization_method | [2024+] DPO 대안군으로 자주 언급되는 기법 |
|  | Speech-to-Speech Model | model_algorithm_family | [2025+] 텍스트 중간 단계 없이 음성을 직접 음성으로 변환·응답하는 모델 흐름 |
|  | Streaming Output | capability_feature_spec | 토큰을 순차 전송하는 응답 모드 |
|  | System Prompt | foundational_concept | 모델 행동 규칙을 상위 우선순위로 주는 프롬프트 층 |
|  | Tool Grounding | foundational_concept | 도구 호출을 실제 스키마/실행 조건에 맞추는 개념 |
|  | Tool Selection | foundational_concept | 여러 도구 중 어떤 도구를 고를지 결정하는 핵심 문제 |
|  | Trajectory Evaluation | metric_benchmark | [2025+] 최종 답뿐 아니라 중간 행동 경로를 보는 평가 방식 |
|  | Tree of Thoughts | system_workflow_pattern | 여러 추론 경로를 탐색하는 탐색형 reasoning 패턴 |
|  | Web Search Grounding | retrieval_knowledge_system | [2024+] 웹 검색 결과 기반 grounding 패턴 |

### math-statistics (42)

| ok | term | type | note |
|---|---|---|---|
|  | Affine Transformation | foundational_concept | linear transformation followed by a translation, common in model layer |
|  | Bayes' Theorem | foundational_concept | rule for updating probabilities using new evidence |
|  | Central Limit Theorem | foundational_concept | theorem explaining why many sample means approach a normal distributio |
|  | Chain Rule | foundational_concept | rule for differentiating compositions of functions |
|  | Conditional Probability | foundational_concept | probability of an event given that another event occurred |
|  | Convex Function | foundational_concept | function whose line segments lie above or on the graph |
|  | Correlation | foundational_concept | normalized measure of linear association between variables |
|  | Covariance | foundational_concept | measure of how two variables vary together |
|  | Covariance Matrix | foundational_concept | matrix capturing pairwise covariance across multiple variables |
|  | Dot Product | foundational_concept | operation that measures alignment between two vectors |
|  | Eigenvalue | foundational_concept | scalar that describes how a transformation stretches a special directi |
|  | Eigenvector | foundational_concept | direction preserved by a linear transformation up to scaling |
|  | Expectation | foundational_concept | probability-weighted average outcome of a random variable |
|  | Gradient | foundational_concept | vector of partial derivatives showing steepest increase direction |
|  | Jacobian | foundational_concept | matrix of first-order partial derivatives for vector-valued functions |
|  | L1 Norm | foundational_concept | sum of absolute values used for sparsity and distance |
|  | L2 Norm | foundational_concept | Euclidean length computed from squared values |
|  | Likelihood | foundational_concept | how compatible observed data are with a parameter choice |
|  | Linear Transformation | foundational_concept | mapping that preserves addition and scalar multiplication in vector sp |
|  | Log-Likelihood | foundational_concept | logarithm of likelihood used for numerical stability and optimization |
|  | Logit | foundational_concept | raw unnormalized score before a probability mapping such as softmax or |
|  | Matrix | foundational_concept | rectangular array of numbers used for linear transformations and data  |
|  | Matrix Multiplication | foundational_concept | core linear algebra operation that composes transformations and domina |
|  | Maximum A Posteriori | foundational_concept | parameter estimation method that combines likelihood with a prior |
|  | Maximum Likelihood Estimation | foundational_concept | parameter estimation method that maximizes likelihood of observed data |
|  | Monte Carlo Estimation | foundational_concept | approximation method that estimates quantities through repeated random |
|  | Norm | foundational_concept | function that measures vector or matrix magnitude |
|  | Normal Distribution | foundational_concept | bell-shaped continuous distribution common in statistics and noise mod |
|  | Orthogonality | foundational_concept | relationship where vectors are perpendicular and have zero dot product |
|  | Partial Derivative | foundational_concept | derivative of a multivariable function with respect to one variable |
|  | Posterior Distribution | foundational_concept | updated distribution after combining prior beliefs with evidence |
|  | Prior Distribution | foundational_concept | distribution expressing beliefs before observing current data |
|  | Probability Distribution | foundational_concept | rule that assigns probabilities across possible outcomes |
|  | Random Variable | foundational_concept | variable whose value is determined by outcomes of a random process |
|  | Rank | foundational_concept | number of linearly independent rows or columns in a matrix |
|  | Saddle Point | foundational_concept | point that is neither a pure local minimum nor maximum because curvatu |
|  | Sampling | foundational_concept | procedure for drawing examples from a distribution or candidate set |
|  | Softmax | foundational_concept | normalization function that converts logits into a probability distrib |
|  | Standard Deviation | foundational_concept | square root of variance expressed in the original unit scale |
|  | Tensor | foundational_concept | multi-dimensional generalization of scalars, vectors, and matrices |
|  | Variance | foundational_concept | measure of how spread out values are around the mean |
|  | Vector | foundational_concept | ordered collection of numbers representing direction, magnitude, or fe |

### ml-fundamentals (74)

| ok | term | type | note |
|---|---|---|---|
|  | Accuracy | metric_benchmark | 전체 예측 중 맞은 비율을 보는 가장 기본 지표 |
|  | Bagging | training_optimization_method | 부트스트랩 샘플 위에 여러 모델을 병렬 학습하는 앙상블 방식 |
|  | Balanced Accuracy | metric_benchmark | 클래스 불균형 상황에서 각 클래스 recall을 평균내는 지표 |
|  | Bayesian Optimization | training_optimization_method | 이전 실험 결과를 반영해 유망한 설정을 탐색하는 최적화 방식 |
|  | Bias-Variance Tradeoff | foundational_concept | 과도한 단순화와 과도한 민감도 사이의 핵심 균형 개념 |
|  | Boosting | training_optimization_method | 이전 모델의 오차를 보완하며 순차적으로 학습하는 앙상블 방식 |
|  | Bootstrap | training_optimization_method | 복원추출로 표본을 반복 생성하는 통계·앙상블 기본 기법 |
|  | Calibration Curve | metric_benchmark | 예측 확률과 실제 빈도 일치를 시각화하는 평가 도구 |
|  | CatBoost | model_algorithm_family | 범주형 변수 처리에 강점을 가진 boosting 계열 모델 |
|  | Class Imbalance | problem_failure_mode | 일부 클래스 표본이 지나치게 적어 학습이 왜곡되는 문제 |
|  | Classification | capability_feature_spec | 입력을 미리 정의된 클래스 중 하나로 분류하는 태스크 |
|  | Clustering | capability_feature_spec | 유사한 샘플끼리 묶어 구조를 찾는 비지도 태스크 |
|  | Covariate Shift | problem_failure_mode | 입력 분포가 학습 시점과 배포 시점 사이에 달라지는 현상 |
|  | Cross-Validation | training_optimization_method | 여러 데이터 분할을 반복 사용해 성능을 안정적으로 추정하는 방법 |
|  | Data Leakage | problem_failure_mode | 학습 과정에 미래 정보나 정답 힌트가 섞여 평가가 왜곡되는 문제 |
|  | DBSCAN | model_algorithm_family | 밀도 기반으로 군집과 이상치를 함께 찾는 알고리즘 |
|  | Decision Boundary | foundational_concept | 서로 다른 예측 영역을 가르는 입력 공간의 경계 |
|  | Decision Tree | model_algorithm_family | 규칙 분기 구조로 예측을 수행하는 해석 가능한 모델 |
|  | Dimensionality Reduction | capability_feature_spec | 정보를 최대한 유지하며 특징 차원을 줄이는 기법 축 |
|  | Elastic Net | model_algorithm_family | L1과 L2 규제를 결합한 선형 모델 |
|  | Feature | foundational_concept | 모델 입력으로 사용하는 개별 변수 또는 속성 |
|  | Feature Engineering | training_optimization_method | 원시 데이터를 더 유용한 입력 특징으로 가공하는 작업 |
|  | Feature Importance | metric_benchmark | 각 특징이 예측에 얼마나 기여하는지 나타내는 지표 또는 분석 |
|  | Feature Selection | training_optimization_method | 예측에 중요한 특징만 남겨 모델을 단순화하는 과정 |
|  | Gradient Boosting | model_algorithm_family | 오차를 순차적으로 보정하며 약한 학습기를 쌓는 앙상블 방법 |
|  | Grid Search | training_optimization_method | 정해진 후보 조합을 전부 시험하는 하이퍼파라미터 탐색 방식 |
|  | Hierarchical Clustering | model_algorithm_family | 병합 또는 분할로 군집 계층 구조를 만드는 방식 |
|  | Hyperparameter | foundational_concept | 학습 전에 설정하고 데이터로 직접 학습되지 않는 파라미터 |
|  | Imputation | training_optimization_method | 결측값을 추정값으로 채워 넣는 데이터 전처리 방법 |
|  | k-Fold Cross-Validation | training_optimization_method | 데이터를 k개 조각으로 나눠 번갈아 검증에 쓰는 대표 CV 방식 |
|  | K-Means | model_algorithm_family | 중심점 기반으로 군집을 나누는 대표 클러스터링 알고리즘 |
|  | k-Nearest Neighbors | model_algorithm_family | 가까운 이웃 샘플을 기준으로 예측하는 비모수 모델 |
|  | Kernel Trick | foundational_concept | 고차원 변환을 명시적으로 계산하지 않고 유사도를 다루는 기법 |
|  | L1 Regularization | training_optimization_method | 절댓값 패널티를 사용해 희소성을 유도하는 규제 방식 |
|  | L2 Regularization | training_optimization_method | 제곱 패널티를 사용해 큰 가중치를 억제하는 규제 방식 |
|  | Label | foundational_concept | 예측 대상이 되는 정답 값 또는 클래스 |
|  | Lasso Regression | model_algorithm_family | L1 규제를 적용해 일부 계수를 0으로 만드는 선형 회귀 모델 |
|  | LightGBM | model_algorithm_family | 대규모 데이터에서 빠른 트리 기반 boosting 라이브러리 |
|  | Linear Regression | model_algorithm_family | 선형 관계를 가정하는 가장 기본적인 회귀 모델 |
|  | Macro Average | metric_benchmark | 클래스별 지표를 동일 가중치로 평균내는 집계 방식 |
|  | Micro Average | metric_benchmark | 전체 샘플 기준으로 지표를 통합 계산하는 집계 방식 |
|  | Naive Bayes | model_algorithm_family | 조건부 독립 가정을 두는 빠르고 단순한 확률 모델 |
|  | Normalization | training_optimization_method | 값 범위를 일정 구간이나 길이 기준으로 맞추는 스케일링 |
|  | One-Hot Encoding | training_optimization_method | 범주형 변수를 이진 벡터로 바꾸는 기본 전처리 방식 |
|  | Outlier Detection | capability_feature_spec | 정상 패턴에서 벗어난 이상 샘플을 찾는 태스크 |
|  | PR-AUC | metric_benchmark | precision-recall 곡선 아래 면적으로 불균형 데이터에서 자주 쓰는 지표 |
|  | Precision | metric_benchmark | 양성으로 예측한 것 중 실제 양성 비율 |
|  | Precision-Recall Curve | metric_benchmark | precision과 recall의 tradeoff를 보는 분류 평가 곡선 |
|  | Principal Component Analysis | training_optimization_method | 분산이 큰 축을 찾아 차원을 줄이는 대표 기법 |
|  | Probability Calibration | training_optimization_method | 모델 확률 출력이 실제 빈도와 맞도록 보정하는 과정 |
|  | Random Forest | model_algorithm_family | 여러 결정트리를 앙상블해 안정성과 성능을 높인 모델 |
|  | Random Search | training_optimization_method | 탐색 공간에서 임의 샘플을 뽑아 튜닝하는 방식 |
|  | Recall | metric_benchmark | 실제 양성 중 모델이 찾아낸 비율 |
|  | Regression | capability_feature_spec | 연속적인 수치를 예측하는 대표 ML 태스크 |
|  | Ridge Regression | model_algorithm_family | L2 규제를 적용한 선형 회귀 모델 |
|  | ROC Curve | metric_benchmark | 임계값 변화에 따른 TPR과 FPR 관계를 그린 곡선 |
|  | ROC-AUC | metric_benchmark | ROC 곡선 아래 면적으로 분류기 순위 성능을 요약한 값 |
|  | Sample | foundational_concept | 데이터셋을 구성하는 개별 관측치 |
|  | Semi-Supervised Learning | training_optimization_method | 적은 라벨과 많은 비라벨 데이터를 함께 쓰는 학습 방식 |
|  | Stacking | training_optimization_method | 여러 기본 모델 출력을 상위 메타 모델이 다시 조합하는 방식 |
|  | Standardization | training_optimization_method | 평균 0, 분산 1 기준으로 스케일을 맞추는 전처리 |
|  | Stratified Split | training_optimization_method | 클래스 비율을 유지하며 데이터를 분할하는 방식 |
|  | Support Vector Machine | model_algorithm_family | 마진을 최대화하는 결정 경계를 찾는 대표 분류 모델 |
|  | t-SNE | training_optimization_method | 고차원 데이터를 저차원 시각화로 펼치는 비선형 기법 |
|  | Target Variable | foundational_concept | 모델이 예측하려는 최종 변수 |
|  | Test Set | foundational_concept | 최종 일반화 성능을 평가하기 위한 홀드아웃 데이터 |
|  | Threshold Tuning | training_optimization_method | 분류 확률을 실제 의사결정 임계값으로 바꾸는 기준을 조정하는 과정 |
|  | Train-Validation-Test Split | system_workflow_pattern | 학습·튜닝·최종 평가를 분리하는 기본 데이터 분할 방식 |
|  | Training Set | foundational_concept | 모델 파라미터를 학습시키는 데 쓰는 데이터 분할 |
|  | UMAP | training_optimization_method | 구조 보존과 속도 면에서 자주 쓰이는 차원축소 기법 |
|  | Underfitting | problem_failure_mode | 모델이 너무 단순해 훈련 데이터조차 충분히 설명하지 못하는 상태 |
|  | Unsupervised Learning | foundational_concept | 정답 라벨 없이 구조와 패턴을 찾는 ML 패러다임 |
|  | Validation Set | foundational_concept | 모델 선택과 튜닝에 쓰는 데이터 분할 |
|  | XGBoost | model_algorithm_family | 실전 성능과 효율성으로 널리 쓰이는 gradient boosting 구현 |

### products-platforms (98)

| ok | term | type | note |
|---|---|---|---|
|  | Accelerate | library_framework_sdk | 분산 학습과 device 관리 보조 라이브러리 |
|  | Arize Phoenix | product_platform_service | LLM tracing·eval·observability 플랫폼 |
|  | AssemblyAI | product_platform_service | STT와 음성 분석 API 플랫폼 |
|  | Axolotl | library_framework_sdk | 오픈 모델 파인튜닝용 실전 설정 프레임워크 |
|  | Azure OpenAI Service | product_platform_service | Azure 인프라 위에서 OpenAI 모델을 제공하는 서비스 |
|  | Baseten | product_platform_service | 모델 배포와 실시간 inference에 특화된 플랫폼 |
|  | BentoML | library_framework_sdk | 모델 서빙 패키징과 배포를 돕는 프레임워크 |
|  | Braintrust | product_platform_service | [2024+] LLM eval과 데이터셋 관리 플랫폼 |
|  | Brave Search API | product_platform_service | 웹 검색 API 제공 서비스 |
|  | Cerebras Inference | product_platform_service | [2025+] 초고속 inference를 내세운 모델 API 제품 |
|  | Chroma | product_platform_service | 로컬 개발과 경량 RAG에 자주 쓰이는 vector DB |
|  | Claude Desktop | product_platform_service | MCP 커넥터와 데스크톱 확장을 지원하는 Anthropic 데스크톱 앱 |
|  | Cline | product_platform_service | VS Code 기반 오픈소스 코딩 에이전트 도구 |
|  | Cloudflare Workers AI | product_platform_service | 엣지 환경에서 AI inference를 제공하는 플랫폼 |
|  | Cohere API | product_platform_service | 임베딩·생성 모델을 제공하는 상용 API |
|  | Comet | product_platform_service | ML 실험 추적과 협업 플랫폼 |
|  | Continue | product_platform_service | 오픈소스 AI 코딩 어시스턴트 확장 도구 |
|  | CrewAI | library_framework_sdk | [2024+] 역할 기반 멀티에이전트 프레임워크 |
|  | Cursor | product_platform_service | [2024+] AI 코딩 IDE 대표 제품 |
|  | Databricks Mosaic AI | product_platform_service | Databricks의 생성형 AI 개발·운영 제품군 |
|  | DeepEval | library_framework_sdk | LLM 응답 품질 평가 라이브러리 |
|  | Deepgram | product_platform_service | 음성 인식과 음성 API 서비스 |
|  | DeepInfra | product_platform_service | 오픈 모델 inference를 API로 제공하는 플랫폼 |
|  | DeepSeek API | product_platform_service | [2025+] OpenAI 호환 호출 패턴으로 자주 언급되는 모델 API 서비스 |
|  | Diffusers | library_framework_sdk | 확산 모델 사용을 위한 대표 라이브러리 |
|  | DSPy | library_framework_sdk | 프롬프트/파이프라인 최적화를 위한 선언형 프레임워크 |
|  | ElevenLabs | product_platform_service | 고품질 음성 합성과 음성 클로닝 대표 플랫폼 |
|  | Evidently AI | product_platform_service | 모델 모니터링과 데이터 품질 리포팅 플랫폼 |
|  | Exa | product_platform_service | 의미 기반 웹 검색·리서치 API 플랫폼 |
|  | Fal | product_platform_service | [2024+] 이미지·비디오 모델 inference 플랫폼 |
|  | Fireworks AI | product_platform_service | [2024+] 고성능 inference API 및 서빙 플랫폼 |
|  | Galileo | product_platform_service | LLM 품질 모니터링과 평가 플랫폼 |
|  | Gemini API | product_platform_service | Google 계열 생성형 AI API 제품 |
|  | Gemini CLI | product_platform_service | [2025+] Google의 오픈소스 터미널형 AI 코딩 에이전트 제품 |
|  | Google AI Studio | product_platform_service | Gemini 실험과 프롬프트 테스트를 위한 Google 플랫폼 |
|  | Gradio | library_framework_sdk | 모델 데모·채팅 UI·멀티모달 앱을 빠르게 만드는 대표 라이브러리 |
|  | GroqCloud | product_platform_service | [2024+] 저지연 LLM inference를 강조하는 API 플랫폼 |
|  | Guidance | library_framework_sdk | 토큰 제어 기반 prompting/templating 라이브러리 |
|  | Haystack | library_framework_sdk | 검색·질의응답 파이프라인 구축용 오픈소스 프레임워크 |
|  | Helicone | product_platform_service | LLM API usage logging·gateway 플랫폼 |
|  | Hugging Face Hub | product_platform_service | 모델·데이터셋·Spaces를 공유하고 배포하는 핵심 플랫폼 |
|  | Hugging Face Inference Endpoints | product_platform_service | 전용 인프라에 모델을 배포하는 Hugging Face managed endpoint 제품 |
|  | Hugging Face Inference Providers | product_platform_service | [2025+] 다양한 추론 파트너를 단일 인터페이스로 묶는 Hugging Face 추론 제품군 |
|  | Hugging Face Spaces | product_platform_service | Gradio·Streamlit 기반 AI 데모 앱을 호스팅하는 플랫폼 |
|  | Humanloop | product_platform_service | 프롬프트 운영과 eval 워크플로를 제공하는 플랫폼 |
|  | IBM watsonx.ai | product_platform_service | IBM의 엔터프라이즈 AI 플랫폼 |
|  | Instructor | library_framework_sdk | LLM 응답을 구조화 타입으로 받기 쉽게 해주는 라이브러리 |
|  | Jina AI | product_platform_service | retrieval·reader 계열 API와 도구를 제공하는 플랫폼 |
|  | Label Studio | product_platform_service | 멀티모달 데이터 라벨링 플랫폼 |
|  | Langfuse | product_platform_service | 오픈소스 중심 LLM observability 플랫폼 |
|  | LangGraph | library_framework_sdk | [2024+] 상태 기반 에이전트 그래프 프레임워크 |
|  | LangSmith | product_platform_service | LangChain 계열 tracing·eval·observability 플랫폼 |
|  | LlamaIndex | library_framework_sdk | RAG와 데이터 커넥터 중심의 대표 프레임워크 |
|  | Luma AI | product_platform_service | 비디오 생성과 3D 캡처 제품군 |
|  | Milvus | product_platform_service | 대규모 벡터 검색을 위한 오픈소스 데이터 플랫폼 |
|  | Mistral API | product_platform_service | Mistral 계열 모델을 제공하는 상용 API |
|  | MLflow | product_platform_service | 실험 추적과 모델 레지스트리의 대표 플랫폼 |
|  | Modal | product_platform_service | GPU 워크로드와 AI 배포에 자주 쓰이는 서버리스 플랫폼 |
|  | Neptune | product_platform_service | 모델 실험 메타데이터 추적 플랫폼 |
|  | OpenAI API | product_platform_service | LLM 앱 개발에서 가장 널리 쓰이는 모델 API 제품 |
|  | OpenSearch | product_platform_service | 검색과 벡터 검색을 함께 다루는 플랫폼 |
|  | Outlines | library_framework_sdk | 구조화 출력과 constrained generation 라이브러리 |
|  | Patronus AI | product_platform_service | LLM risk·evaluation 중심의 플랫폼 |
|  | PEFT | library_framework_sdk | parameter-efficient fine-tuning 라이브러리 |
|  | Perplexity API | product_platform_service | [2025+] 검색 결합형 응답 API 제품 |
|  | Pika | product_platform_service | 텍스트·이미지 기반 영상 생성 제품 |
|  | Pinecone | product_platform_service | 대표적인 managed vector database 서비스 |
|  | Portkey | product_platform_service | AI gateway와 provider routing 플랫폼 |
|  | PromptLayer | product_platform_service | 프롬프트 버전 관리와 로그 수집 플랫폼 |
|  | PydanticAI | library_framework_sdk | [2024+] Pydantic 기반 에이전트/LLM 애플리케이션 프레임워크 |
|  | Qdrant | product_platform_service | 오픈소스 중심 vector database 플랫폼 |
|  | Ragas | library_framework_sdk | RAG 평가에 널리 쓰이는 라이브러리 |
|  | RedisVL | library_framework_sdk | Redis 기반 벡터 검색을 위한 라이브러리/제품 축 |
|  | Replicate | product_platform_service | 오픈 모델을 API로 실행할 수 있는 대표 플랫폼 |
|  | Roboflow | product_platform_service | 컴퓨터 비전 데이터 관리와 모델 배포 도구 |
|  | RunPod | product_platform_service | GPU 임대와 모델 서빙에 자주 쓰이는 인프라 플랫폼 |
|  | Runway | product_platform_service | 영상 생성과 편집을 제공하는 대표 생성형 미디어 제품 |
|  | SambaNova Cloud | product_platform_service | [2025+] 고성능 모델 API와 inference를 제공하는 클라우드 |
|  | Semantic Kernel | library_framework_sdk | Microsoft 계열 AI 앱 오케스트레이션 SDK |
|  | SerpAPI | product_platform_service | 검색 엔진 결과 수집용 API 플랫폼 |
|  | smolagents | library_framework_sdk | 가벼운 코드 실행형 에이전트 프레임워크 |
|  | Snowflake Cortex | product_platform_service | Snowflake 내부에서 AI 기능을 제공하는 플랫폼 제품 |
|  | Sourcegraph Cody | product_platform_service | 코드 검색 연계형 AI 코딩 도우미 |
|  | Stability AI API | product_platform_service | 이미지 생성 모델 API 제품 |
|  | Tavily | product_platform_service | AI agent용 웹 검색 API |
|  | Together AI | product_platform_service | 오픈 모델 서빙과 inference API를 제공하는 플랫폼 |
|  | Transformers | library_framework_sdk | 오픈 모델 사용의 표준 라이브러리 |
|  | TruLens | library_framework_sdk | LLM app 평가와 추적을 위한 오픈소스 툴킷 |
|  | Unsloth | library_framework_sdk | [2024+] LLM 파인튜닝 최적화 라이브러리 |
|  | v0 | product_platform_service | Vercel의 UI 생성형 개발 제품이자 모델 API 제품군 |
|  | Vercel AI SDK | library_framework_sdk | 웹 앱에서 LLM UX를 빠르게 붙이는 대표 SDK |
|  | Vertex AI | product_platform_service | Google Cloud의 대표 AI 개발 플랫폼 |
|  | Vertex AI Agent Builder | product_platform_service | [2025+] Google Cloud의 에이전트 구축·배포 제품군 |
|  | Voyage AI | product_platform_service | 임베딩과 reranking 중심의 AI API 서비스 |
|  | Weaviate | product_platform_service | 벡터 검색과 retrieval용 데이터 플랫폼 |
|  | Weights & Biases | product_platform_service | 실험 추적과 모델 관찰의 대표 플랫폼 |
|  | Windsurf | product_platform_service | [2025+] AI 코딩 에이전트 IDE 제품 |
|  | xAI API | product_platform_service | [2025+] Grok 계열 모델과 agent tools를 제공하는 API 플랫폼 |

### safety-ethics (36)

| ok | term | type | note |
|---|---|---|---|
|  | Abuse Monitoring | system_workflow_pattern | ongoing observation of misuse patterns, policy violations, and attack  |
|  | Audit Trail | capability_feature_spec | record of actions and changes used for accountability and investigatio |
|  | Bias | problem_failure_mode | systematic skew in outputs that can create unfair or distorted outcome |
|  | Content Authenticity | foundational_concept | practice of verifying the origin, integrity, and modification history  |
|  | Content Moderation | system_workflow_pattern | screening process for unsafe, disallowed, or policy-violating content |
|  | Deceptive Alignment | problem_failure_mode | advanced alignment risk where a model appears aligned while pursuing d |
|  | Demographic Parity | metric_benchmark | fairness criterion comparing positive prediction rates across groups |
|  | Differential Privacy | foundational_concept | privacy framework that bounds how much one record can affect outputs |
|  | Dual Use | foundational_concept | property of AI capabilities that can support beneficial uses and harmf |
|  | Equalized Odds | metric_benchmark | fairness criterion comparing error rates across groups at matched outc |
|  | Explainability | capability_feature_spec | ability to provide human-understandable reasons for a model's output o |
|  | Fairness | foundational_concept | goal of avoiding unjustified disparities across people or groups |
|  | Fallback Policy | system_workflow_pattern | predefined action taken when the primary model path is unsafe or unrel |
|  | Frontier AI Safety | foundational_concept | safety practices focused on highly capable frontier model development  |
|  | Guardrail | capability_feature_spec | constraint or control layer that blocks or limits unsafe behavior |
|  | Human Oversight | capability_feature_spec | practice of keeping human review or intervention in high-risk decision |
|  | Interpretability | capability_feature_spec | ability to inspect and understand internal model mechanisms or learned |
|  | Misalignment | problem_failure_mode | state where a model's behavior or objectives diverge from human intent |
|  | Model Card | protocol_format_data_structure | documentation artifact describing model purpose, limits, and evaluatio |
|  | Model Extraction | problem_failure_mode | attack that reconstructs a model or its behavior through repeated quer |
|  | Model Inversion | problem_failure_mode | attack that infers sensitive attributes or source patterns from model  |
|  | Model Misuse | problem_failure_mode | unsafe or abusive use of a model outside intended or permitted boundar |
|  | NIST AI Risk Management Framework | protocol_format_data_structure | risk management framework for governing AI design, deployment, and ove |
|  | Out-of-Distribution Detection | capability_feature_spec | ability to recognize inputs unlike the training or operating distribut |
|  | Personally Identifiable Information | foundational_concept | information that can identify or trace a specific individual |
|  | Privacy-Preserving Machine Learning | training_optimization_method | methods for training or using ML systems while reducing exposure of se |
|  | Prompt Leakage | problem_failure_mode | exposure of hidden instructions, secrets, or internal prompts to users |
|  | Refusal | capability_feature_spec | behavior where a model declines unsafe or disallowed requests |
|  | Responsible AI | foundational_concept | development and deployment approach emphasizing fairness, safety, acco |
|  | Safety Classifier | model_algorithm_family | classifier used to detect unsafe content, intent, or policy violations |
|  | Safety Evaluation | system_workflow_pattern | measurement process focused on harms, misuse, and failure behavior |
|  | Sensitive Information Disclosure | problem_failure_mode | LLM application risk where private, confidential, or security-sensitiv |
|  | Specification Gaming | problem_failure_mode | behavior where a system exploits gaps between the written objective an |
|  | Synthetic Media | foundational_concept | media generated or substantially modified by AI systems |
|  | Toxicity | problem_failure_mode | harmful, abusive, or hateful language generated or amplified by a syst |
|  | Uncertainty Estimation | capability_feature_spec | technique for estimating how uncertain a model is about its output |

## 3. 뉴스 1편에만 나온 용어

`candidates.jsonl`에 있음 (posts=1). 기본 제외 — 필요하면 검색해서 추가.
