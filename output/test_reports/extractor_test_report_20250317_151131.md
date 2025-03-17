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
| Checkpoint mechanism | ❌ Fail | 0.00s | 1 != 3 |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 3.20s |  |
| Process URL | ✅ Pass | 0.00s |  |
| Output directory functions | ✅ Pass | 0.00s |  |
| Save article data | ✅ Pass | 0.02s |  |
| Adapter calls specific scraper | ✅ Pass | 0.00s |  |
| Adapter fallback to generic | ✅ Pass | 0.00s |  |
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
| End-to-end extraction | ✅ Pass | 114.82s |  |
| Main module | ✅ Pass | 0.14s |  |

---

### Site-Specific Scrapers

Success Rate: 50.0% (6/12)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| BTV scraper | ❌ Error | 0.00s | '<' not supported between instances of 'int' and 'str' |
| BTV scraper | ✅ Pass | 0.00s |  |
| PostKhmer scraper | ❌ Error | 0.00s | '<' not supported between instances of 'int' and 'str' |
| PostKhmer scraper | ✅ Pass | 0.00s |  |
| Kohsantepheap scraper | ❌ Error | 0.00s | '<' not supported between instances of 'int' and 'str' |
| Kohsantepheap scraper | ✅ Pass | 0.00s |  |
| DapNews scraper | ❌ Error | 0.00s | generic_scrape() got an unexpected keyword argument 'is_id' |
| DapNews scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ✅ Pass | 0.01s |  |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Fail | 31.78s | unexpectedly None |
| RFA scraper | ❌ Fail | 0.00s | 'rfa_scraper' != <function scrape_rfa at 0x7fbb62ba16c0> |

---

## Error Summary

The following key issues need to be addressed:

1. **Error 1:** '<' not supported between instances of 'int' and 'str'
2. **Error 2:** 1 != 3
3. **Error 3:** generic_scrape() got an unexpected keyword argument 'is_id'
4. **Error 4:** unexpectedly None
5. **Error 5:** 'rfa_scraper' != <function scrape_rfa at 0x7fbb62ba16c0>

Report generated at: 2025-03-17 15:11:31
