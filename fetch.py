import json
import pathlib
import re
import requests
from bs4 import BeautifulSoup

OBJECT_ID = 329076
OUTDIR = pathlib.Path("output")
OUTDIR.mkdir(exist_ok=True, parents=True)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
}

def dump(obj, path):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

summary = {"object_id": OBJECT_ID}

# 1) Official object API
obj_url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{OBJECT_ID}"
try:
    r = requests.get(obj_url, timeout=60, headers=COMMON_HEADERS)
    summary["object_api_status"] = r.status_code
    summary["object_api_url"] = obj_url
    try:
        data = r.json()
        dump({"status_code": r.status_code, "json": data}, OUTDIR / "object_api_329076.json")
        summary["object_api_json_ok"] = True
        if isinstance(data, dict):
            summary["department"] = data.get("department")
            summary["title"] = data.get("title")
            summary["medium"] = data.get("medium")
            summary["objectName"] = data.get("objectName")
            summary["culture"] = data.get("culture")
            summary["objectDate"] = data.get("objectDate")
            summary["accessionNumber"] = data.get("accessionNumber")
            summary["objectURL"] = data.get("objectURL")
    except Exception:
        dump({"status_code": r.status_code, "text": r.text[:20000]}, OUTDIR / "object_api_329076.json")
        summary["object_api_json_ok"] = False
except Exception as e:
    summary["object_api_error"] = repr(e)

# 2) Official search API
search_url = "https://collectionapi.metmuseum.org/public/collection/v1/search"
search_params = {"q": "bird", "departmentId": 3}
try:
    r = requests.get(search_url, params=search_params, timeout=60, headers=COMMON_HEADERS)
    summary["search_api_status"] = r.status_code
    try:
        data = r.json()
        dump({"status_code": r.status_code, "params": search_params, "json": data}, OUTDIR / "search_api_bird_department3.json")
        summary["search_api_json_ok"] = True
    except Exception:
        dump({"status_code": r.status_code, "params": search_params, "text": r.text[:20000]}, OUTDIR / "search_api_bird_department3.json")
        summary["search_api_json_ok"] = False
except Exception as e:
    summary["search_api_error"] = repr(e)

# 3) Met object webpage HTML
page_url = f"https://www.metmuseum.org/art/collection/search/{OBJECT_ID}"
try:
    r = requests.get(page_url, timeout=60, headers=COMMON_HEADERS)
    summary["object_page_status"] = r.status_code
    html = r.text
    (OUTDIR / "object_page_329076.html").write_text(html, encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    page_summary = {}
    title_tag = soup.find("title")
    if title_tag:
        page_summary["html_title"] = title_tag.get_text(" ", strip=True)
    # Look for JSON-LD
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        if isinstance(data, dict):
            page_summary.setdefault("json_ld", []).append(data)
    # find medium in visible text sections
    text = soup.get_text("\n", strip=True)
    m = re.search(r"\bMedium:\s*(.+)", text)
    if m:
        page_summary["medium_line"] = m.group(1)[:500]
    # generic key-value parsing around labels
    labels = ["Medium", "Department", "Title", "Object Name", "Culture", "Date"]
    for label in labels:
        # Try patterns like 'Label\nValue'
        m = re.search(rf"{re.escape(label)}\s*\n\s*([^\n][^\n]{{0,300}})", text)
        if m:
            page_summary[label] = m.group(1).strip()
    dump(page_summary, OUTDIR / "object_page_summary_329076.json")
    if "medium" not in summary:
        if page_summary.get("Medium"):
            summary["medium"] = page_summary["Medium"]
        elif page_summary.get("medium_line"):
            summary["medium"] = page_summary["medium_line"]
    if "department" not in summary and page_summary.get("Department"):
        summary["department"] = page_summary["Department"]
    if "title" not in summary and page_summary.get("Title"):
        summary["title"] = page_summary["Title"]
except Exception as e:
    summary["object_page_error"] = repr(e)

# 4) Met collection listing API with query bird
listing_url = "https://www.metmuseum.org/api/collection/collectionlisting"
listing_params = {
    "artist": "",
    "department": "Ancient Near Eastern Art",
    "era": "",
    "geolocation": "",
    "material": "",
    "offset": 0,
    "pageSize": 0,
    "perPage": 100,
    "q": "bird",
    "showOnly": "",
    "sortBy": "Relevance",
    "sortOrder": "asc",
}
try:
    r = requests.get(listing_url, params=listing_params, timeout=60, headers=COMMON_HEADERS)
    summary["collectionlisting_status"] = r.status_code
    try:
        data = r.json()
        dump({"status_code": r.status_code, "params": listing_params, "json": data}, OUTDIR / "collectionlisting_bird_aneart.json")
        summary["collectionlisting_json_ok"] = True
        # try find result by id in url
        results = data.get("results") or []
        for item in results:
            url = item.get("url","")
            if str(OBJECT_ID) in url:
                summary["listing_match"] = {
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "date": item.get("date"),
                    "medium": item.get("medium"),
                    "accessionNumber": item.get("accessionNumber"),
                    "url": url,
                }
                summary.setdefault("title", item.get("title"))
                summary.setdefault("medium", item.get("medium"))
                break
    except Exception:
        dump({"status_code": r.status_code, "params": listing_params, "text": r.text[:50000]}, OUTDIR / "collectionlisting_bird_aneart.json")
        summary["collectionlisting_json_ok"] = False
except Exception as e:
    summary["collectionlisting_error"] = repr(e)

dump(summary, OUTDIR / "summary_329076.json")
(OUTDIR / "summary_329076.txt").write_text(
    "\n".join(f"{k}: {v}" for k, v in summary.items()),
    encoding="utf-8"
)
print(json.dumps(summary, ensure_ascii=False, indent=2))