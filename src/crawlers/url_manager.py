import os
import json
import time
import logging
import threading
from typing import Dict, Set, List, Iterable, Any
from urllib.parse import urlparse
import random

logger = logging.getLogger(__name__)

class URLManager:
    def __init__(self, output_dir: str, crawler_name: str, urls_per_category: int = 0, auto_save: bool = True, save_interval: int = 60):
        # Store the base output directory for all categories
        self.output_dir = output_dir
        self.crawler_name = crawler_name
        self.urls_per_category = urls_per_category
        
        # Create temp dir with crawler name for isolation
        self.temp_dir = os.path.join(output_dir, "temp", f"{int(time.time())}_{crawler_name}")
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        # Rest of initialization
        self.lock = threading.RLock()
        self.category_urls: Dict[str, Set[str]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.progress: Dict[str, Dict[str, Any]] = {}
        self._stop_auto_save = threading.Event()
        self._auto_save_thread = None
        if auto_save:
            self._start_auto_save(save_interval)
        logger.info(f"URL Manager initialized for {crawler_name} (output: {output_dir})")

    def __del__(self):
        self.stop()

    def stop(self):
        if not self._stop_auto_save.is_set():
            self._stop_auto_save.set()
            if self._auto_save_thread and self._auto_save_thread.is_alive():
                self._auto_save_thread.join(timeout=5)
            self.save_final_results()

    def _start_auto_save(self, interval: int):
        self._auto_save_thread = threading.Thread(target=self._auto_save_worker, args=(interval,), daemon=True)
        self._auto_save_thread.start()

    def _auto_save_worker(self, interval: int):
        while not self._stop_auto_save.is_set():
            time.sleep(interval)
            if not self._stop_auto_save.is_set():
                try:
                    self.save_intermediate_results()
                except Exception as e:
                    logger.error(f"Error in auto-save: {e}")

    def add_urls(self, category: str, urls: Iterable[str]) -> int:
        with self.lock:
            if category not in self.category_urls:
                self.category_urls[category] = set()
            original_count = len(self.category_urls[category])
            self.category_urls[category].update(urls)
            new_count = len(self.category_urls[category])
            if category not in self.progress:
                self.progress[category] = {"total": 0, "last_update": time.time(), "sources_processed": 0}
            self.progress[category]["total"] = new_count
            self.progress[category]["last_update"] = time.time()
            self.progress[category]["sources_processed"] += 1
            return new_count - original_count

    def add_urls_with_metadata(self, category: str, url_data: Dict[str, Any]) -> int:
        with self.lock:
            if category not in self.metadata:
                self.metadata[category] = {}
            urls = set(url_data.keys())
            added = self.add_urls(category, urls)
            self.metadata[category].update(url_data)
            return added

    def save_intermediate_results(self) -> None:
        with self.lock:
            for category in self.category_urls:
                temp_file = os.path.join(self.temp_dir, f"{category}_urls.json")
                urls = list(self.category_urls[category])
                self._save_urls_to_file(urls, temp_file)
            progress_file = os.path.join(self.temp_dir, "progress.json")
            try:
                with open(progress_file, "w", encoding="utf-8") as f:
                    json.dump(self.progress, f, ensure_ascii=False, indent=4)
            except Exception as e:
                logger.error(f"Error saving progress: {e}")
            logger.info(f"Saved intermediate results for {len(self.category_urls)} categories")

    def save_final_results(self) -> Dict[str, int]:
        results = {}
        with self.lock:
            for category, urls in self.category_urls.items():
                # Save directly to category.json in the output directory
                output_file = os.path.join(self.output_dir, f"{category}.json")
                
                # Load any existing URLs from the category file
                existing_urls = set()
                if os.path.exists(output_file):
                    existing_urls = set(self._load_urls_from_file(output_file))
                
                # Merge new URLs with existing ones
                final_urls = existing_urls.union(urls)
                
                # Apply URL limit if configured
                if self.urls_per_category > 0 and len(final_urls) > self.urls_per_category:
                    final_urls = set(random.sample(list(final_urls), self.urls_per_category))
                
                # Save to file based on format (metadata or simple list)
                if category in self.metadata:
                    self._save_urls_with_metadata(category, final_urls, output_file)
                else:
                    self._save_urls_to_file(final_urls, output_file)
                
                results[category] = len(final_urls)
                logger.info(f"Saved {len(final_urls)} URLs for category '{category}' to {output_file}")
        
        return results

    def _save_urls_to_file(self, urls: Iterable[str], file_path: str, format_type: str = "json", ensure_ascii: bool = False, indent: int = 4) -> bool:
        try:
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            urls_list = sorted(list(set(urls)))
            if format_type.lower() == "json":
                temp_file = f"{file_path}.temp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(urls_list, f, ensure_ascii=ensure_ascii, indent=indent)
                os.replace(temp_file, file_path)
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    for url in urls_list:
                        f.write(f"{url}\n")
            return True
        except Exception as e:
            logger.error(f"Error saving URLs to {file_path}: {e}")
            return False

    def _save_urls_with_metadata(self, category: str, urls: Iterable[str], file_path: str) -> bool:
        try:
            urls_with_metadata = {}
            for url in urls:
                if url in self.metadata[category]:
                    urls_with_metadata[url] = self.metadata[category][url]
                else:
                    urls_with_metadata[url] = {"url": url, "category": category}
            temp_file = f"{file_path}.temp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(urls_with_metadata, f, ensure_ascii=False, indent=4)
            os.replace(temp_file, file_path)
            return True
        except Exception as e:
            logger.error(f"Error saving URLs with metadata to {file_path}: {e}")
            return False

    def _load_urls_from_file(self, file_path: str) -> List[str]:
        try:
            if not os.path.exists(file_path):
                return []
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if isinstance(content, list):
                        return content
                    elif isinstance(content, dict):
                        return list(content.keys())
                    else:
                        logger.warning(f"Unexpected JSON format in {file_path}")
                        return []
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.error(f"Error loading URLs from {file_path}: {e}")
            return []
