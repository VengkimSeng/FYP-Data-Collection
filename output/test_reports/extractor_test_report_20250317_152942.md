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
| Import test | ✅ Pass | 0.00s |  |
| Generic scraper test | ✅ Pass | 2.01s |  |
| Checkpoint mechanism | ✅ Pass | 0.00s |  |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 2.86s |  |
| Process URL | ✅ Pass | 0.00s |  |
| Output directory functions | ✅ Pass | 0.00s |  |
| Save article data | ✅ Pass | 0.00s |  |
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
| End-to-end extraction | ✅ Pass | 114.64s |  |
| Main module | ✅ Pass | 0.08s |  |

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
| DapNews scraper | ❌ Error | 0.00s | invalid literal for int() with base 10: 'title' |
| DapNews scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Fail | 31.74s | 'Error retrieving title' != 'Test RFA Article'
- Error retrieving title
+ Test RFA Article
 |
| RFA scraper | ❌ Fail | 0.00s | 'rfa_scraper' != <function scrape_rfa at 0x7f2939ba96c0> |

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

Report generated at: 2025-03-17 15:29:42
