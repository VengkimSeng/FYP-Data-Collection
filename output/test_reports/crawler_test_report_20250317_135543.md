# Crawler Test Report

## Summary

- **Total Tests:** 37
- **Passed:** 31
- **Failed:** 6

**Success Rate:** 83.8%

```
[================>   ]
```

## Detailed Results

### Master Controller

Success Rate: 100.0% (1/1)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Master controller test | ✅ Pass | 0.12s | Successfully initialized controller with 6 crawlers |

---

### Kohsantepheapdaily - sport

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import kohsantepheapdaily module | ✅ Pass | 0.00s | Successfully imported kohsantepheapdaily crawler module |
| Required function 'crawl_category' in kohsantepheapdaily | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for kohsantepheapdaily - sport | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for kohsantepheapdaily | ✅ Pass | 0.00s | URL filtering works: 5 → 2 |
| Minimal crawl test for kohsantepheapdaily - sport | ✅ Pass | 41.98s | Successfully crawled 86 URLs |
| URL saving test for kohsantepheapdaily - sport | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for kohsantepheapdaily - sport**

- Error: No URLs added: 0

---

### Btv - sport

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import btv module | ✅ Pass | 0.00s | Successfully imported btv crawler module |
| Required function 'crawl_category' in btv | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for btv - sport | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for btv | ✅ Pass | 0.00s | URL filtering works: 5 → 2 |
| Minimal crawl test for btv - sport | ✅ Pass | 7.24s | Successfully crawled 20 URLs |
| URL saving test for btv - sport | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for btv - sport**

- Error: No URLs added: 0

---

### Rfanews - health

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import rfanews module | ✅ Pass | 0.00s | Successfully imported rfanews crawler module |
| Required function 'crawl_category' in rfanews | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for rfanews - health | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for rfanews | ✅ Pass | 0.00s | URL filtering works: 5 → 2 |
| Minimal crawl test for rfanews - health | ✅ Pass | 19.82s | Successfully crawled 8 URLs |
| URL saving test for rfanews - health | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for rfanews - health**

- Error: No URLs added: 0

---

### Dapnews - sport

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import dapnews module | ✅ Pass | 0.00s | Successfully imported dapnews crawler module |
| Required function 'crawl_category' in dapnews | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for dapnews - sport | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for dapnews | ✅ Pass | 0.00s | URL filtering works correctly: 6 → 2 |
| Minimal crawl test for dapnews - sport | ✅ Pass | 8.29s | Successfully crawled 8 URLs |
| URL saving test for dapnews - sport | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for dapnews - sport**

- Error: No URLs added: 0

---

### Sabaynews - sport

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import sabaynews module | ✅ Pass | 0.00s | Successfully imported sabaynews crawler module |
| Required function 'crawl_category' in sabaynews | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for sabaynews - sport | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for sabaynews | ✅ Pass | 0.00s | URL filtering works: 5 → 2 |
| Minimal crawl test for sabaynews - sport | ✅ Pass | 6.38s | Successfully crawled 3 URLs |
| URL saving test for sabaynews - sport | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for sabaynews - sport**

- Error: No URLs added: 0

---

### Postkhmer - sport

Success Rate: 83.3% (5/6)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import postkhmer module | ✅ Pass | 0.00s | Successfully imported postkhmer crawler module |
| Required function 'crawl_category' in postkhmer | ✅ Pass | 0.00s | Found crawl_category function with correct signature |
| Source URLs for postkhmer - sport | ✅ Pass | 0.00s | Found 1 source URLs |
| URL filtering test for postkhmer | ✅ Pass | 0.00s | URL filtering works: 5 → 3 |
| Minimal crawl test for postkhmer - sport | ✅ Pass | 21.48s | Successfully crawled 10 URLs |
| URL saving test for postkhmer - sport | ❌ Fail | 0.01s | Failed to add URLs to saver |

#### Error Details

**URL saving test for postkhmer - sport**

- Error: No URLs added: 0

---



Report generated at: 2025-03-17 13:55:43
