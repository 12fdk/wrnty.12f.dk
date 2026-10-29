# wrnty — Marketing Plan (living doc)

Owner: Robert · Maintained by: Hermes (social pipeline agent) · Last updated: 2026-10-29

## 1. What this is & how it's updated

- Hermes owns this file and runs every step in it. Robert reviews it and owns
  the decisions marked *Robert* in §9.
- Pipeline (Appwrite db `marketing`, app slug `wrnty`, on app.12f.dk):
  - Nightly job (`wrnty-social-content`, shared `social-post` template, channel
    platform, spark#140): builds the next due §6 row — media rendered on the spark
    (`comfy-gen`, `motion-render`), created with `marketing-post` as `status=ready`
    at the time it picks (Hermes owns the schedule, marketing#97); `publish-social`
    publishes it then.
  - Before it picks a row, the job removes §6 plan rows whose post is published
    (`plan_prune.py`, spark#138). History lives in §8, in Appwrite and in the look
    ledger, not in §6.
  - Function `publish-social` (every 15 min) publishes to IG and FB; enforces a 20h
    minimum gap between two feed posts of the app.
  - Function `collect-metrics` (every 2h) writes IG/FB engagement into the post docs.
  - Function `optimize-guidelines` (monthly) — **dormant**.
- The nightly job also runs the §7 review and appends rows to §8.
- This file is the social plan only. The weekly blog has its own brief
  (`prompt.md`); the two share the facts in §2 and the consumer-law rule in §3.
- Editing rules for this file:
  - Append-only to §8: never delete or rewrite past log rows.
  - Plan changes go in §6, plus a §8 row that says why.
  - §3 and §4 change only on Robert's say-so.
  - Update the `Last updated` line on every edit.
  - Keep exactly one text-slide colour line (§3): `marketing-post --colors-from`
    refuses a file with zero or two.
  - Never put secrets, API keys or tokens in this file.

## 2. Product & funnel

- Product (LIVE iOS app, warranty & receipt tracker): for each item you record
  "product name, brand, merchant, price, purchase and expiry dates, serial number
  and notes", attach receipts and documents "as photos and PDFs", get an expiry
  reminder before the warranty runs out, see what's expiring next in Home and Lock
  Screen widgets, and export a claim-ready PDF. Spotlight search, categories, a
  running total of the value under warranty, dark mode and VoiceOver.
  (Source: `llms-full.txt` "Features", read 2026-10-15; the live file and the repo
  copy are identical.)
- Platforms: iPhone and iPad, iOS 17 or later. App in 28 languages; site in
  English. Made by 12F ApS, Denmark. (Homepage + `llms-full.txt` "Key Facts".)
- Price model: free to download; **free tracks up to 2 warranty items**.
  **Premium is a one-time in-app purchase** — "No subscription, ever." — that
  removes the item limit and adds expiry alerts, iCloud sync, PDF export, and
  share & print. The site does not print a price ("the current price is shown in
  the App Store"), so **posts never quote a price**. (Homepage "Pricing" + FAQ.)
- Privacy: no account, no sign-up; data stays on the device and syncs only
  through the user's own iCloud if they turn it on; no ads, no tracking, no data
  selling; any analytics are anonymous and optional. (Homepage "Privacy" +
  `llms-full.txt`.)
- Launch status: **live**. The App Store listing answered on 2026-10-15
  (`https://apps.apple.com/us/app/wrnty-warranty-receipts/id6747742961`, app id
  6747742961, "Requires iOS 17.0 or later", offers in-app purchases). It has
  almost no ratings yet: never cite a rating, a review or a user count.
- Funnel today: profile bio → `https://wrnty.12f.dk/` → App Store tap (Umami
  event `appstore-click`, with `placement` nav / cta) → App Store id6747742961.
  Every page also carries Apple's Smart App Banner (app-id 6747742961).
  - Umami site `fbcd006e-5e3c-456b-ad83-5a495a84c308`.
  - **There is no `/go/?src=` hop on wrnty.12f.dk** (`/go/` answered 404 on
    2026-10-15), so social traffic shows up only as IG/FB referrers. See §9.
- Downloads are counted in App Store Connect (read through the `app-store`
  Appwrite project), not Umami.
- Instagram / Facebook account: **not known** — the app record's
  `instagramHandle` is null and the site links to no social profile. See §9.

### Claim sheet — what each §6 feature may say (added 2026-10-15)

Verbatim from the live homepage and `llms-full.txt` (read 2026-10-15). Use these
lines, not paraphrased promises. If a line here and the site disagree, the site
wins — re-read it and fix this table.

| §6 feature | Verbatim line(s) | Tier |
|---|---|---|
| Add an item | "Add a product in seconds: a photo of the receipt, the warranty length, the purchase date." · "One-tap presets cover the common durations." | Free |
| Receipts & proof | "Photograph the receipt, the box, the serial plate. When something fails, the proof is one tap away — not in a drawer somewhere." · "photos and PDFs, as many as an item needs" | Free |
| Expiry reminders | "Set the expiry date and wrnty warns you in good time — on your Home and Lock Screen — so you claim while the cover still stands." | **Premium** |
| PDF export | "export a PDF pack for the insurer" · "a tidy claim pack for insurers and retailers" | **Premium** |
| iCloud sync | "the same list on your iPhone and iPad" · "synced only through your personal, end-to-end encrypted iCloud" | **Premium** |
| Widgets | "Pin what's next and glance at the days left, no tapping in." | (site does not say) |
| Running total | "a running total of the value you have under warranty" | (site does not say) |
| Spotlight search | "jump to a product straight from iOS search" | (site does not say) |
| Sorted / organised | "By expiry, price, purchase date or name — due-soon items float to the top." · "Categories, brands & serials — organised the way you shop" | Free |
| One-time purchase | "Pay once. That's it." · "No monthly fee, no annual renewal, no trial that quietly charges you. Buy wrnty once and it stays yours." | — |
| Free tier | "Free to start. One-time upgrade if you want more." · "Two items free — no card, no countdown." | Free |
| Privacy | "No account, no sign-up. Nothing to create, nothing to forget, nothing to breach." · "Your receipts are a map of what you own and what it cost." · "No ads, no tracking, no selling" | — |
| The story | "The washing machine goes. You think it might still be covered, you can't find the receipt, so you pay for the repair. Three weeks later the receipt turns up in a drawer — four months of cover left." · "The engineer asks when you bought it. You know — to the day" | — |

Rules for the claim sheet:

- A post about reminders, PDF export or iCloud sync never puts "free" next to
  that feature. Say "Premium" or leave price out of that post.
- **Never claim:** reading or scanning a receipt's text (the user takes a photo
  and types the details — no OCR, no auto-fill), barcode or product lookup,
  auto-filled warranty lengths, works offline (the app record says so; the site
  does not), sharing items with other people (only "share & print" of the
  export), an Android, web, Mac or desktop app, any backup but the user's own
  iCloud, any rating, review, testimonial or user count, any price.
- **Never use the app record's statistics** (e.g. "75% of consumers lose track of
  warranties") or the "$8,642.94" example from a screenshot caption. Neither is
  sourced. Make the point in words.

## 3. Content rules

- Text-slide colours: background #0b6b3a · text #f1faf4 · accent #fbbf24
  (carousel text slides; `marketing-post --colors-from` reads this line, so keep
  its format. Taken from the site's own tokens in `css/style.css`: `--green-dark`
  #0B6B3A, `--bg-soft` #F1FAF4, and the dark-mode amber `--gold-ink` #FBBF24 —
  the amber "highlighter" of the site. Contrast: text on background 6.2:1 (WCAG
  AA for all text), accent on background 4.0:1 (above the 3:1 for large text and
  graphic rules). Set 2026-10-15 for spark#140.)
- **The brand is always lowercase `wrnty`**, also at the start of a sentence or
  a slide — reword so the sentence does not start with it. Never "Wrnty", never
  "WRNTY" (the `bold` reel look sets type in capitals: keep the app name out of
  `bold` headlines).
- **Photo style — "the evidence" (wrnty's own; generated fresh for every post).**
  Real-looking documentary photography of the things people own and the proof
  that goes with them, in real lived-in homes. Never illustration, never 3D
  renders, never glossy product-ad style.
  - Two shot types. **Exhibit**: overhead, square-on, the item's kit laid out
    neatly (knolling) on one surface — the item, its charger or parts, the empty
    box, a folded receipt. Used for carousel covers. **Moment**: eye level, the
    minute it breaks or the minute the proof turns up — a stopped washer with
    water on the floor, a kitchen drawer stuffed with paper, a laptop closed on a
    desk. Used for reels and inner carousel photos.
  - Light: honest daylight first — overcast window light, cold morning, garage
    strip light, utility fluorescent. Warm lamp light only for evening scenes.
    Golden hour at most one post in five (the app record's style preset leans to
    golden hour; treat it as one option, not the default).
  - Palette: neutral rooms (white, oak, concrete, steel, linen) with a green
    thread (sage, eucalyptus, bottle green) and **one amber object in every
    frame** (a blank sticky note, a highlighter, brass, a mustard towel) — the
    site's highlighter, carried into the photos. Never the plum-and-peach of the
    sister apps.
  - Lens: about 35–50 mm documentary, enough depth of field to see what the
    objects are; macro for details. No dreamy bokeh portraits of products.
- Settings come from where things break and where proof hides: utility room,
  kitchen drawer, home office, garage bench, hallway with delivery boxes, living
  room with the TV switched off, nursery, bike shed, loft, home gym, pantry,
  doorstep. §6's Look column gives each row its own start point.
- Every post looks new (spark#133): a different setting, light, colour mood and
  composition from the app's recent posts (`marketing-post looks --app wrnty`);
  for a reel also a different reel look and music variant. Fresh stills and clips
  for every post; never reuse a still or clip from an earlier post.
- Image rules (the job enforces them on every still and every video frame):
  - No phone screens, no app UI, no screens with content. Phones face-down, in a
    pocket or in a sealed box; TVs and laptops off (black glass) or closed.
  - No AI faces. Hands are fine (check the finger count); people only from
    behind or cropped below the shoulders.
  - No readable text: receipts, manuals and serial plates are folded, curled,
    face-down or out of focus — never a printed face the model can garble.
  - No brand logos; appliances and gadgets are generic and unbranded.
- **No real app footage exists yet** (nothing for wrnty in `12fdk/motion`,
  checked 2026-10-15). Until §9's footage question is solved, app UI appears
  nowhere — not in reels either. Feature reels tell the feature in on-screen text
  over b-roll.
- One message per post. The hook lands in the first 1–2 seconds and names **a
  concrete product + a concrete moment or problem** ("The fridge is 22 months
  old.", "The receipt turned up three weeks later."). The app name never opens a
  post.
- Banned openers: a statistic ("75% of people…"), "Did you know…", "Stop losing
  money" with no product in it, a season with no product and no problem ("Black
  Friday is coming!"), fear with no fix ("Your warranty expired yesterday." alone).
- Tone: the brand record's "friend who always keeps the receipt" — practical,
  dry, a little smug in a fun way, never preachy. Never talk down to someone who
  lost a receipt (the blog brief's rule holds here too). No hype words
  ("game-changer", "must-have", "ultimate"), no exclamation-mark selling.
- **Consumer law and warranty facts — how posts handle them:**
  - The generic line is always safe: "In many countries you also have a separate
    statutory right against the seller, and it can outlast the warranty." (live
    blog, `consumer-rights-when-something-breaks`).
  - The **EU** rule may be named only as the EU's and only with the check line:
    "In the EU you have a minimum 2-year guarantee on goods from the seller" —
    source: European Commission, Your Europe, "Guarantees and returns" ("You
    always have the right to a minimum 2-year guarantee from the moment you
    received the goods", read 2026-10-15) and Directive (EU) 2019/771.
  - UK and US rules are not stated in posts (they have their own frameworks and
    time limits; no slide has room for them). Say "the rules differ by country".
  - Every post that mentions rights or coverage ends that slide or caption line
    with "Check the rules where you live." It never says someone *will* get a
    repair, refund or replacement, and it is never legal advice.
  - Warranty lengths: only generic and hedged ("often", "many", "check your
    terms"), never one named brand's terms, never as a universal fact.
  - Product-care tips: common-knowledge habits only ("clean the filter", "check
    the manual for how often"), no numbers, no safety claims; the manual wins.
  - Money: no currency figures (the audience is international). Ages and months
    in hooks ("22 months old") are the scenario, not a statistic.
- CTA (the app is live and free to start), verbatim from the app record's
  ctaOptions:
  - Default, every post: "Download free today".
  - Pay-once posts may use instead: "One-time purchase - no subscriptions".
  - Proof-kit and gift posts may add: "Tag someone who just bought a new phone".
  - Carousels may add the comment prompt: "How many warranties have you
    forgotten about?"
  - The caption points to the profile with "Link in bio". Never "Get notified".
- Hashtags: at most 5 per post, always `#wrnty`. The rest from the brand list:
  `#WarrantyTracker`, `#Warranty`, `#ConsumerProtection`, `#SaveMoney`,
  `#SmartShopping`, `#HomeAppliances`, `#Electronics`, `#OrganizedLife`,
  `#PrivacyFirst`, `#giftingtips`, plus at most one tag for the §6 calendar moment
  (`#blackfriday` is in the brand list; e.g. `#CyberMonday`, `#BoxingDay`).
- One video per episode.
- A post that breaks any rule is not published: set it back from `ready` and log
  why in §8.

## 4. Cadence

- Set 2026-10-15 for spark#140. wrnty's audience is 30–55 and heavy on Facebook,
  and the app record ranks carousels first (saves) and reels second (reach), so
  wrnty is **carousel-led**, unlike the reel-led sister apps.
- Ramp:

  | Week of | Posts |
  |---|---|
  | Oct 19 | 2 (1 carousel + 1 reel) |
  | Oct 26 | 3 |
  | Nov 2 – Nov 16 | 4/week (2 carousels + 2 reels) |
  | Nov 23, Nov 30 | 5/week — Black Friday / Cyber Monday, the biggest purchase weeks |
  | From Dec 7 | steady 4/week (2 carousels + 2 reels) |

- Floor: never below 3/week from Nov 2. Consistency beats bursts: if a week
  can't be filled, spread posts out instead of batching.
- The pipeline posts every post to both IG and FB. 5/week fits under the 20h gap
  (~8/week max). Avoid FB link posts.
- Posting time: the app record has "[Auto-observed 2026-10] Active days:
  Wednesday, Sunday · Active hours (UTC): 16:00". That is data, not a rule — use it
  to break ties between free slots in a row's week, never to skip a week.

## 5. Format playbook

| Format | Job | Evidence | Rules |
|---|---|---|---|
| Carousel (5–8 slides) | Earns saves — the app record's top format | Checklists ("5 warranties you are forgetting to track", "what to do when your warranty expires") are the most saveable | Slide 1 = an Exhibit photo + the hook (product + problem); inner slides alternate text slides and Moment photos; last slide = CTA |
| Reel (15–30 s) | Reach to non-followers | The app record: "this is how much money you lost" scenarios and satisfying organisation clips | Fresh b-roll only (no app footage yet); hook text at 0 s; end card with the CTA; spec in `/workspace/motion/reels/wrnty-<slug>.json` |
| Stories | Polls, quick tips | The app record wants them daily | Pipeline is feed-only today — decision in §9 |
| Static image | Updates only | The app record | Not in the plan |

### Reel look (wrnty's own)

- Reel spec skin, locked: `"accent": "#FBBF24"`, `"ink": "#FFFFFF"`,
  `"bg": "#0B6B3A"` (the same amber and green as the text slides).
- Look rotates between the three reel looks in `remotion/src/reel/spec.ts`:
  - `clean` (Bricolage over a scrim) — the default: features, pay-once, tips.
  - `editorial` (Fraunces over a scrim) — the "Three weeks too late" stories and
    the care reels; slower cuts, longer holds.
  - `bold` (Anton in amber bars) — only deal-season rows (Singles' Day, Black
    Friday, Cyber Monday, Boxing Day, Presidents' Day). Never two `bold` reels in
    a row. Keep "wrnty" out of `bold` headlines (it sets capitals).
- Never the same look in more than two reels in a row. The §6 Look column names a
  look per reel row; swap it when `marketing-post looks` shows a repeat.
- Pacing on the 0.5 s grid: 5–8 scenes; a Moment clip first, the Exhibit still
  near the end, then the end card "Download free today" with the sub-line
  "iPhone & iPad · iOS 17+".
- Music: the `music` bed with a variant —
  `"audio": {"bed": "music", "variant": <0-5>, "clips": false}` (`render-reel.mjs`
  reads `audio.variant`; `music.mjs` ids 0–5 = c-major, a-major, g-min, e-min,
  d-major, c-min). No variant twice within any 6 consecutive reels. Minor
  variants (2, 3, 5) for the "it broke" stories; major variants (0, 1, 4) for
  wins, organising and pay-once. Clip audio off: generated clips carry random
  sound. Motion also ships a `-silent.mp4`.

### Series (recurring formats; each row in §6 names one)

| Series | Format | What it is | Pillar (app record) |
|---|---|---|---|
| **Still covered?** | Carousel or reel | One item at a given age; what to check before paying for a repair: the date, the proof, the seller (hedged, §3) | Warranty tips 30% |
| **The proof kit** | Carousel or reel | What to keep for one purchase or one moment (a delivery, a gift, an online order); Exhibit cover | Money-saving 25% + app features 15% |
| **Three weeks too late** | Reel (`editorial`) | The site's story, retold with a different product each time; the fix in the last 3 s | Money-saving scenarios |
| **Fine print** | Carousel | One warranty gotcha per post, from the blog (accidental damage, registration, opening the device) | Warranty tips |
| **Before the counter** | Carousel or reel | The protection-plan question, decided before the till; timed to deal days | Seasonal buying guides 10% |
| **Make it last** | Carousel or reel | One appliance, a few generic care habits, "check the manual" | Product care 20% |
| **Pay once** | Reel or carousel | One-time purchase, no account, private by design | App features / anti-subscription |

Brand-record pillar split: warranty tips 30%, money-saving scenarios 25%,
product care 20%, app features 15%, seasonal buying guides 10%. Audience:
homeowners and gadget owners 30–55 who have been burned before, privacy-minded
and tired of subscriptions; secondary small business owners with equipment;
tertiary new homeowners furnishing a first home.

Baseline: **none known.** The look ledger for `wrnty` is empty (2026-10-15) and
this session could not read the platform's post history. The first §7 run sets
the baseline in §8 (see §9).

## 6. Content plan (week of Oct 19, 2026 – week of Feb 15, 2027)

### Calendar hooks — the moments this plan piggybacks on (added 2026-10-15)

Buying seasons are the reach engine for a warranty app: post **just before** the
purchase (the protection-plan question, what to keep) and **just after** it
(log it before the box goes out). The hook names the moment AND a product AND a
problem — a moment alone is the banned seasonal opener (§3).

| Moment | Date | Post by | Angle | §6 rows |
|---|---|---|---|---|
| Clocks change (EU / US) | Sun Oct 25 / Sun Nov 1, 2026 | Oct 30 | a seasonal care check for the things that work hardest in winter | Oct 26 #2 |
| **Singles' Day** (global online sale) | Wed Nov 11, 2026 | Nov 10 | an online order: the confirmation is the proof | Nov 2 #3, Nov 9 #2 |
| **Black Friday** | Fri Nov 27, 2026 | Nov 26 | before: the protection plan at the till; after: what to keep from each deal | Nov 9 #1, Nov 16 #3, Nov 23 #1–#4 |
| **Cyber Monday** | Mon Nov 30, 2026 | Nov 29 | online orders, delivery week, log it on arrival | Nov 23 #5, Nov 30 #1–#2 |
| **Holiday gifts** | all of December | Dec 20 | gift receipts; give the proof with the gift | Nov 30 #3, Dec 7 #1, Dec 14 #1, Dec 21 #2 |
| **Christmas / unwrapping day** | Fri Dec 25, 2026 | Dec 24 | log it before the box goes in the recycling | Dec 21 #1 |
| **Boxing Day sales** (UK, IE, CA, AU) | Sat Dec 26, 2026 | Dec 24 | the big TV and the plan offered at the till | Dec 21 #3 |
| **New year, organising** | Fri Jan 1, 2027 → all January | Jan 15 | the receipt drawer, a home inventory, fewer subscriptions | Dec 28 #1, #3, Jan 4 #1–#2, Jan 11 #2 |
| **Gift returns & new kit** (pattern, Jan) | no fixed date | — | Christmas gadgets: set the reminder now | Jan 18 #1 |
| **Valentine's Day** | Sun Feb 14, 2027 | Feb 10 | a watch or jewellery gift: keep the paperwork with it | Feb 1 #4, Feb 8 #2 |
| **Presidents' Day sales** (US) | Mon Feb 15, 2027 | Feb 12 | appliance deals: four questions before you pay | Feb 8 #1, #4 |
| Winter wear and tear (pattern) | Dec–Feb | — | heating, dryers, dishwashers and boilers under load | Nov 30 #4, Dec 14 #4, Jan 18 #3 |
| Spring appliance season, tax-refund buys | Mar–Apr 2027 | next plan | the app record's spring spike | Feb 15 #2 (lead-in) |

Not planned, on purpose: **Halloween** and **Thanksgiving** (no warranty
angle), **Super Bowl TV sales** (the NFL date was tentative; the TV angle is
covered on Jan 25), **back-to-school** (August, outside this plan). Deal days
are patterns of retail behaviour: posts never state a discount, a sales figure or
a statistic about them.

Dates checked 2026-10-15 (weekdays computed; Black Friday = the day after US
Thanksgiving, the 4th Thursday of November; Presidents' Day = the 3rd Monday of
February; EU clocks change on the last Sunday of October, US on the 1st Sunday of
November).

### The plan

| Week of | # | Format | Series | Feature / message | Hook (first 1–2 s) | Look / scene (start point; must differ from recent looks) | Status |
|---|---|---|---|---|---|---|---|
| Nov 2 | 4 | Reel | Three weeks too late | Expiry reminders (Premium) | "The headphones died at month 13. The warranty ended at month 12." | `editorial` · park bench in fog, headphones on wet wood, cool grey-green, slow push-in | built 2026-10-29 6ae38c9c35bffc973e9b |
| Nov 9 | 1 | Carousel | Before the counter | Extended warranty: decide before Black Friday | "Black Friday TV in your cart. Do you need the extended warranty?" | living room, TV off (black glass) on an oak sideboard, soft north light, amber throw | queued |
| Nov 9 | 2 | Reel | The proof kit | Add an item in seconds | "Singles' Day parcels arrive. Log each one before the box goes out." | `clean` · student-flat floor, three parcels opened by hands only, crisp daylight, kraft and green | queued |
| Nov 9 | 3 | Carousel | Make it last | Coffee machine care (generic; check the manual) | "The coffee machine is two winters old. Descale it before it decides for you." | pantry corner at dawn, steam, blue early light, brass kettle, oat linen | queued |
| Nov 9 | 4 | Reel | Pay once | Private by design ("a map of what you own") | "Your receipts are a map of what you own. Keep that map to yourself." | `editorial` · dim study with deep green walls, a filing box lid closing, single desk lamp | queued |
| Nov 16 | 1 | Carousel | Fine print | Defects vs accidents (blog: what a warranty covers) | "The laptop warranty covers defects. Not the coffee you spill on it." | home office, closed laptop beside a tipped mug, morning side light, sage notebook | queued |
| Nov 16 | 2 | Reel | Still covered? | Expiry dates + receipts | "The pushchair wheel cracked at month 10. Where's the receipt?" | `clean` · hallway by the front door, folded pushchair, soft pastel daylight, eucalyptus wall | queued |
| Nov 16 | 3 | Carousel | The proof kit | Black Friday: what to keep from every order | "Black Friday checklist: what to keep from every order." | Exhibit: parcels, scissors, packing slips face-down on white, high-key overhead, one amber tape roll | queued |
| Nov 16 | 4 | Reel | Three weeks too late | Receipts attached | "The robot vacuum stopped. The order email is somewhere in 4,000 others." | `editorial` · rainy evening, closed laptop, window streaks, teal-grey, vacuum stuck under a sofa | queued |
| Nov 23 | 1 | Reel | Before the counter | Protection plan decision (deal day) | "Black Friday at the till: 'Want the protection plan?' Decide before you go." | `bold` · car park at night, wet tarmac, sodium light, shopping bags in an open car boot | queued |
| Nov 23 | 2 | Carousel | The proof kit | Big appliance delivery: receipt, serial plate photo, registration email | "The new fridge arrives Saturday. Take three photos before it's pushed into place." | kitchen mid-install, cardboard corners, a hand truck, flat daylight, steel and sage | queued |
| Nov 23 | 3 | Reel | Pay once | One-time purchase | "Black Friday rule: no new subscriptions. Pay once." | `clean` · kitchen counter, tidy stack of paper envelopes, a hand slides one away, hard noon light, black and amber | queued |
| Nov 23 | 4 | Carousel | Fine print | Registering does not create coverage (blog: register a product) | "Do you need to register that Black Friday TV to get the warranty?" | living room, packaging foam on a rug, TV lying face-down on a blanket, cold morning light | queued |
| Nov 23 | 5 | Reel | Still covered? | Expiry reminders (Premium) | "Last year's Cyber Monday laptop. Is it still covered?" | `editorial` · co-working desk, overcast, closed laptop on grey felt, amber pencil | queued |
| Nov 30 | 1 | Carousel | The proof kit | Cyber Monday orders: where the proof lives in a year | "Cyber Monday orders: where will the proof be next November?" | parcels by a radiator, low winter sun, long shadows, white and moss green | queued |
| Nov 30 | 2 | Reel | Still covered? | Running total | "Add up what you bought this month. That's what's under warranty now." | `bold` · dining table covered with boxes, overhead, cool white light, quick cuts | queued |
| Nov 30 | 3 | Carousel | The proof kit | Gift receipts are proof too (blog: proof of purchase) | "Buying a gift? Ask for the gift receipt — it's proof for them too." | wrapping table, kraft paper, green ribbon, warm afternoon window | queued |
| Nov 30 | 4 | Reel | Make it last | Dryer care in winter (generic) | "Winter is hard on the dryer. Two minutes after every load." | `editorial` · laundry room at night, tumbling towels, warm amber bulb, steam | queued |
| Nov 30 | 5 | Carousel | Pay once | No account, nothing to breach | "No account. No sign-up. Nothing to breach." | minimalist hallway shelf, keys in a brass bowl, morning daylight, white and bottle green | queued |
| Dec 7 | 1 | Reel | The proof kit | Gift + proof | "Giving someone a coffee machine? Give them the proof too." | `clean` · snowy window, box wrapped in green paper, crisp blue daylight | queued |
| Dec 7 | 2 | Carousel | Still covered? | Repair or claim, before the holidays (blog: repair or replace) | "Hosting this month? The oven is four years old and running hot." | kitchen, oven door open, roasting tray, warm tungsten evening, cast iron | queued |
| Dec 7 | 3 | Reel | Three weeks too late | Receipts attached | "The e-bike battery quit in the cold. Where's the proof?" | `editorial` · bike shed, frost, cold blue dusk, a head-torch beam | queued |
| Dec 7 | 4 | Carousel | Fine print | Accidental damage is usually not covered (blog) | "Dropped it? The warranty usually doesn't cover that." | macro: cracked glass kettle lid on slate tiles, overcast, sage cloth | queued |
| Dec 14 | 1 | Carousel | The proof kit | Phone purchase: what to keep | "Just bought a new phone? Keep these five things." | Exhibit: sealed phone box, cable, SIM tool, folded receipt on dark walnut, soft top light | queued |
| Dec 14 | 2 | Reel | Pay once | One-time purchase, end of a subscription year | "A year of subscriptions. Here's one you won't need." | `clean` · reading corner, wool blanket, green armchair, lamp and dusk window | queued |
| Dec 14 | 3 | Carousel | Make it last | Vacuum care before guests (generic) | "Vacuum working overtime before guests arrive? Empty it, check the filter." | hallway with pine needles on oak boards, cordless vacuum, warm afternoon | queued |
| Dec 14 | 4 | Reel | Still covered? | Expiry reminders (Premium) | "The dishwasher has run every night this month. When does its cover end?" | `editorial` · kitchen after dinner, dishwasher open with steam, low warm light | queued |
| Dec 21 | 1 | Reel | The proof kit | Add an item in seconds | "Unwrapping day: log it before the box goes in the recycling." | `clean` · morning living room, torn wrapping paper, hands only, pale winter sun | queued |
| Dec 21 | 2 | Carousel | The proof kit | A gift with no receipt: what can still count (blog: proof of purchase) | "Got a gift with no receipt? It may still be provable." | gift tags and ribbon, a box under a tree (no faces), fairy-light bokeh, green and gold | queued |
| Dec 21 | 3 | Reel | Before the counter | Boxing Day: the plan at the till | "Boxing Day sale, a big TV, and the plan at the till. Decide now." | `bold` · snowy high street at dusk, shop windows blurred (no readable signs) | queued |
| Dec 21 | 4 | Carousel | Still covered? | Warranty vs statutory rights (blog: consumer rights) | "The warranty ended. In many countries the seller may still owe you something." | quiet desk with paperwork face-down, flat between-holidays light, blue-grey | queued |
| Dec 28 | 1 | Carousel | The proof kit | Clear the receipt drawer | "The receipt drawer: 15 minutes before New Year's Eve." | overhead: a drawer stuffed with paper, then the same items sorted (knolling), crisp daylight | queued |
| Dec 28 | 2 | Reel | Three weeks too late | Expiry reminders (Premium) | "Last Christmas's stand mixer. One year on, it's making a noise." | `editorial` · pantry, flour dust, cold early light, mixer bowl, amber spatula | queued |
| Dec 28 | 3 | Carousel | Pay once | One-time purchase (new-year budgets) | "New year, fewer subscriptions. Start with the receipts app." | calm desk, blank paper budget notebook, green pen, low sun | queued |
| Dec 28 | 4 | Reel | Still covered? | Widgets: what's expiring next | "Which of your things runs out of warranty in 2027?" | `clean` · loft with boxes, a skylight, dust in the light | queued |
| Jan 4 | 1 | Carousel | The proof kit | Home inventory, one room at a time (blog: home inventory) | "A home inventory, one room at a time. Start with the kitchen." | kitchen counters cleared, appliances in a row, bright January daylight, white and sage | queued |
| Jan 4 | 2 | Reel | Pay once | Private by design | "Organising everything this January? Keep your receipts off someone else's server." | `clean` · clean desk, fresh plant, frost on the window, cool white | queued |
| Jan 4 | 3 | Carousel | Fine print | Why the serial number matters (blog: proof of purchase / claims) | "Why the serial number matters more than the box." | macro: the edge of a serial plate on the back of an appliance (unreadable), steel, cold light | queued |
| Jan 4 | 4 | Reel | Three weeks too late | Receipts attached | "The new-year treadmill stopped on day nine. The receipt is in last year's inbox." | `editorial` · home gym in a garage, rubber floor, cold LED + amber heater glow | queued |
| Jan 11 | 1 | Carousel | Still covered? | Repair, replace or claim (blog: repair or replace) | "The dryer needs a repair. Fix it, replace it, or claim it?" | laundry, dryer drum open, overcast, white and green | queued |
| Jan 11 | 2 | Reel | The proof kit | PDF export (Premium) for insurance | "The insurer wants a list of what you own. Hand them one PDF." | `clean` · home office, blank printer paper, an envelope, morning light | queued |
| Jan 11 | 3 | Carousel | Make it last | Earbuds care (generic) | "Your earbuds go everywhere. Five habits that help them last." | Exhibit: gym-bag contents on a rubber mat, top-down, cool light, amber towel | queued |
| Jan 11 | 4 | Reel | Before the counter | A warranty as a signal (blog: which brands last) | "Choosing a new washer? Read the warranty before the price tag." | `editorial` · utility room, two washers with doors open, softbox light, no logos | queued |
| Jan 18 | 1 | Reel | Still covered? | Expiry reminders (Premium) | "A Christmas laptop, three weeks old. Set the reminder now, not in 11 months." | `clean` · student desk, snow outside, closed laptop, cool light + amber lamp | queued |
| Jan 18 | 2 | Carousel | The proof kit | Small business kit needs records too | "Running a business from home? The kit needs a paper trail too." | workshop bench, power tools, sawdust, warm side light | queued |
| Jan 18 | 3 | Reel | Three weeks too late | Receipts attached | "The boiler failed in January. The installer's paperwork is somewhere in the loft." | `editorial` · loft hatch, torch beam, insulation, cold | queued |
| Jan 18 | 4 | Carousel | Fine print | The long cover you never registered (blog: register a product) | "The long motor warranty you never registered." | under-stairs cupboard, vacuum and boxes, dim warm bulb | queued |
| Jan 25 | 1 | Carousel | Before the counter | New TV: what the warranty covers and what it doesn't | "Upgrading the TV this winter? Read what the warranty leaves out." | living room at blue hour, TV off, green sofa, wool throw | queued |
| Jan 25 | 2 | Reel | Pay once | One-time purchase | "Count your subscriptions. Now count the apps you paid for once." | `clean` · kitchen table, paper envelopes, hard flash look, black and amber | queued |
| Jan 25 | 3 | Carousel | Make it last | Fridge care (generic) | "The fridge never gets a day off. Three checks each season." | kitchen at night, the fridge light the only glow, steel and sage | queued |
| Jan 25 | 4 | Reel | The proof kit | Find any item fast (Spotlight, receipts one tap away) | "The engineer asks when you bought it. You know — to the day." | `editorial` · hallway, a toolbag and work boots on the floor (no face), daylight | queued |
| Feb 1 | 1 | Reel | Three weeks too late | Expiry reminders (Premium) | "The camera lens started clicking at month 25." | `editorial` · photographer's desk, lens caps, overcast north light | queued |
| Feb 1 | 2 | Carousel | Still covered? | EU 2-year minimum (named EU, hedged) | "Bought it in the EU 20 months ago? The seller may still owe you a fix." | balcony with an outdoor speaker, winter sun, terracotta pot, cool shadows | queued |
| Feb 1 | 3 | Reel | Pay once | No account | "No account. Nothing to forget, nothing to breach." | `clean` · minimal desk, keyring, white and bottle green, raking side light | queued |
| Feb 1 | 4 | Carousel | The proof kit | Valentine's gift: keep the paperwork | "Buying a watch for Valentine's Day? Keep these with it." | Exhibit: deep green velvet tray, closed watch box, folded receipt, low-key warm light | queued |
| Feb 8 | 1 | Carousel | Before the counter | Presidents' Day appliance sale: four questions | "Presidents' Day washer deal? Four questions before you pay." | empty laundry space waiting for a washer, hoses, a tape measure, flat daylight | queued |
| Feb 8 | 2 | Reel | The proof kit | Receipts one tap away | "The Valentine's gift didn't fit. The receipt is one tap away." | `clean` · bedroom dresser, gift box with tissue, soft grey morning | queued |
| Feb 8 | 3 | Carousel | The proof kit | Self-employed: work kit purchase records (no tax advice) | "Self-employed? Your work kit's receipts belong in one place." | home office, printer, shelf of binders with blank spines, late afternoon | queued |
| Feb 8 | 4 | Reel | Before the counter | Presidents' Day: the plan at the till | "Presidents' Day fridge deal. Decide on the plan before the till." | `bold` · kitchen with a new fridge still in plastic wrap, hard daylight | queued |
| Feb 15 | 1 | Reel | Make it last | Mattress care (generic; the manual says how often) | "The mattress is three years old. When did you last turn it?" | `editorial` · bedroom, linen stripped, morning sun stripes, oatmeal and sage | queued |
| Feb 15 | 2 | Carousel | Still covered? | Spring lead-in: last year's garden kit | "Bought a lawnmower last spring? Check its cover before the first cut." | garden shed, mower, damp morning, moss green, amber gloves | queued |
| Feb 15 | 3 | Reel | Three weeks too late | Protection you already pay for | "The microwave died at month 13. The extended plan was in the drawer all along." | `editorial` · office kitchenette, flickering strip light, mugs, cold palette | queued |
| Feb 15 | 4 | Carousel | Pay once | Free tier: two items free | "Two warranties free. Start with the two you'd hate to lose." | Exhibit: headphones and a coffee grinder on linen, bright daylight, one amber note | queued |

Plan totals: 71 posts — Oct 5, Nov 22, Dec 16, Jan 16, Feb 12 (by week-of
month); carousels 36, reels 35.

- Every post ends with "Download free today" (§3 lists the allowed swaps).
- The Look column is a starting point, not a script: the nightly job still checks
  `marketing-post looks` and changes anything that repeats a recent post. Reel
  rows name a reel look; the music variant follows the §5 rotation, not the row.
- Hooks may be tightened; the product + problem must stay. Hooks name dates only
  from the calendar hooks table. Ages and counts in hooks are scenarios, never
  claims about users.
- Rows that touch rights or coverage (Oct 19 #1, Dec 21 #4, Feb 1 #2, all
  Still covered? rows) follow the §3 consumer-law rules word for word.
- The nightly job may swap a row only per a §7 verdict, and must log it in §8.
- **Status** (spark#136): `queued` → `built <date> <postId>` (created, scheduled)
  → removed by `plan_prune.py` once the platform has published it. The nightly job
  builds the first `queued` row whose week starts within 7 days, one row per
  night, and writes its status here.
- Extend the plan by ~4 weeks when fewer than 4 weeks of `queued` rows remain
  (next: Feb 22 – Apr 2027 — spring appliance season, tax-refund buys, Easter
  Sun Mar 28, 2027), using the calendar hooks table; log it in §8.

## 7. 7-day review procedure

1. Every run, select posts with `status=published` published 7–13 days ago and
   not yet in §8 (Appwrite `marketing`, app `wrnty`).
2. For each post, read the metrics `collect-metrics` wrote into the post doc:
   reach, likes, comments, saves, shares (IG and FB). Note the doc's
   last-collected time.
3. Read Umami (site `fbcd006e-5e3c-456b-ad83-5a495a84c308`) for the 7 days after
   publish: pageviews with an `instagram` / `facebook` referrer and the
   `appstore-click` events. Weekly context:
   `python3 /opt/data/scripts/social_funnel_report.py --app wrnty`.
   Funnel context only — not tied to a single post (there is no `/go` hop, §2).
4. Compute **reach = IG reach + FB reach** and
   **eng = likes + comments + saves + shares** (summed across both platforms).
5. Verdict:
   - **PASS**: reach ≥ 5, or saves ≥ 1, or shares ≥ 1.
   - **FAIL**: reach ≤ 1 and eng = 0.
   - **HOLD**: anything else.
   - **NO-DATA**: metrics missing, or last-collected time > 24h old. Rerun next
     run; do not judge the post.
6. Actions:
   - PASS: keep the format + series; add one more post of that series (new
     product, new scene) to §6 within 2 weeks.
   - HOLD: no change.
   - FAIL: rewrite the next planned §6 row with the same failure pattern (e.g. a
     hook with no concrete product) to use a product + problem hook.
   - Rotate out: a format + series combo that FAILs 2 reviews in a row is replaced
     in next week's plan by the best PASS combo.
   - Saves are wrnty's main signal (carousel-led plan): when carousels PASS on
     saves and reels FAIL twice in a row, propose in §9 a shift toward carousels
     for Robert. Do not change §4 without him.
   - The §4 cadence floor always holds.
7. Re-baseline: when the median reach of the last 8 reviewed posts is ≥ 20,
   propose new thresholds in §9 for Robert. Do not change them without his
   approval.
8. Append one row per post to §8, using this template:

   ```
   | YYYY-MM-DD | <post id> "<hook>" (<format>, <series>) | IG r/l/c/s/sh · FB r/l/c/s/sh · Umami 7d ig/fb referrers, appstore-click | PASS/HOLD/FAIL/NO-DATA | <change made, or "none"> |
   ```

## 8. Learnings log

Append-only. Newest at bottom. Never edit or delete rows.

| Date | Post | Numbers | Verdict | Change |
|---|---|---|---|---|
| 2026-10-15 | CREATED: this file (spark#140) | no baseline: look ledger empty; post history not read | — | Plan week of Oct 19, 2026 – week of Feb 15, 2027 (71 rows, all `queued`); wrnty's own look (§3, §5), text-slide colours from the site's tokens, carousel-led cadence (§4). |
| 2026-10-15 | BASELINE: look ledger backfilled for wrnty | 12 backfilled posts (2026-08-16 → 2026-08-29): 7 carousel (bar layout), 3 image, incl. "$900 per year", "Black Friday is coming", "Your washing machine just died"; no metrics in the post docs (collect-metrics not run for them) | — | Baseline = backfilled ledger + funnel (0 attributed social visits, 0 store taps, 2 site visits 7d). No posts in the §7 review window (published 7–13d ago). Platform note: wrnty's app record has no Instagram credentials, only Facebook — tonight's post 6ad1072bee79697d3988 was created as Facebook-only (marketing-post dropped instagram); §9's IG/FB account question is confirmed on the IG side. |
| 2026-10-16 | 6ad2638cb35d3fb2ff4f "The washing machine broke. The receipt turned up three weeks later." (reel, Three weeks too late) | created 2026-10-16, scheduled 2026-10-25T16:00Z, Facebook-only (no Instagram credentials on the app record, as expected) | — | Built from the Oct 19 #2 row. Editorial reel 22 s, music variant 5 (c-min, unused in last 6 reels). Fresh shoot (prefix wr-social-20261016): utility-room washer puddle (hook shot is a crop of the generated frame so no control panel or brand is visible), hand on door handle, whiteboard + toolbag, dark drawer with amber highlighter, knolling exhibit; one amber object per frame. Claude design task 20261016-1843; review round 1 FAIL on the not-yet-done create/marketing.md steps and the end-card dash (fixed to ·, re-rendered); round 2 pending. Funnel 7d: 0 social visits / 0 store taps — post keeps the product feature (receipts attached) on screen per the brief. |
| 2026-10-19 | 6ad64eddb3b6d580cde9 "New laptop on the desk. Keep these five things before the box goes out." (carousel, The proof kit) | created 2026-10-19, scheduled 2026-10-26T16:00Z, Facebook-only (no Instagram credentials on the app record); 7 slides: 3 fresh photos (prefix wr-social-20261019: 00007 exhibit knolling, 00008 hand + folded receipt, 00010 blurred serial label) + 4 text slides; no metrics yet (publishes Oct 26) | — | Built from the Oct 26 #1 row. Look: home office, pale concrete desk, bottle-green mat, cool overcast top light, neutral grey-white + green + one brass accent — different setting/light from the Oct 15 kitchen and Oct 16 utility room. Deviations, logged: the amber object rendered as a small brass tool, a brass paperweight and a brass pawn instead of the design’s brass ruler (the ruler’s scale markings failed the no-readable-text rule); the slide-5 photo shows the laptop’s lid underside with a heavily blurred unreadable serial label instead of a pure bottom-shell pose (Flux could not render the exact pose after 4 attempts; it passes every §3 image rule — no visible screen content, no readable text, no logos). Funnel 7d: 0 social visits / 0 store taps, so the free receipts-&-proof feature stays on screen. Claude design task 20261019-1841; review round 1 FAIL only on the not-yet-done create/marketing.md steps; round 2 after create. |
| 2026-10-20 | 6ad7ac4d59edfc32a5b8 "Clocks change, the dryer runs every night. Clean the lint filter." (reel, Make it last) | created 2026-10-20, scheduled 2026-10-28T16:00Z, Facebook-only expected (no Instagram credentials on the app record, as expected); no metrics yet (publishes Oct 28) | — | Built from the Oct 26 #2 row. Look: clean reel (the 10-16 reel was editorial), built-in laundry cupboard at dusk, blue window + one warm bulb, oat/cream/sage/oak palette, honey-wood lint brush as the single amber object, music variant 4 (d-major; only variant 5 was used in the last 6 reels) — differs from the 10-16 utility-room reel and the 10-19 home-office carousel in setting, light, palette and look. Fresh shoot prefix wr-social-20261020 (6 stills + 2 LTX clips, 01c/05c). Deviations, logged: hook rewritten from the row ("this weekend" and "ten minutes" out per §3); honey-wood lint brush instead of the row’s mustard towel (the towel repeated the 10-16 reel); 03b rendered neutral/soft light instead of the family’s blue-vs-warm dusk; 04d manual rendered as a small blank booklet (no readable print); 06d knolling is missing the empty box after 5 render attempts — the on-screen text references the receipt, not the box. Audio: shipped the template output as-is; checks.json WARNs — true peak -0.9 dBTP (0.1 dB over the -1 target), limiter 4.1 dB on the d-major v4 bed; sample peak -1.10 dBFS (no clipping), loudness -14.1 LUFS (pass); a -0.5 dB re-encode was tried and rejected because it introduced a +2.2 dBFS inter-sample artifact. Funnel 7d: 0 social visits / 0 store taps, so the free care-notes feature stays on screen. Claude design task 20261020-1840; review round 1 FAIL only on the not-yet-done create/marketing.md steps; round 2 after update. |
| 2026-10-21 | 6ad8f2afb36e547597ef "Opened the console to clean the fan? Read the warranty first." (carousel, Fine print) | created 2026-10-21, scheduled 2026-11-01T16:00Z, Facebook-only expected (no Instagram credentials on the app record, as expected); no metrics yet (publishes Nov 1) | — | Built from the Oct 26 #3 row. 8 slides: 6 fresh photos (prefix wr-social-20261021: 00007 cover, 00011 games corner, 00003 hands, 00010 seal macro, 00005 box+receipt, 00012 quiet corner) + 2 text slides (bar layout; em dashes verified in preview). Look: games corner at night, console on a low shelf, screen off; deep slate-blue evening + one amber desk lamp; charcoal/dark oak with a bottle-green thread — differs from the 10-15 kitchen, 10-16 utility room, 10-19 office and 10-20 laundry looks in setting, light and palette. Deviations, logged: slide 1 re-rendered (first render showed a GPD-style logo and four amber screwdriver handles; final is unbranded with one amber screwdriver, and the lifted panel reads as a plain cylindrical component); slide 2 re-rendered twice (SAMSUNG and WIZX logos in attempts 1–2; final clean; the green rug rendered grey, the green thread carries as a plant + teal blanket); slide 5 (seal) re-rendered once (first read as a flake; final clearly a half-peeled blank sticker on a dark casing); slide 7 dropped the phone (a barcode label failed the no-readable-text rule) and shows the quiet corner + blank receipt on the rug, console not in frame; CTA "Download free today" sits in the body of slide 8 (the text-slide renderer has no accent CTA field); no text overlay on photo slides, so the hook is the first caption line. Schedule note: the Oct 26 / Oct 28 slots recorded in §8 were force-published on 10-19/10-20, so the 2026-11-01T16:00Z slot was free (verified via marketing-post schedule). Funnel 7d: 0 social visits / 0 store taps, so the free features (receipt photo, purchase details, proof one tap away) stay on screen. Claude design task 20261021-1838; review round 1 FAIL only on the not-yet-done create/marketing.md steps; round 2 after create. |

| 2026-10-22 | NO-OP run: §7 review window (published 7–13d ago, 2026-10-09 → 10-15) empty — the earliest published wrnty post is 6ad2638cb35d3fb2ff4f at 2026-10-19T16:45Z, outside the window | funnel 7d: 0 social visits / 0 store taps; all four October posts verified `published` (6ad2638c 10-19, 6ad64edd 10-19, 6ad7ac4d 10-20, 6ad8f2af 10-21, all force-published; Facebook-only as expected) | — | No due row: the week-of-Oct-26 rows are all published (its last row, Oct 26 #3, was force-published 10-21); the first `queued` row is Nov 2 #1 (reel, Pay once), whose week starts in 11 days — outside the 7-day due window. `plan_prune.py` removed the published Oct 26 #3 row (6ad8f2afb36e547597ef) from §6. Nothing built tonight; the Nov 2 #1 row becomes due on Oct 26. |
| 2026-10-23 | NO-OP run: §7 review window (published 7–13d ago, 2026-10-10 → 10-16) empty — the earliest published wrnty post is still 6ad2638cb35d3fb2ff4f at 2026-10-19T16:45Z, outside the window | funnel 7d: 0 social visits / 0 store taps (site totals 0 visits, prev 2); fresh Appwrite read (100 newest of 122 wrnty docs) verifies all five October posts `published` (6ad1072b 10-19, 6ad2638c 10-19, 6ad64edd 10-19, 6ad7ac4d 10-20, 6ad8f2af 10-21; Facebook-only as expected) and shows no `failed` post — the single `publishing` doc is the stale April one (69d0d274, inert) | — | No due row: the first `queued` row is Nov 2 #1 (reel, Pay once), whose week starts in 10 days (2026-11-02) — outside the 7-day due window; the Oct 30 clocks-change hook was already spent by the 10-20 post (6ad7ac4d). `plan_prune.py`: nothing to remove. Nothing built tonight; the Nov 2 #1 row becomes due on Oct 26. |

| 2026-10-25 | NO-OP run: §7 review window (published 7–13d ago, 2026-10-12 → 10-18) empty — all five October posts published 2026-10-19 → 10-21 (4–6 days old, outside the window); fresh by-id Appwrite reads today confirm all five `published` (6ad1072b 10-19, 6ad64edd 10-19, 6ad2638c 10-19, 6ad7ac4d 10-20, 6ad8f2af 10-21; Facebook-only as expected) and `marketing-post schedule` shows no `failed` post — the single `publishing` doc is the stale 69d0d274 (inert) | funnel 7d (Oct 18 → 25): 0 social visits / 0 store taps (site totals 0 visits, prev 2) | — | No due row: the first `queued` row is Nov 2 #1 (reel, Pay once), whose week starts in 8 days (2026-11-02) — outside the 7-day due window. `plan_prune.py`: nothing to remove. Nothing built tonight; the Nov 2 #1 row becomes due on Oct 26. || 2026-10-24 | NO-OP run: §7 review window (published 7–13d ago, 2026-10-11 → 10-17) empty — fresh Appwrite read today: 0 wrnty posts published in the window (earliest published is still 6ad2638cb35d3fb2ff4f at 2026-10-19T16:45Z, 5 days old) and 0 `failed` posts | funnel 7d (Oct 17 → 24): 0 social visits / 0 store taps (site totals 0 visits, prev 2) | — | No due row: the first `queued` row is Nov 2 #1 (reel, Pay once), whose week starts in 9 days (2026-11-02) — outside the 7-day due window. `plan_prune.py`: nothing to remove. Nothing built tonight; the Nov 2 #1 row becomes due on Oct 26. |

| 2026-10-26 | 6ad2638cb35d3fb2ff4f "The washing machine broke. The receipt turned up three weeks later." (reel, Three weeks too late) | IG n/a (Facebook-only post — no IG credentials on the app record) · FB reach n/a / likes 0 / comments 0 / shares 0 (fbReach null, metricsUpdatedAt 2026-10-19T18:00Z — >24h stale, never re-collected after the force-publish) · Umami 7d 0 ig / 0 fb referrers, 0 appstore-click | NO-DATA | none — re-check next run; collect-metrics has not run on this post since the 10-19 force-publish |

| 2026-10-26 | 6adf9e1b5d8917dcbc8e "Another subscription just to remember your receipts? Pay once." (reel, Pay once) | created 2026-10-26, scheduled 2026-11-04T16:00Z, Facebook-only expected (no Instagram credentials on the app record); no metrics yet (publishes Nov 4) | — | Built from the Nov 2 #1 row. Look: bright-midday white hallway, stack of opened kraft delivery boxes, amber tape gun as the single amber object, bottle-green plant in a white pot, `clean` reel, music v0 (c-major; the last two reels used v5 and v4) — differs from the recent slate-blue night, dusk laundry, cool-office and cold-utility looks in setting, light and palette. Fresh shoot prefix wr-social-20261026 (6 stills + 2 LTX clips: c1c hook push-in, c4b receipt drop; every still and every sampled clip frame passed §3 QA). Deviations, logged: scene 1 re-shot handless (s1b) with a pure camera-push-in clip (c1c) — two LTX attempts with the hand failed §3 (fused fingers, vanishing hand/tape gun, morphing); scenes 2/3/4/5/6 re-rendered once to five times (receipt face-up with faint print → blank face-down; orange staple gun + terracotta pot → tape gun + white ceramic pot; barcode on box contents and yellow pot → plain box + white pot; first clip flickered the paper → stable c4b; tape gun missing with a glass bottle → tape gun present; readable receipt text and two amber glue guns → one amber packing-tape dispenser with blank paper). Audio: -13.9 LUFS, true peak -1.4 dBTP, limiter 1.4 dB — all PASS; the render WARNed only on the generic 15–20 s Reels length hint (22.5 s is inside wrnty's own 15–30 s range, §5). File 6.9 MB, under the 9 MB upload cap. Funnel 7d: 0 social visits / 0 store taps. Claude design task 20261026-1841; review PASS round 1 (minor notes only: spec `post` field text, the pending marketing.md edits). |

| 2026-10-27 | 6ad1072bee79697d3988 "The fridge is 22 months old and the freezer just stopped. Still covered?" (carousel, Still covered?) | IG n/a (Facebook-only post — no IG credentials on the app record) · FB reach/likes/comments/shares all null (metricsUpdatedAt null, collect-metrics has never run on it) · Umami 7d 0 ig / 0 fb referrers, 0 appstore-click | NO-DATA | none — re-check next run; collect-metrics has not run on this post since the 10-19 force-publish |
| 2026-10-27 | 6ad64eddb3b6d580cde9 "New laptop on the desk. Keep these five things before the box goes out." (carousel, The proof kit) | IG n/a (Facebook-only post — no IG credentials on the app record) · FB reach/likes/comments/shares all null (metricsUpdatedAt null, collect-metrics has never run on it) · Umami 7d 0 ig / 0 fb referrers, 0 appstore-click | NO-DATA | none — re-check next run; collect-metrics has not run on this post since the 10-19 force-publish |
| 2026-10-27 | 6ae0e7a33d344deaa7af "New phone at the till, and the protection plan is on the table." (carousel, Before the counter) | created 2026-10-27, scheduled 2026-11-08T16:00Z, Facebook-only (no Instagram credentials on the app record, as expected; marketing-post dropped instagram); no metrics yet (publishes Nov 8) | — | Built from the Nov 2 #2 row. Look: kitchen table at night, warm tungsten pendant pool over dark walnut, brown/amber mood with a bottle-green thread, overhead Exhibit cover + eye-level Moments, centered text layout — differs from the recent bright-midday hallway, slate-blue games corner, dusk laundry, cool-office, cold-utility and overcast-kitchen looks in setting, light and palette. Fresh shoot prefix wr-social-20261027: 8 slides P T P T T P T T (00004 Exhibit overhead, 00005 hand + leaflet + phone box, 00007 quiet-table Moment; 00001, 00002, 00003 and 00006 re-rendered and discarded — wrong subject, box shape, or missing amber object), every final frame QA'd clean (no screens, text, faces, logos; one amber object and the green thread in each; finger count checked). Deviations, logged: photo-slide prompts shortened to fit the 2048-char serialized budget (the CLI counts photo prompts too); slides 4/5 and 7/8 are consecutive text pairs (minor, per design); the CTA sits in the body of slide 8 (the text-slide renderer has no CTA field). Text-slide total 739 serialized chars; IG caption 942 chars, FB 763 chars (a rewrite, 3 hashtags). Funnel 7d: 0 social visits / 0 store taps, so the free receipt-photo/two-items features stay on screen and no Premium features are named. Slot: Sun Nov 8 16:00Z — active day/hour per the brand data, inside the row's week, 96h from the booked 2026-11-04T16:00Z reel and clear of every other slot (verified via marketing-post schedule). Claude design task 20261027-1842-plan-tonight-s-social-post-for-wrnty-wrn; review round 1 FAIL only on the not-yet-done create/marketing.md steps; round 2 after create. |

| 2026-10-28 | 6ad7ac4d59edfc32a5b8 "Clocks change, the dryer runs every night. Clean the lint filter." (reel, Make it last) | IG n/a (Facebook-only post — no IG credentials on the app record) · FB reach null / comments 0 / shares 0 (metricsUpdatedAt 2026-10-20T20:00Z, 8 days old — >24h stale, collect-metrics has not re-run since the 10-20 force-publish) · Umami 7d 0 ig / 0 fb referrers, 0 appstore-click | NO-DATA | none — re-check next run; metrics >24h stale |
| 2026-10-28 | 6ad8f2afb36e547597ef "Opened the console to clean the fan? Read the warranty first." (carousel, Fine print) | IG n/a (Facebook-only post — no IG credentials on the app record) · FB reach/likes/comments/shares all null (metricsUpdatedAt null — collect-metrics has never run on this post since the 10-21 force-publish) · Umami 7d 0 ig / 0 fb referrers, 0 appstore-click | NO-DATA | none — re-check next run; collect-metrics has never run on this post |
| 2026-10-28 | 6ae23a9b84da969d1e25 "Singles' Day order on its way? Keep the confirmation, not just the parcel." (carousel, The proof kit) | created 2026-10-28, scheduled 2026-11-06T16:00Z, Facebook-only expected (no Instagram credentials on the app record, as expected; marketing-post dropped instagram); 6 slides P T P T P T (00005 Exhibit overhead, 00002 doorstep Moment, 00003 porch-step Moment + 3 text slides, poster layout); no metrics yet (publishes Nov 6) | — | Built from the Nov 2 #3 row. Look: doorstep and porch, cold overcast grey morning, flat even daylight, wet slate and autumn leaves, bottle-green door, one amber object per frame (amber tape spool, amber parcel tape, blank amber sticky note) — first outdoor post of the run; differs from the recent night-walnut, midday-hallway, slate-blue-games-corner, dusk-laundry, cool-office and fluorescent-utility looks in setting, light and palette; not golden hour. Fresh shoot prefix wr-social-20261028 (3 stills). Deviations, logged: slide 1 re-rendered twice — attempt 1 showed a smartphone with a visible screen (failed the no-phone rule), attempt 2 (00004) rendered two kraft tape rolls and no clear amber object, final (00005) is exactly one amber tape spool plus the green thread; slide 5 porch bench rendered as a porch step. Every final frame QA'd clean (no screens, text, faces, logos). Text-slide total 1825 serialized chars (2048 budget); IG caption 730 chars, FB 1005 chars (a rewrite, 3 hashtags, App Store link inline). Slot: Fri Nov 6 16:00Z — inside the row's week (Nov 2 week), the only future feed post in the schedule (the 2026-11-04T16:00Z reel force-published 2026-10-26T18:45Z, freeing that slot), 9.7 days after the last published post 2026-10-27T18:15Z, and ahead of Singles' Day (Nov 11) per the calendar-hooks table. Funnel 7d: 0 social visits / 0 store taps, so only the free features (confirmation photo, purchase date, two free items) are shown; no Premium feature is named. The coverage lines end with "Check the rules where you live." Claude design task 20261028-1853-plan-tonight-s-social-post-for-wrnty-wrn; review round 1 FAIL (create/marketing.md steps not yet done + slide 1 amber-object count) — fixed by the 00005 re-render and this create; round 2 after the marketing.md updates. |


| 2026-10-29 | 6ae38c9c35bffc973e9b "The headphones died at month 13. The warranty ended at month 12." (reel, Three weeks too late) | created 2026-10-29, scheduled 2026-11-04T16:00Z, Facebook-only expected (no Instagram credentials on the app record, as expected); no metrics yet (publishes Nov 4) | — | Built from the Nov 2 #4 row. Look: foggy public park at early morning, weathered oak bench with wet slats, pale misty sage-grey diffused light, moss and eucalyptus green with charcoal headphones, one amber object per frame (mustard knitted scarf / amber highlighter / blank amber sticky note), slow push-in; `editorial` reel (last two reels were `clean`), music v3 (e-min; last six reels used v5, v4, v0) — first park/fog post of the run; differs from the recent cold-overcast doorstep, night-walnut kitchen, bright-midday hallway, slate-blue games corner, dusk-laundry, cool-office and cold-utility looks in setting, light, palette and reel look; not golden hour. Fresh shoot prefix wr-social-20261029 (4 stills + 2 LTX clips; every still and 8 sampled clip frames QA'd: no screens, text, faces or logos; finger count checked on the s5 hand — 4-finger grip, natural). Deviations, logged: the first c1 attempt rendered a readable "Z" on the headphone band (failed the no-logos rule; re-shot clean as c1b); the first s4 attempt was missing the amber object (a copper plug tip is not amber; re-shot with an amber highlighter as s4b); the first s6 attempt rendered an embossed "B·mblf" logo on the case (re-shot plain as s6b); s6's receipt rendered as a blank sticky note instead of a folded receipt — the on-screen text says nothing about the receipt, so it passes every rule; audio true-peak WARN -0.3 dBTP (limiter 1.5 dB, loudness -13.9 LUFS pass — the template output shipped as-is, same class of deviation as the 10-20 reel). Audio: music v3 (e-min), clips off. Render: 24.5 s, 1080x1920, 8.3 MB (under the ~9 MB upload cap); checks.json 10 PASS, 1 WARN (true peak), no ERROR. Slot: Wed Nov 4 16:00Z — active day/hour per the brand data, inside the row's week (Nov 2), 48 h from the booked 2026-11-06T16:00Z carousel and 6.9 days after the last published post 2026-10-28T18:15Z (verified via marketing-post schedule). Funnel 7d (Oct 22-29): 0 social visits / 0 store taps, so the Premium expiry-reminders feature stays on screen in three text beats with "Premium" beside it; "free" appears only in the end card and CTA, never next to the reminders line. Claude design task 20261029-1843-plan-tonight-s-social-post-for-wrnty-wrn; review round 1 FAIL only on the not-yet-done create/marketing.md steps; round 2 after create. |

## 9. Open questions & watch items

- **Instagram / Facebook account unknown** (owner: *Robert*) — the app record's
  `instagramHandle` is null and the site links to no social profile. Confirm that
  wrnty has IG + FB accounts connected to the marketing platform (and set the
  handle in the app record). Until then `publish-social` can fail and posts come
  back as `failed`.
- **No `/go/?src=` hop on wrnty.12f.dk** (owner: *Robert*) — `/go/` answers 404,
  so social visits show up only as referrers and a store tap cannot be tied to a
  platform. Add the hop the sister sites use (Event Stories'
  `docs/social-source-links.md`), then set the bio links.
- **Bio link** (owner: *Robert*) — the bio points to `https://wrnty.12f.dk/` for
  now; change it to the tracked `/go` link once the hop exists.
- **Real app footage** (owner: *Robert*) — none in `12fdk/motion`. The app repo
  has a preview-video pipeline (`fastlane/previews/`, `make videos-all`; the
  `.mp4` files are git-ignored). Render the en-US walkthrough and copy it to
  `/workspace/motion/assets/wrnty/` to allow app UI in reels; then §3's footage
  rule changes (Robert's say-so).
- **Baseline unknown** (owner: Hermes) — the look ledger is empty and past wrnty
  posts were not read when this file was written. On the first run: run
  `marketing-post ledger-backfill --app wrnty` once, read the app's published
  posts, and log a BASELINE row in §8.
- **App record vs site** (owner: *Robert*) — the app record says "works offline",
  "receipt scanning demos", "100% private" and "75% of consumers lose track of
  warranties". The site says none of these, and the blog brief says the app
  does not read receipt text. §2 bans them in posts; fix the app record or add
  the claims to the site with a source.
- **CTA left out** (owner: *Robert*) — "Never miss a warranty claim again" from
  ctaOptions is not in §3: it promises an absolute, and reminders are Premium.
  "Stop losing money on expired warranties", "Your receipts deserve better",
  "download" and "comment below" are also unused. Decide whether to add any.
- **Style preset** (owner: *Robert*) — the app record's `comfyuiStylePreset`
  says "natural golden hour light"; §3 limits golden hour to one post in five so
  posts keep looking new. Consider a preset without a fixed light.
- **Stories decision** (owner: *Robert*) — the app record wants daily stories
  (polls, quick tips); the pipeline is feed-only today.
- **Audience markets** (owner: *Robert*) — the app record's audience is US
  (income in $), while the site is international (28 app languages, built in
  Denmark). The plan mixes US deal days (Black Friday, Presidents' Day) with
  global and UK ones (Singles' Day, Boxing Day). Check the IG/FB audience by
  country after the first month and swap rows if needed.
- **Upload size cap** (owner: Hermes) — found on Event Stories 2026-10-15: the
  platform's upload path rejects request bodies between 8 and 12 MB. Keep reels
  under ~9 MB (2-pass h264 ~2.6 Mbps + aac 128k fits a 30 s 1080x1920 reel).
- **Blog brief links** (owner: Hermes) — two FTC URLs in `prompt.md`'s vetted
  source list (`consumer.ftc.gov/articles/warranties` and
  `.../extended-warranties-and-service-contracts`) answered 404 on 2026-10-15.
  Not used here; check them before the blog job cites them again.
- **Umami ingestion lag** (owner: Hermes) — do not read the funnel as final for
  the last 24–48h. `optimize-guidelines` is dormant — enable once §8 has ≥ 4
  weeks of logs.
