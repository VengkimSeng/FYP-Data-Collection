# Extractor Test Report

## Summary

- **Total Tests:** 31
- **Passed:** 24
- **Failed:** 3
- **Errors:** 4

**Success Rate:** 77.4%

```
[===============     ]
```

## Detailed Results

### Common Components

Success Rate: 94.1% (16/17)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import test | ✅ Pass | 0.01s |  |
| Generic scraper test | ✅ Pass | 2.01s |  |
| Checkpoint mechanism | ✅ Pass | 0.00s |  |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 2.87s |  |
| Process URL | ✅ Pass | 0.00s |  |
| Output directory functions | ✅ Pass | 0.00s |  |
| Save article data | ✅ Pass | 0.02s |  |
| Adapter calls specific scraper | ✅ Pass | 0.00s |  |
| Adapter fallback to generic | ❌ Fail | 0.00s | expected call not found.
Expected: mock('https://unknown.com/article', 'test_category')
Actual: mock('https://unknown.com/article', 'test_category', is_id=None) |
| Close driver | ✅ Pass | 0.00s |  |
| Create driver | ✅ Pass | 0.00s |  |
| Get Chrome options | ✅ Pass | 0.00s |  |
| Log debug | ✅ Pass | 0.00s |  |
| Log error | ✅ Pass | 0.00s |  |
| Log scrape status | ✅ Pass | 0.00s |  |

---

### Integration Tests

Success Rate: 100.0% (2/2)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| End-to-end extraction | ✅ Pass | 114.92s |  |
| Main module | ✅ Pass | 0.13s |  |

---

### Site-Specific Scrapers

Success Rate: 50.0% (6/12)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| BTV scraper | ❌ Error | 0.00s | invalid literal for int() with base 10: 'h4.color' |
| BTV scraper | ✅ Pass | 0.00s |  |
| PostKhmer scraper | ❌ Error | 0.00s | invalid literal for int() with base 10: 'div.section-article-header h2' |
| PostKhmer scraper | ✅ Pass | 0.00s |  |
| Kohsantepheap scraper | ❌ Error | 0.00s | invalid literal for int() with base 10: 'div.article-recap h1' |
| Kohsantepheap scraper | ✅ Pass | 0.00s |  |
| DapNews scraper | ❌ Error | 0.01s | invalid literal for int() with base 10: 'title' |
| DapNews scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Fail | 32.94s | unexpectedly None |
| RFA scraper | ❌ Fail | 0.00s | 'https://www.rfa.org' not found in {'btv.com.kh': 'btv_scraper', 'www.btv.com.kh': 'btv_scraper', 'postkhmer.com': 'postkhmer_scraper', 'www.postkhmer.com': 'postkhmer_scraper', 'rfa.org': 'rfa_scraper', 'www.rfa.org': 'rfa_scraper', 'dap-news.com': 'dapnews_scraper', 'www.dap-news.com': 'dapnews_scraper', 'news.sabay.com.kh': 'sabay_scraper', 'kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'www.kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'https://btv.com.kh': <function scrape_btv at 0x7f0af9f411b0>, 'https://www.postkhmer.com': <function scrape_postkhmer at 0x7f0af9f41360>, 'https://dap-news.com': <function scrape_dapnews at 0x7f0af9f41900>, 'https://news.sabay.com.kh': <function scrape_sabay at 0x7f0af9f42290>, 'https://kohsantepheapdaily.com.kh': <function scrape_kohsantepheap at 0x7f0af9f41b40>} |

---

## Error Summary

The following key issues need to be addressed:

1. **Error 1:** expected call not found.
Expected: mock('https://unknown.com/article', 'test_category')
Actual: mock('https://unknown.com/article', 'test_category', is_id=None)
2. **Error 2:** invalid literal for int() with base 10: 'h4.color'
3. **Error 3:** invalid literal for int() with base 10: 'div.section-article-header h2'
4. **Error 4:** invalid literal for int() with base 10: 'div.article-recap h1'
5. **Error 5:** invalid literal for int() with base 10: 'title'

Report generated at: 2025-03-17 15:17:48
