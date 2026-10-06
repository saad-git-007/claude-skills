# Setting real fonts through Firefox automation

The Canva MCP can't change font family, so drive the Canva web editor in the user's signed-in browser.

## 1. Connect to the right browser
- A headless Firefox MCP (`--headless`, fresh profile) is **not signed in**, so Canva shows a login wall. Don't try to log in with credentials.
- Use the Firefox MCP configured with `--connect-existing --marionette-port 2828`. It needs a Firefox running with automation (Marionette) on. Check with `get_firefox_info`: "No Marionette listener" means none is running.
- **Use a dedicated control profile, separate from the user's everyday browser.** The user signs in to Canva once in that profile. **Never close, signal or control the user's everyday Firefox profile.** Two profiles can run side by side only as separate instances (`--new-instance`). Without that flag, Firefox hands the launch to the already-running browser and opens a window in the user's personal profile.
- **Launch it yourself** (no need to ask, because nothing the user has open is interrupted):
  - If the user has a personal launcher (e.g. `~/.local/bin/firefox-claude`, or one recorded in memory), run that.
  - Otherwise run the bundled `scripts/firefox-control-launcher.sh "<profile dir>"`. Profile folders live under `~/snap/firefox/common/.mozilla/firefox/` (snap) or `~/.mozilla/firefox/`, named like `xxxxxxxx.Profile 1`; ask the user which profile is the control one. The script exits early if the instance is already up. If the control profile is open *without* automation, it stops; then ask the user to close only that profile's window.
  - Offer to make it permanent: copy the script to `~/.local/bin/firefox-claude` with the profile filled in, plus an optional `.desktop` entry, and save a memory note naming the control profile.
- Confirm you're on the right instance: `list_pages` should show the control profile's tabs (a fresh launch shows a single new tab), not the user's everyday tabs.
- While automation is on, Firefox shows a striped address bar and a robot icon. Tell the user that's normal.
- Open `https://www.canva.com/design/<DESIGN_ID>/edit` and take a screenshot to confirm the editor loaded.

## 2. Getting clickable handles for canvas text
Canva renders text as DOM spans, but the snapshot tree is truncated too deep to reach them. The pattern that works:
1. Tag the target with `evaluate_script`: walk text nodes under `main`, take the **first** match (the visible canvas copy; later duplicates are hidden measuring copies), and set `parentElement.id = 'cc_cur'`. Remove the previous `cc_cur` first.
2. Call `take_snapshot` with `selector: "#cc_cur"` to get its uid.
3. Call `click_by_uid` with that uid.

**Pitfall**: running several `#id` snapshots in parallel made them all return the same uid, which then pointed at the last element tagged. Snapshot and click **one element at a time**. After clicking, verify with a screenshot or by reading the toolbar's `button[aria-label^="Toggle font selector"]` label.

## 3. Applying a font
- **Everything at once**: click any text element, press `ctrl+a` (this selects every element on the page), and open the font picker. The font applies to all text in the selection; shapes and images are unaffected.
- Font picker button: `button[aria-label^="Toggle font selector"]`. Tag it and click it the same way.
- Search box: `input[type=search]` whose placeholder contains "Calligraphy". Use `fill_by_uid` with the font name, then wait about 1.5s.
- Result button: `button[aria-label="<Exact Font Name>"]`. Results are images, so match the aria-label, not the text. Tag it and click it.
- While the font panel stays open, the result button's uid stays valid. For each further element: tag it, snapshot it, click it, then click the same result uid.
- **Don't** press the "Change all" bar that appears at the bottom of the panel unless you want every use of that font in the design replaced.

## 4. Verify
- Check fonts per element with `getComputedStyle(span).fontFamily`. Canva uses internal ids like `"YAFdJhem5V8_1"`, so matching ids mean matching fonts.
- Take a full screenshot and look for overflow: text running into neighbours, or a card title wrapping onto an extra line.
- Read the save state from page text: look for "All changes saved".
- Canva autosaves, so there's no separate commit step in the browser.
- Later, `pdffonts` on an exported PDF confirms the real font names (e.g. PlayfairDisplay-Bold, Montserrat-Regular).
