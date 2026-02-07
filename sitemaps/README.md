# Player ID Mapping

## player_id_map.csv

**Source:** Smart Fantasy Baseball Tools Player ID Map
**URL:** https://www.smartfantasybaseball.com/tools/

This file maps MLBAM IDs (universal baseball identifier) to platform-specific IDs
for Fangraphs, Fantrax, ESPN, Yahoo, CBS, and other fantasy platforms.

### Why CSV from Google Sheets?

The SFBB tools page publishes this mapping as a Google Sheets document. We download
the CSV export because:
- Simpler to work with (no Excel dependencies)
- Better for version control (git can show diffs)
- We commit to repository, so no need for live Google Sheets connection
- Can be automated with a simple download script

### How to Refresh:

**Easy way (recommended):**
```bash
python sitemaps/refresh_player_map.py
git add sitemaps/player_id_map.csv
git commit -m "Update player ID mapping"
```

**Manual way:**
1. Visit https://www.smartfantasybaseball.com/tools/
2. Find the Player ID Map section
3. Download the CSV export
4. Save as `sitemaps/player_id_map.csv`
5. Commit to repository

**Recommended refresh frequency:**
- Weekly during baseball season (March-October)
- Monthly in offseason (November-February)
- Before any major draft or auction

### Why Periodic Download vs Google Sheets API?

We use periodic downloads rather than real-time Google Sheets API access because:
- No runtime dependencies on Google APIs
- No authentication/API keys needed
- Data is versioned in git (can track changes)
- Faster (local file vs network call)
- Player IDs rarely change (weekly updates are sufficient)

## Migration from fangraphs_to_fantrax.csv

This file replaces the manually-maintained `fangraphs_to_fantrax.csv` mapping.

**Benefits:**
- No more manual mapping maintenance
- Stable IDs across minor→major league transitions (MLBAM IDs don't change)
- Easy multi-platform support (ESPN, Yahoo, etc. are already in the file)
- Community-maintained and updated weekly
- Handles edge cases gracefully with Fangraphs ID fallback

**The old mapping file is deprecated and can be removed after verifying the new system works.**
