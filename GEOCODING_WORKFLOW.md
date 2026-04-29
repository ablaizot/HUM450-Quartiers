# Geocoding Workflow: Historical Lausanne Addresses

This document describes the complete workflow for converting historical directory addresses into geocoded map data.

## Overview

The process consists of three main steps:

1. **Sanitize** addresses for Nominatim geocoding (OCR-extracted text → clean addresses)
2. **Geocode** addresses to get latitude/longitude coordinates (Nominatim API)
3. **Export** to GeoJSON for mapping (ready for QGIS, Leaflet, web maps)

## Step 1: Address Sanitization (`SanitiseForNominatim.py`)

### What it does
Cleans historical addresses extracted from directories using an OCR-aware approach:
- Uses **sheet names** as official street names (manually verified, robust to OCR errors)
- **Extracts house numbers** from OCR text (patterns: "123", "123bis", "n°123", etc.)
- Combines them with Lausanne city context for geocoding

### Why this approach?
- OCR text is often corrupted with stuck-together words
- Sheet names are manually selected, so highly reliable
- This avoids trying to parse OCR-corrupted street names
- Still captures house numbers when present

### Input/Output
- **Input Column**: D (OCR-extracted address text)
- **Input**: Sheet names (manually curated street/location names)
- **Output Column**: S (Clean address ready for Nominatim)

### Example transformations
```
Sheet: "Rue de la Paix"  |  OCR: "niedelaPaix 42"      → "42 Rue de la Paix, Lausanne, Switzerland"
Sheet: "La Pontaise"     |  OCR: "ruede la Pontaise 18" → "18 La Pontaise, Lausanne, Switzerland"
Sheet: "Avenue Druey"    |  OCR: "à l'Avenue Druey"      → "Avenue Druey, Lausanne, Switzerland"
```

### Run it
```bash
python SanitiseForNominatim.py
```

Status: ✅ **COMPLETE** (4,256 addresses sanitized across 13 Excel files)

---

## Step 2: Nominatim Geocoding (`GeocodeWithNominatim.py`)

### What it does
Uses Nominatim (OpenStreetMap's free geocoding service) to convert sanitized addresses to coordinates.

The sanitized addresses in column S are now clean, reliable, and ready for geocoding:
- Format: `"42 Rue de la Paix, Lausanne, Switzerland"` or `"Avenue Druey, Lausanne, Switzerland"`
- All OCR-corrupted text has been removed
- House numbers are properly extracted
- City context is included

### Important Notes
- **Rate limiting**: 1.5 seconds between requests (respects Nominatim usage policy)
- **Depends on**: Step 1 (sanitized addresses in column S)
- **Processing time**: ~4,000+ addresses will take ~2-3 hours
- **Results cached**: Re-running skips already-geocoded addresses

### Input/Output
- **Input Column**: S (Sanitized addresses)
- **Output Columns**: 
  - T = Latitude
  - U = Longitude

### Nominatim Details
- Service: https://nominatim.openstreetmap.org
- Returns results rounded to 6 decimal places (~0.11m precision)
- Caches results to avoid duplicate API calls

### Run it
```bash
python GeocodeWithNominatim.py
```

**Note**: This will take several hours for all files. Consider running overnight or on a subset first to test.

---

## Step 3: Export to GeoJSON (`ExportToGeoJSON.py`)

### What it does
Converts the geocoded Excel data to GeoJSON format for mapping.

### Input/Output
- **Input Columns**: S (address), T (latitude), U (longitude)
- **Output**: GeoJSON files in `GeoJSON_Output/` folder
- **File format**: One .geojson file per Excel file

### Example GeoJSON structure
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [6.633, 46.519]
      },
      "properties": {
        "address": "Rue de la Paix",
        "year": 1885,
        "name": "Acacia"
      }
    }
  ]
}
```

### Run it
```bash
python ExportToGeoJSON.py
```

---

## Mapping Tools

### QGIS (Desktop)
1. Open QGIS
2. Layer > Add Layer > Add Vector Layer
3. Select `.geojson` file from `GeoJSON_Output/`
4. Style by year or neighborhood

### Online Viewers
- **geojson.io**: https://geojson.io/ (drag & drop GeoJSON)
- **Leaflet**: Web mapping library with style options
- **Folium** (Python): Create interactive maps programmatically

### Python Mapping Example
```python
import folium
import json

with open('GeoJSON_Output/Pontaise1885.geojson') as f:
    data = json.load(f)

m = folium.Map(location=[46.52, 6.63], zoom_start=13)
folium.GeoJson(data).add_to(m)
m.save('map.html')
```

---

## Workflow Commands (Quick Reference)

Run all three steps in sequence:

```bash
# Step 1: Sanitize (quick, ~10 seconds)
python SanitiseForNominatim.py

# Step 2: Geocode (slow, ~2-3 hours)
python GeocodeWithNominatim.py

# Step 3: Export (quick, ~10 seconds)
python ExportToGeoJSON.py
```

---

## Excel Column Reference

| Column | Letter | Content | Created By |
|--------|--------|---------|-----------|
| 4 | D | Original address | Directory extraction |
| 19 | S | Sanitized address | `SanitiseForNominatim.py` |
| 20 | T | Latitude | `GeocodeWithNominatim.py` |
| 21 | U | Longitude | `GeocodeWithNominatim.py` |

---

## Troubleshooting

### Geocoding takes too long
- Run on a subset of files first
- Nominatim is free but slower than commercial services
- Results are cached, so re-running only processes new addresses

### Many addresses return (None, None)
- Check the sanitized address format (column S)
- Historical street names may have changed
- Some addresses may not exist in Nominatim's database
- Consider searching by neighborhood instead

### GeoJSON export shows no features
- Ensure Step 2 is complete (coordinates in columns T & U)
- Check that addresses were successfully geocoded

### Rate limiting errors
- Script includes built-in 1.5s delay per request
- This is the minimum recommended by Nominatim
- If errors occur, increase the delay parameter

---

## Data Quality Notes

### Known Issues
- Some historical addresses don't exist in modern Nominatim
- Street names may have changed since 1880s-1950s
- Nominatim may geocode to modern equivalents
- Neighborhoods (Pontaise, Prélaz) are recognized better than specific old street names

### Validation
After geocoding, check:
1. Are coordinates within Lausanne bounds? (~46.5°N, 6.6°E)
2. Do clusters match known neighborhoods?
3. Are there obvious outliers far from Lausanne?

### Advanced: Improving Matches
For addresses Nominatim can't find:
1. Try adding neighborhood name: "Rue X, Pontaise, Lausanne"
2. Use modern street names if known
3. Fall back to neighborhood center point
4. Manually research historical street renames

---

## References

- **Nominatim**: https://nominatim.org/
- **OpenStreetMap**: https://www.openstreetmap.org/
- **GeoJSON Spec**: https://geojson.org/
- **QGIS**: https://www.qgis.org/
- **Folium**: https://python-visualization.github.io/folium/

---

## File Summary

| Script | Purpose | Time | Status |
|--------|---------|------|--------|
| `SanitiseForNominatim.py` | Clean addresses | ~10s | ✅ Run this first |
| `GeocodeWithNominatim.py` | Get coordinates | ~2-3h | ⏳ Run after sanitizing |
| `ExportToGeoJSON.py` | Create map-ready data | ~10s | Run last |

