#!/usr/bin/env python3
"""Best-effort free Korean translation; no private API keys, no manufactured translations.
Uses an unofficial public translation interface via deep-translator. Availability is not guaranteed.
"""
import json
import time
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "site" / "data" / "tracker.json"

def translate_inplace(doc, translate):
    updated = failed = reused = 0
    cache = {}
    for row in doc.get("stocks", []):
        en = str(row.get("summary_en") or "").strip()
        if not en:
            row.pop("summary_ko", None)
            continue
        if row.get("summary_ko"):
            cache[en] = row["summary_ko"]
            reused += 1
            continue
        if en in cache:
            row["summary_ko"] = cache[en]
            reused += 1
            continue
        try:
            ko = str(translate(en) or "").strip()
            # Never mislabel an untranslated English sentence as Korean.
            if not ko or not any("가" <= ch <= "힣" for ch in ko):
                raise ValueError("no Korean script returned")
            row["summary_ko"] = ko
            cache[en] = ko
            updated += 1
        except Exception as exc:
            failed += 1
            print(f"Translation unavailable for {row.get('ticker', '?')}: {type(exc).__name__}: {str(exc)[:120]}")
        time.sleep(0.35)
    return updated, reused, failed

def main():
    if not FILE.exists():
        raise SystemExit("No tracker.json yet")
    doc = json.loads(FILE.read_text(encoding="utf-8"))
    try:
        from deep_translator import GoogleTranslator
        service = GoogleTranslator(source="en", target="ko")
        result = translate_inplace(doc, service.translate)
    except ImportError as exc:
        raise SystemExit(f"Translation dependency unavailable: {exc}")
    FILE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Korean summary translation: %d new; %d cached; %d unavailable" % result)

if __name__ == "__main__":
    main()
