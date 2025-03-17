# Extractor Test Report

## Summary

- **Total Tests:** 32
- **Passed:** 24
- **Failed:** 3
- **Errors:** 5

**Success Rate:** 75.0%

```
[===============     ]
```

## Detailed Results

### Common Components

Success Rate: 88.9% (16/18)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import test | ✅ Pass | 0.01s |  |
| Generic scraper test | ❌ Error | 4.02s | log_category_progress() missing 2 required positional arguments: 'success' and 'errors' |
| Checkpoint mechanism | ❌ Fail | 0.00s | 1 != 3 |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 2.94s |  |
| Process URL | ✅ Pass | 0.00s |  |
| Output directory functions | ✅ Pass | 0.00s |  |
| Save article data | ✅ Pass | 0.00s |  |
| Adapter calls specific scraper | ✅ Pass | 0.00s |  |
| Adapter fallback to generic | ✅ Pass | 0.00s |  |
| Create extractor for domain | ✅ Pass | 0.00s |  |
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
| End-to-end extraction | ✅ Pass | 5.00s |  |
| Main module | ✅ Pass | 0.10s |  |

---

### Site-Specific Scrapers

Success Rate: 50.0% (6/12)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| BTV scraper | ❌ Error | 4.01s | log_category_progress() missing 2 required positional arguments: 'success' and 'errors' |
| BTV scraper | ✅ Pass | 0.00s |  |
| PostKhmer scraper | ❌ Error | 4.01s | log_category_progress() missing 2 required positional arguments: 'success' and 'errors' |
| PostKhmer scraper | ✅ Pass | 0.00s |  |
| Kohsantepheap scraper | ❌ Error | 4.01s | log_category_progress() missing 2 required positional arguments: 'success' and 'errors' |
| Kohsantepheap scraper | ✅ Pass | 0.00s |  |
| DapNews scraper | ❌ Error | 4.01s | log_category_progress() missing 2 required positional arguments: 'success' and 'errors' |
| DapNews scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.01s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Fail | 32.35s | unexpectedly None |
| RFA scraper | ❌ Fail | 0.00s | 'https://www.rfa.org' not found in {'btv.com.kh': 'btv_scraper', 'www.btv.com.kh': 'btv_scraper', 'postkhmer.com': 'postkhmer_scraper', 'www.postkhmer.com': 'postkhmer_scraper', 'rfa.org': 'rfa_scraper', 'www.rfa.org': 'rfa_scraper', 'dap-news.com': 'dapnews_scraper', 'www.dap-news.com': 'dapnews_scraper', 'news.sabay.com.kh': 'sabay_scraper', 'kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'www.kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'https://btv.com.kh': <function scrape_btv at 0x7f4fab8441f0>, 'https://www.postkhmer.com': <function scrape_postkhmer at 0x7f4fab846680>, 'https://dap-news.com': <function scrape_dapnews at 0x7f4fab846b90>, 'https://news.sabay.com.kh': <function scrape_sabay at 0x7f4fab846ef0>, 'https://kohsantepheapdaily.com.kh': <function scrape_kohsantepheap at 0x7f4fab846dd0>} |

---

## Error Summary

The following key issues need to be addressed:

1. **Error 1:** log_category_progress() missing 2 required positional arguments: 'success' and 'errors'
2. **Error 2:** 1 != 3
3. **Error 3:** unexpectedly None
4. **Error 4:** 'https://www.rfa.org' not found in {'btv.com.kh': 'btv_scraper', 'www.btv.com.kh': 'btv_scraper', 'postkhmer.com': 'postkhmer_scraper', 'www.postkhmer.com': 'postkhmer_scraper', 'rfa.org': 'rfa_scraper', 'www.rfa.org': 'rfa_scraper', 'dap-news.com': 'dapnews_scraper', 'www.dap-news.com': 'dapnews_scraper', 'news.sabay.com.kh': 'sabay_scraper', 'kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'www.kohsantepheapdaily.com.kh': 'kohsantepheap_scraper', 'https://btv.com.kh': <function scrape_btv at 0x7f4fab8441f0>, 'https://www.postkhmer.com': <function scrape_postkhmer at 0x7f4fab846680>, 'https://dap-news.com': <function scrape_dapnews at 0x7f4fab846b90>, 'https://news.sabay.com.kh': <function scrape_sabay at 0x7f4fab846ef0>, 'https://kohsantepheapdaily.com.kh': <function scrape_kohsantepheap at 0x7f4fab846dd0>}

Report generated at: 2025-03-17 14:47:41
