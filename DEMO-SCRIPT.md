# Demo video shot list (target 2:45, hard cap 3:00)

Record the browser window only (1280 × 800 is plenty), page zoom 110%. Open
`site/index.html` from the repo, or the GitHub Pages URL. Each deep link below sets the
page up in one click; paste it in the address bar after the `index.html`.

| # | Time | On screen | Say (roughly) |
|---|------|-----------|---------------|
| 1 | 0:00–0:15 | The page header, top strip with 911 / 988 | "It's 11 pm, your wrist is swollen. ER or urgent care? Hospitals already publish how long their emergency departments take, but nobody can read it. This is ER or Urgent Care?" |
| 2 | 0:15–0:35 | Click the **Chicago, IL** chip. Check "Chest pain or pressure". | "Safety first. If you check any red flag, like chest pain, the page stops comparing and tells you to call 911. Wait numbers don't apply to emergencies; the sickest are seen first." Point at the greyed-out results. |
| 3 | 0:35–0:55 | Uncheck chest pain, check "Sprain, strain…". Green verdict appears. | "For a sprain, urgent care is usually fine. The checklist is paraphrased from MedlinePlus, and it's information, not a diagnosis." |
| 4 | 0:55–1:30 | Scroll to the Northwestern Memorial card (5 h 50 min). | "Here's the real CMS number: Northwestern's median total visit for patients sent home is 5 hours 50. That's the whole visit, not the time until you see a doctor, and it covers October 2024 to September 2025. Next to it: that is longer than almost every other Illinois hospital, and busy departments like this one run longer nationally too." |
| 5 | 1:30–2:00 | Drag the σ slider from 0.6 to 0.9 and back. | "CMS publishes one number, no spread. So the range is an assumption, and I label it that way. I model a visit as lognormal with the median pinned to the CMS value. Move the spread and the range and the chance of going over four hours update. The median is data; the band is illustration." |
| 6 | 2:00–2:15 | The Lurie Children's card showing "Not Available" and its footnote. | "When CMS has no value, you see why, from CMS's own footnotes, instead of a blank." |
| 7 | 2:15–2:30 | Urgent-care column: Physicians Immediate Care, hours, "Wait time: no public data". | "Urgent care from OpenStreetMap. No public source publishes urgent-care waits, so I don't invent one." |
| 8 | 2:30–2:45 | Type ZIP 14850 (Ithaca), show Cayuga Medical Center; then scroll to "How to read these numbers". | "Any US ZIP works for hospitals. Every number is either from CMS, the Census or OpenStreetMap, or marked assumed. The method, tests and one-page summary are in the repo." End on the footer with sources. |

Deep links:

- Chicago with a red flag: `#zip=60611&check=chest`
- Chicago, sprain: `#zip=60611&check=sprain`
- Ithaca: `#zip=14850&check=cold`
- Fremont with wide spread: `#zip=94539&sigma=0.9`

Tips: keep the mouse still while talking; cut any dead air in the edit. If the video runs long,
drop shot 6 first, then shot 8's ZIP typing.
