# 비용 없는 시작과 검증 가능한 재시도

확인일: 2026-10-08. 공식 제품 문서, 공개 개발 이슈와 논문 초록을 확인했다.
논문 실험을 재현하거나 신규 사용자 인터뷰를 실시한 것은 아니다.

## 이번 조사에서 바뀐 결정

| 확인한 자료 | 직접 확인한 내용 | Second Look에 반영한 판단 |
| --- | --- | --- |
| [Promptfoo caching](https://www.promptfoo.dev/docs/configuration/caching/) | 요청·provider 설정을 구분한 cache와 반복 실행별 namespace가 있다. 새 표본에는 cache를 끄는 방법을 안내한다. | 비용 절약과 독립 표본 생성을 구분한다. 같은 결과의 재평가를 새 모델 실험으로 세지 않는다. |
| [Promptfoo configuration](https://www.promptfoo.dev/docs/configuration/reference/) | `providerOutput`으로 이미 생성된 출력에 assertion을 적용하며 provider 호출을 생략할 수 있다. | 결과 import 자체는 새 발명이 아니다. 기존 AI 도구를 그대로 쓰게 하는 실용적 진입 경로로 채택한다. |
| [LangSmith comparison](https://docs.langchain.com/langsmith/compare-experiment-results) · [외부 실험 import](https://docs.langchain.com/langsmith/upload-existing-experiments) | 여러 experiment의 차이와 회귀를 비교하고 외부에서 실행한 실험도 올릴 수 있다. | 비교 dashboard만으로 차별화하지 않는다. 원래 목적·과거 구현·평가 기준을 묶는 준비 과정에 집중한다. |
| [Strands Evals 이슈 #88](https://github.com/strands-agents/evals/issues/88) | 모델·prompt·도구 변경이 품질과 비용에 어떤 영향을 주는지 비교하려는 개발 요구가 기록돼 있다. | 실제 pain point의 한 사례다. 대표 수요 조사나 시장 크기 근거는 아니다. |
| [LLM-as-Judge on a Budget](https://arxiv.org/abs/2602.15481) | 확률적 judge 점수의 분산을 이용해 제한된 평가 예산을 배분하는 연구다. | 과거 task의 개선 가능성 예측과 동일한 문제가 아니다. 데이터 없이 이 알고리즘이나 절감률을 제품 성과로 주장하지 않는다. |
| [Correcting the Winner's Curse in Adaptive Benchmarking](https://arxiv.org/abs/2605.05973) | 튜닝에 재사용한 평가 항목에서 고른 최고 결과가 새로운 데이터의 성능을 과대평가할 수 있음을 다룬다. | 기준을 먼저 고정하고 실패·회귀를 함께 공개한다. 단일 성공 사례를 SOTA나 일반적인 모델 우위로 부르지 않는다. |

마지막 열은 자료로부터 내린 제품 판단이다. 경쟁 제품 전체 기능을 조사해
부재를 입증했다는 뜻은 아니다. 두 논문은 공개 초록 수준으로 확인했고,
통계적 보장이나 실험 수치를 이 제품에 이전하지 않는다.

## v0.6의 제품 범위

추가 API 계정 없이 `prepare → 외부 생성 → assess → share`로 시작한다.
준비 시 원래 의도, 원본과 검사 기준을 고정하고, 응답의 request ID로 혼입을
막는다. 재구현 요청에는 과거 writable source를 넣지 않는다. 외부 도구가
어떤 추가 context를 봤는지는 검증할 수 없어 명시적으로 미확인으로 남긴다.

Local assessment는 최대 네 후보에 같은 브라우저 검사를 적용한다. 같은
구현은 해당 batch의 검사 증거를 재사용하고 표시한다. 사용자 입력 모델명,
토큰과 비용은 provider receipt로 격상하지 않는다. 비용 미상은 0원이 아니다.

현재 가능한 실행 대상은 신뢰할 수 있는 static HTML/CSS/JS다. 외부 결과를
가져올 수 있다는 것이 모든 provider의 API 통합이나 임의 repository 실행을
의미하지 않는다. 외부 도구로 요청을 보내고 결과를 저장하는 단계는 수동이다.

## 다음에 검증할 가설

1. **시작 부담:** 같은 과제로 capsule 수동 작성과 prepare/import 흐름을
   비교한다. 최초 비교까지 걸린 시간, 수정 횟수와 포기한 단계를 기록한다.
2. **실제 채택:** 통과 수 증가와 사용자가 채택한 개선을 따로 수집한다.
   원래 의도가 불충분했던 사례와 만족한 과제에서의 새로운 개선도 기록한다.
3. **선택 비용:** 전체 재실행과 선택적 재실행에 동일한 task 집합·모델·예산을
   적용하고, 토큰뿐 아니라 놓친 개선을 기록한다. 일부 보류 과제를 별도로
   검사하는 탐색 표본이 필요하다. 아직 절감률·누락률은 측정하지 않았다.
4. **반복과 범위:** 두 번째 좁은 adapter는 구조화된 추출 결과를 우선 검토한다.
   임의 Python 실행보다 격리 부담이 작다. 코드 실행 확대에는 실제 sandbox가
   필요하다. 알려진 모델 버전의 반복 표본과 고정된 평가 protocol을 확보한다.

5–8명/약 20개 과제의 사용성 pilot은 제안 상태다. 모집·인터뷰·유료 지출은
이번 작업에 포함하지 않았다. 제품의 가치는 아직 위 가설로 평가해야 한다.

## 무료 주소

[Vercel Hobby](https://vercel.com/docs/plans/hobby)는 무료 플랜이고,
[기본 배포 주소](https://vercel.com/docs/deployments/generated-urls)를 제공한다.
따라서 개인 아이디를 포함하지 않는 프로젝트명 기반 주소를 목표로 할 수 있다.
이는 `.io` 도메인을 무료로 소유하는 것과 다르다. 이름 배정과 계정 접근,
실제 배포를 확인하기 전에는 특정 주소를 확보했다고 표시하지 않는다.
