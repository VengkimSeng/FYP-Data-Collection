# Extractor Test Report

## Summary

- **Total Tests:** 32
- **Passed:** 14
- **Failed:** 1
- **Errors:** 17

**Success Rate:** 43.8%

```
[========            ]
```

## Detailed Results

### Common Components

Success Rate: 66.7% (12/18)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| Import test | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Generic scraper test | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Checkpoint mechanism | ❌ Fail | 0.00s | 1 != 3 |
| test_is_scraped | ✅ Pass | 0.00s |  |
| Extract domain | ✅ Pass | 0.00s |  |
| Process file | ✅ Pass | 2.78s |  |
| Process URL | ✅ Pass | 0.00s |  |
| Output directory functions | ✅ Pass | 0.00s |  |
| Save article data | ✅ Pass | 0.00s |  |
| Adapter calls specific scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Adapter fallback to generic | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Create extractor for domain | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
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
| End-to-end extraction | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Main module | ✅ Pass | 0.07s |  |

---

### Site-Specific Scrapers

Success Rate: 8.3% (1/12)

| Test | Result | Duration | Message |
|------|--------|----------|--------|
| BTV scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| BTV scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| PostKhmer scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| PostKhmer scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Kohsantepheap scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Kohsantepheap scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| DapNews scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| DapNews scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Sabay scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| Sabay scraper | ✅ Pass | 0.00s |  |
| RFA scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |
| RFA scraper | ❌ Error | 0.00s | cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py) |

---

## Error Summary

The following key issues need to be addressed:

1. **Error 1:** cannot import name 'generic_scrape' from 'src.extractors.scrapers.generic_scraper' (/home/root/FYP-Data-Collection/FYP-Data-Collection/src/extractors/scrapers/generic_scraper.py)
2. **Error 2:** 1 != 3

Report generated at: 2025-03-17 14:51:57
