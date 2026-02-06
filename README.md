# shared-workflows

재사용 가능한 GitHub Actions 워크플로우와 Python 유틸리티 모음

## 빠른 시작

### 1. 대시보드 레포에서 사용하기

기존 `.github/workflows/update.yml` 파일을 다음과 같이 교체:

```yaml
name: Update Dashboard

on:
  schedule:
    - cron: '0 22 * * *'  # 7 AM KST
  workflow_dispatch:

jobs:
  update:
    uses: kittycapital/shared-workflows/.github/workflows/python-fetch.yml@main
    with:
      script: fetch_data.py
      requirements: requests yfinance
    secrets: inherit
```

기존 30-50줄 워크플로우가 15줄로 줄어듦!

### 2. Python 유틸리티 사용하기

`fetch_utils.py`를 레포에 복사하거나:

```python
# fetch_data.py
from fetch_utils import (
    fetch_with_retry,
    get_coingecko_price,
    get_defillama_fees,
    save_json,
    get_kst_timestamp,
    format_usd,
    format_korean_number
)

# CoinGecko (자동 rate limiting 포함)
prices = get_coingecko_price(["bitcoin", "ethereum"])

# DefiLlama
fees = get_defillama_fees()

# 자동 retry + 에러 핸들링
resp = fetch_with_retry("https://api.example.com/data", max_retries=3)

# JSON 저장 (폴더 자동 생성)
save_json({"data": prices, "updated": get_kst_timestamp()}, "data/prices.json")
```

## 워크플로우 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `script` | (필수) | 실행할 Python 스크립트 |
| `python-version` | `3.11` | Python 버전 |
| `requirements` | `requests` | 설치할 pip 패키지 (공백 구분) |
| `data-paths` | `data/ index.html` | 커밋할 파일/폴더 |
| `commit-message` | `Update data` | 커밋 메시지 접두어 |
| `timezone` | `Asia/Seoul` | 로그 타임존 |

## 지원되는 Secrets

워크플로우가 자동으로 인식하는 시크릿:

- `COINGECKO_API_KEY`
- `MOLIT_API_KEY`
- `GOOGLE_MAPS_API_KEY`
- `FMP_API_KEY`
- `ALPHA_VANTAGE_API_KEY`
- `SERPAPI_KEY`

레포 Settings → Secrets → Actions에서 설정

## fetch_utils.py 기능

### API 헬퍼

```python
# 자동 retry + exponential backoff
fetch_with_retry(url, params, max_retries=3, base_delay=2.0)

# CoinGecko (12초 rate limiting 자동)
get_coingecko_price(["bitcoin", "ethereum"])
get_coingecko_market_data(["bitcoin"])
get_coingecko_historical("bitcoin", days=365)

# Binance
get_binance_price("BTCUSDT")
get_binance_prices(["BTCUSDT", "ETHUSDT"])

# DefiLlama
get_defillama_tvl("aave")
get_defillama_fees()
get_defillama_yields()

# data.go.kr (이중 인코딩 방지)
build_data_go_kr_url(base_url, api_key, params)
```

### 포맷팅

```python
format_number(1234567.89)      # "1,234,567.89"
format_korean_number(123456789) # "1.23억"
format_usd(1234567)            # "$1,234,567"
format_percent(0.1234)         # "+12.34%"
```

### 시간

```python
get_kst_timestamp()  # "2024-01-15 07:00:00 KST"
get_kst_date()       # "2024-01-15"
```

### 파일

```python
save_json(data, "data/output.json")  # 폴더 자동 생성
load_json("data/output.json", default={})
ensure_data_dir("data")
```

## 마이그레이션 체크리스트

기존 대시보드를 이 워크플로우로 전환할 때:

- [ ] `.github/workflows/update.yml` 교체
- [ ] (선택) `fetch_utils.py` 복사해서 공통 패턴 활용
- [ ] Actions 탭에서 수동 실행 테스트
- [ ] 시크릿 설정 확인

## 폴더 구조

```
shared-workflows/
├── .github/workflows/
│   └── python-fetch.yml    # 재사용 가능한 워크플로우
├── fetch_utils.py          # Python 유틸리티
├── examples/
│   └── dashboard-workflow.yml  # 사용 예시
└── README.md
```
