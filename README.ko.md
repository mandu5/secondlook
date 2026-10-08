# Second Look

**새 모델이 나왔다. 예전 작업에서 실제로 무엇이 좋아졌나?**

원래 문제와 실패 이유를 보관하고, 예산 안에서 다시 풀 작업을 고른 뒤,
기존 수정·문제 재정의 후 수정·기존 코드 없이 재구현한 결과를 같은 기준으로
비교하는 오픈소스입니다. 기능 변화, 회귀, 화면, 토큰과 비용을 함께 봅니다.

[설치 없이 데모 보기](https://mandu5.github.io/secondlook/) · [English](README.md) ·
[다운로드](https://github.com/mandu5/secondlook/releases)

MIT · Python 3.11+ · macOS / Linux · **0.5 beta**

## 모델 계정 없이 시작

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'https://github.com/mandu5/secondlook/releases/download/v0.5.0/secondlook_revisit-0.5.0-py3-none-any.whl'
python -m playwright install chromium
secondlook doctor
secondlook demo --offline --output ./first-look
```

`first-look/report.html`을 브라우저에서 열면 됩니다. 의도적으로 결함을 넣은
예제와 사람이 작성한 수정안을 실제 Chromium으로 검사해 **3/8 → 8/8**을
보여줍니다. 모델 호출은 0회이며, 모델 성능 비교 자료는 아닙니다.

## 내 작업 넣기

간단한 텍스트 요구는 JSON을 작성하지 않고 지정할 수 있습니다.

```bash
secondlook init ./my-app --files index.html \
  --intent '독자를 환영하고 문서 링크를 유지한다' \
  --expect-text 'role=heading[level=1]' 'Hello' \
  --preserve-text 'role=link[name="Documentation"]' 'Documentation' \
  --output ./capsule.json
secondlook probe ./capsule.json --output ./baseline
```

문구와 selector는 실제 요구에 맞게 바꿉니다. `--expect-text`는 개선 목표,
`--preserve-text`는 유지할 기능입니다. 생성된 intent는 draft입니다. 검토 후
확인해야 모델을 호출할 수 있습니다. 독립적인 요구사항 파일을 추가하면
기존 코드 없이 새로 구현하는 D 방식도 비교합니다.
[전체 실행 예시](docs/quickstart.md).

현재 실행 adapter는 **신뢰할 수 있는 static HTML/CSS/JS + Claude Code CLI**입니다.
Python·backend·임의 저장소 실행과 다른 provider는 지원하지 않습니다.
연구·문서·기획 과제도 보관할 수 있지만 실행 adapter가 없으면 보류됩니다.

## 토큰과 판단 비용을 줄이는 방법

이미 기준을 만족한 과제는 무료 probe에서 건너뜁니다. 같은 조건으로 시도한
과제는 이력으로 중복 실행을 막습니다. 큰 HTML에서는 script만 context에
넣는 방식을 지원합니다. 이는 context **byte** 절감이며 보편적인 토큰 절약률을
검증한 것은 아닙니다. 모델 catalog 변화는 관찰·queue 준비만 하며 유료 호출은
명시적인 `revisit` 실행에서 이루어집니다. 비용이 불명확하면 다음 호출을 멈춥니다.

## 결과 공유

```bash
secondlook share ./first-look/result.json --output ./shareable
# 화면과 원래 요청을 공유할 때만 명시적으로 포함합니다.
secondlook share ./first-look/result.json --output ./visual-share \
  --include-screenshots --include-intent
```

`index.html`과 `summary.json`을 함께 공유하면 됩니다. 기본값은 지표와 익명화된
검사 이름만 내보내며, 인식 가능한 versioned model ID도 포함합니다. 원본 코드,
prompt, raw receipt, 개인 경로와 상세 오류는 제외합니다. 화면·요청을 포함하면
그 안의 내용은 그대로 공개되므로 확인이 필요합니다. 자동 업로드는 없습니다.

실제 기존 프로젝트 두 개에서 모든 방식이 각각 **6/9 → 9/9**, **3/7 → 7/7**에
도달했습니다. 재구현이 더 저렴한 사례도, 기존 수정이 더 저렴한 사례도
있었습니다. 이미 통과한 연구 페이지는 0회 호출했습니다. [평가 실수까지 포함한
전체 측정](docs/real-cases-v0.4.md)을 공개합니다. 과거 제작 모델은 미상이며,
SOTA·일반적 우월성·시장 수요를 증명한 결과는 아닙니다.

[선행 도구·차별화 가설](docs/research-v0.3.md) · [기여 안내](CONTRIBUTING.md) ·
[데이터 경계](SECURITY.md) · [명령어 참고](docs/cli-reference.md)
