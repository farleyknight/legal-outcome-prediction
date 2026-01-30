# CourtListener API Specification

## Overview
- Base URL: `https://www.courtlistener.com/api/rest/v4/`
- Authentication: API token (free tier available)
- Rate limit: 1 request per second (enforced client-side)
- Documentation: https://www.courtlistener.com/help/api/rest/

## Authentication

### Getting an API Token
1. Create account at https://www.courtlistener.com/register/
2. Go to https://www.courtlistener.com/profile/api/
3. Copy API token

### Using the Token
```
Authorization: Token <your_api_token>
```

Store token in environment variable:
```bash
export COURTLISTENER_API_TOKEN="your_token_here"
```

---

## Endpoints

### 1. Search Dockets

Find dockets by court and docket number.

**Endpoint**: `GET /dockets/`

**Query Parameters**:
| Parameter | Description | Example |
|-----------|-------------|---------|
| `court` | Court abbreviation | `nysd` |
| `docket_number` | Docket number pattern | `2019cv01234` |
| `fields` | Comma-separated field list | `id,docket_number,date_filed` |

**Example Request**:
```
GET /api/rest/v4/dockets/?court=nysd&docket_number=2019cv01234
```

**Example Response**:
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 12345678,
      "resource_uri": "https://www.courtlistener.com/api/rest/v4/dockets/12345678/",
      "court": "https://www.courtlistener.com/api/rest/v4/courts/nysd/",
      "docket_number": "1:19-cv-01234",
      "date_filed": "2019-03-15",
      "date_terminated": "2021-06-22"
    }
  ]
}
```

---

### 2. Get Docket Entries

Retrieve all entries for a specific docket.

**Endpoint**: `GET /docket-entries/`

**Query Parameters**:
| Parameter | Description | Example |
|-----------|-------------|---------|
| `docket` | Docket ID | `12345678` |
| `order_by` | Sort order | `entry_number` |

**Example Request**:
```
GET /api/rest/v4/docket-entries/?docket=12345678&order_by=entry_number
```

**Example Response**:
```json
{
  "count": 45,
  "next": "https://www.courtlistener.com/api/rest/v4/docket-entries/?docket=12345678&page=2",
  "previous": null,
  "results": [
    {
      "id": 987654321,
      "docket": "https://www.courtlistener.com/api/rest/v4/dockets/12345678/",
      "entry_number": 1,
      "date_filed": "2019-03-15",
      "description": "COMPLAINT against ABC Corp. Filing fee $ 400, receipt number ANYDC-1234567. (Attachments: # 1 Exhibit A, # 2 Civil Cover Sheet)(Smith, John)"
    },
    {
      "id": 987654322,
      "docket": "https://www.courtlistener.com/api/rest/v4/dockets/12345678/",
      "entry_number": 2,
      "date_filed": "2019-03-20",
      "description": "SUMMONS Issued as to ABC Corp."
    }
  ]
}
```

---

## Pagination

API returns paginated results (default 20 per page).

**Handling Pagination**:
```python
def fetch_all_entries(docket_id):
    entries = []
    url = f"{BASE_URL}/docket-entries/?docket={docket_id}&order_by=entry_number"

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        entries.extend(data["results"])
        url = data["next"]  # None when no more pages
        time.sleep(1)  # Rate limiting

    return entries
```

---

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 401 | Unauthorized | Check API token |
| 404 | Not found | Case not in RECAP |
| 429 | Rate limited | Back off, retry after delay |
| 500 | Server error | Retry with exponential backoff |

---

## Caching Strategy

Cache responses to `data/cache/` to avoid re-fetching:

```
data/cache/
├── dockets/
│   └── nysd_2019cv01234.json
└── entries/
    └── 12345678.json
```

**Cache Key Format**:
- Docket search: `{court}_{docket_number}.json`
- Docket entries: `{docket_id}.json`

**Cache Policy**:
- Check cache before API call
- Never expire (FJC cases are historical)
- Store raw API response JSON

---

## Docket Number Formatting

FJC and CourtListener use different formats:

| Source | Format | Example |
|--------|--------|---------|
| FJC IDB | YYDDDDD or YYYYDDDDD | 191234 or 20191234 |
| CourtListener | Various | 1:19-cv-01234, 19-cv-1234 |

**Matching Strategy**:
1. Extract year and sequence from FJC format
2. Search CourtListener with pattern: `{year}cv{sequence}`
3. If no match, try variations: `{year}-cv-{sequence}`, `1:{year}-cv-{sequence}`
4. Match on date_filed as secondary confirmation
