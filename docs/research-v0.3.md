# 원래 아이디어에 대한 재검토

확인일: 2026-10-07~08 (KST). 공개 릴리스 준비 중 공식 Promptfoo/LangSmith 문서와 scaffold-ablation/Strands 이슈를 다시 확인했다. 공식 문서, 공개 저장소/이슈와 직접 확인한 API에 기반한다. 사용자 인터뷰나 대표 표본 조사는 수행하지 않았다.

## 판단

**문제의식이나 구성 요소가 유일한 아이디어는 아니다.** 모델 비교, 비용 관찰, 명세 보존, 평가를 통한 자동 개선에는 선행 사례가 있다. 기회는 개인과 소규모 팀의 오래된 작업에 이를 적용할 때 생기는 준비·선택의 부담을 줄이는 데 있다는 가설이다. 전 세계 수요 규모나 모든 경쟁 제품의 부재를 확인한 것은 아니다.

| 사례 | 확인한 내용 | 제품 판단 |
|---|---|---|
| [Promptfoo](https://www.promptfoo.dev/docs/getting-started/) · [cache](https://www.promptfoo.dev/docs/configuration/caching/) | 모델/prompt/검사 비교, provider/request/config 기반 cache, 새 표본을 위한 cache 비활성화 | 비교와 호출 절약 자체는 새 발명이 아니다. |
| [LangSmith](https://docs.langchain.com/langsmith/compare-experiment-results) | Dataset의 experiment 비교, 출력 diff, 개선/회귀와 사례별 필터 | 결과 비교 화면만으로 차별화하기 어렵다. |
| [Braintrust](https://www.braintrust.dev/learn/ai-agent-evaluation/v0) | Agent 단계별 평가, experiment 비교, model/prompt 변경 후 재실행 | 평가 인프라를 모두 다시 만들기보다 통합할 여지가 있다. |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | 무엇을 왜 만들지 명세하고 plan/tasks/implementation에 연결 | 원래 의도를 모델과 분리해 보존하는 접근에도 선행 사례가 있다. |
| [GEPA](https://github.com/gepa-ai/gepa) | 평가와 reflection을 통한 prompt/text parameter 최적화 | 자동 개선과 재실행 대상 선정은 구분해야 한다. |
| [Scaffold ablation on model upgrade](https://github.com/agentpatternscatalog/patterns/blob/main/patterns/scaffold-ablation-on-model-upgrade.md) | 모델 약점을 전제로 만든 harness 요소를 upgrade마다 평가하면서 제거 | 옛 모델의 제약이 새 모델을 제한한다는 문제의식과 직접 겹친다. |

마지막 열은 자료를 바탕으로 한 제품 판단이다. 해당 도구들이 다른 워크플로를 지원하지 않는다는 뜻은 아니다.

## 직접 드러난 pain point

[Strands Evals의 비교 기능 이슈](https://github.com/strands-agents/evals/issues/88)는 모델 교체 비용이 가치 있는지, 새 tool이 품질을 높였는지, latency만 늘렸는지 판단하기 어렵다고 명시한다. 사례별 regression, 비용·quality 비교, 통계적 불확실성을 다룬다. 이는 개발자의 직접적인 문제 기록이지만 시장 크기를 알려주는 대표 표본은 아니다.

사용자의 요청과 이 사례들을 연결하면 네 가지 부담을 구분할 수 있다.

1. 최종 결과물만 남아 원래 요구와 실패 원인을 복구해야 하는 **보관 비용**.
2. 모델이 나올 때마다 모든 과제를 다시 보내거나 사람이 골라야 하는 **선택 비용**.
3. 이전 해결책의 형태가 새 시도를 제한하는 **상속된 가정**.
4. 보기 좋은 diff와 실제 기능 향상을 구분해야 하는 **개선 판단**.

첫 세 항목의 상대적 중요도와 유료 수요는 검증할 가설이다. 마지막 항목에는 이미 경쟁력 있는 공급이 있다.

## 이번 구현에 반영한 것

첫 화면을 여러 프로젝트의 원래 문제 보관함으로 만들었다. Intent/source, constraints, observed failures, legacy assumptions, capability 요구, 영향도/비용 추정을 별도로 보존한다. 기존 명세·실험 관행을 연결한 형식이지 새 표준을 발명했다는 주장이 아니다.

[OpenRouter Models API](https://openrouter.ai/docs/api/api-reference/models/get-models)의 availability/created/context/modality/pricing metadata를 사용한다. 실제 연결로 465개 항목을 관찰했다. 첫 조회는 inventory이고 이후 차이는 observation이다. 출시 시점이나 context 길이가 과제 해결력 향상을 입증하지는 않는다. Capability 근거와 실행 모델 연결은 명시적인 profile에 둔다.

선택은 영향도/추정비용과 capability overlap을 쓰는 공개된 heuristic이다. 성공확률 예측처럼 포장하지 않는다. 같은 source/checks/model revision/harness/trial의 중복 시도는 이력으로 피하고, 선택된 과제에만 baseline probe와 bounded revision을 실행한다. 비용이 불명확하면 다음 실행을 막는다.

C 방식은 원래 목표로 brief를 만든 뒤 기존 코드를 수정한다. 이후 v0.4에서는 기존 writable source를 보지 않는 D 재구현과 독립 입력 검사를 추가했다. [실제 사례](real-cases-v0.4.md)에서는 기능 점수가 같았고 가장 저렴한 방식은 사례마다 달랐다. v0.5는 사용자가 직접 요구를 기록하고 결과를 공개하는 준비 부담을 줄인다. 과거 모델을 모르는 결과물과 새 결과물의 비교는 알려진 구·신 모델의 인과적 benchmark도 아니다.

## 다음 검증

차별화 가설은 **“새 모델이 나온 뒤 오래된 프로젝트 중 무엇을 다시 풀 가치가 있는지, 이유와 결과를 함께 남기는 개인용 작업 보관함”**이다. Release watcher나 dashboard만으로 지속적인 우위를 주장하기 어렵다. 축적할 정보는 원래 목적 → 실패 이유 → 재시도 근거 → 실제 채택된 개선의 연결이다.

5–8명, 약 20개 과제, 2주 사용을 제안한다. 아직 실시하지 않았다. 기록 준비 시간, 채택된 개선, 회귀, 토큰/비용당 채택, 두 번째 과제 재사용률을 측정한다. 사용자가 다시 오지 않으면 기능을 늘리기보다 보관과 평가 준비 비용부터 줄여야 한다.

OSS 공개 자료는 세 과제의 선택/보류 이유, 실제 before/after, 전체 비용, 중복 실행 회피를 60초 안에 보여주는 데 집중한다. No-key demo와 명확한 한계를 포함한 증거를 우선한다. 연말 흥행이나 바이럴 가능성을 현재 자료로 확정할 수는 없다.
