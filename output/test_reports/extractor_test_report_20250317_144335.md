# Extractor Test Report

## Summary

- **Total Tests:** 32
- **Passed:** 23
- **Failed:** 2
- **Errors:** 7

**Success Rate:** 71.9%

```
[==============      ]
```

## Detailed Results

### Common Components

Success Rate: 88.9% (16/18)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import test | ✅ Pass | 0.00s |  |
| Generic scraper test | ❌ Error | 4.01s | log_category_progress() got an unexpected keyword argument 'is_end' |
| Checkpoint mechanism | ❌ Fail | 0.00s | 1 != 3 |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 2.95s |  |
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

Success Rate: 50.0% (1/2)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| End-to-end extraction | ❌ Error | 4.65s | name 'datetime' is not defined |
| Main module | ✅ Pass | 0.10s |  |

---

### Site-Specific Scrapers

Success Rate: 50.0% (6/12)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| BTV scraper | ❌ Error | 4.01s | log_category_progress() got an unexpected keyword argument 'is_end' |
| BTV scraper | ✅ Pass | 0.00s |  |
| PostKhmer scraper | ❌ Error | 4.01s | log_category_progress() got an unexpected keyword argument 'is_end' |
| PostKhmer scraper | ✅ Pass | 0.00s |  |
| Kohsantepheap scraper | ❌ Error | 4.01s | log_category_progress() got an unexpected keyword argument 'is_end' |
| Kohsantepheap scraper | ✅ Pass | 0.00s |  |
| DapNews scraper | ❌ Error | 4.01s | log_category_progress() got an unexpected keyword argument 'is_end' |
| DapNews scraper | ✅ Pass | 0.00s |  |
| Sabay scraper | ❌ Fail | 0.01s | Calls not found.
Expected: [call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call(<MagicMock name='create_driver()' id='140680610919712'>, 30)]
Actual: [call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call().until(<function presence_of_element_located.<locals>._predicate at 0x7ff2c1de93f0>),
 call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call().until(<function presence_of_element_located.<locals>._predicate at 0x7ff2c1de9480>)] |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Error | 0.00s | module 'src.extractors.scrapers.rfa_scraper' has no attribute 'extract_article' |
| RFA scraper | ✅ Pass | 0.00s |  |

---

## Error Summary

The following key issues need to be addressed:

1. **Error 1:** log_category_progress() got an unexpected keyword argument 'is_end'
2. **Error 2:** 1 != 3
3. **Error 3:** name 'datetime' is not defined
4. **Error 4:** Calls not found.
Expected: [call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call(<MagicMock name='create_driver()' id='140680610919712'>, 30)]
Actual: [call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call().until(<function presence_of_element_located.<locals>._predicate at 0x7ff2c1de93f0>),
 call(<MagicMock name='create_driver()' id='140680610919712'>, 30),
 call().until(<function presence_of_element_located.<locals>._predicate at 0x7ff2c1de9480>)]
5. **Error 5:** module 'src.extractors.scrapers.rfa_scraper' has no attribute 'extract_article'

Report generated at: 2025-03-17 14:43:35
