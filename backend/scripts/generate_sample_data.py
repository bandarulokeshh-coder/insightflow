"""
Generate sample_data/feedback.csv — realistic, messy, multilingual customer
feedback for a fictional Indian quick-commerce company ("Zestly").

Deliberately INCLUDES the noise the Feedback Refinery is meant to fix:
  • exact duplicates            • transliterated Hindi/Telugu/Tamil mixed with English
  • typos and shorthand         • emoji, inconsistent casing and spacing
  • sparse metadata             • a rising complaint wave in recent months

Run:  python backend/scripts/generate_sample_data.py
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

OUT = Path(__file__).resolve().parents[2] / "sample_data" / "feedback.csv"

PRODUCTS = ["Groceries", "Fresh Produce", "Electronics", "Personal Care", "Home Care", "Dairy & Bakery"]
CHANNELS = (["app_store"] * 90 + ["support"] * 60 + ["survey"] * 75 +
            ["review"] * 60 + ["social"] * 25 + ["form"] * 10)
CITIES = ["Hyderabad", "Bengaluru", "Chennai", "Mumbai", "Pune", "Delhi", "Vijayawada", "Warangal"]
NAMES = ["Ananya", "Rahul", "Sneha", "Vikram", "Priya", "Arjun", "Kavya", "Rohit", "Divya", "Kiran",
         "Meera", "Naveen", "Shruti", "Aditya", "Ishita", "Manoj", "Pooja", "Sandeep", "Aisha", "Tarun",
         "Lakshmi", "Gaurav", "Nithya", "Harish", "Ritu", "Sameer", "Anjali", "Varun", "Deepa", "Karthik"]

T = {
    "Delivery": {
        "negative": [
            "Delivery was {d} late and the rider never called. Food was cold by the time it arrived.",
            "My order was supposed to arrive in 15 minutes, it came after 50 minutes. Delivery is getting worse.",
            "Rider marked the order as delivered but I never received it. Very disappointed with delivery.",
            "Third time this month the delivery is late with zero update. The ETA means nothing.",
            "Courier left my parcel at the wrong gate and it was delivered to a neighbour. Unacceptable.",
            "Tracking showed 'arriving in 5 minutes' for an hour. Delivery experience is terrible now.",
            "The delivery rider was rude when I asked about the delay. Made me wait 20 minutes downstairs.",
            "Order arrived an hour late, items were spilled inside the bag. Late delivery plus damaged items.",
        ],
        "positive": [
            "Delivery was super fast, arrived in 11 minutes and everything was fresh. Love this app!",
            "The rider was polite and handed the order on time. Delivery experience was smooth.",
            "Fastest delivery I have had in {city}, well packed and on time. Great work by the team.",
            "Delivery arrived before the promised ETA and the rider even called to confirm the gate. Excellent.",
        ],
        "neutral": [
            "Delivery took the usual 20 minutes, nothing special. Items were fine.",
            "Order arrived on time but the app tracking kept showing the old status for a while.",
        ],
    },
    "App Bug": {
        "negative": [
            "The app crashes every time I open the cart. Latest update broke checkout completely.",
            "Cannot login since yesterday, OTP screen goes blank. App bug is blocking my order.",
            "After the new update the app freezes on the home screen and I have to force close it.",
            "My cart empties itself randomly. This glitch has cost me two orders this week.",
            "App gets stuck at the payment screen and then shows an error. Have to reinstall every time.",
            "Login with my number fails and I get logged out after every order. Please fix this bug.",
            "The app closes whenever I tap on the offers tab. Reinstalling did not help.",
        ],
        "positive": [
            "New update fixed the crash I had during checkout. App feels smooth now.",
            "The app is quick, no bugs found so far and login with fingerprint is convenient.",
        ],
        "neutral": ["The app works fine but the offers tab loads very slowly sometimes."],
    },
    "Refund": {
        "negative": [
            "Refund still not credited after 9 days. Customer support keeps saying 48 hours.",
            "I cancelled the order within a minute and the refund was deducted as a cancellation fee. Money is stuck.",
            "Returned the damaged item but the refund never came. I have been chasing this for two weeks.",
            "Refund of ₹{amount} pending since last month with no update. This is my money, please return it.",
            "The app shows refund completed but nothing was credited to my wallet or bank. Very frustrating.",
            "Cancelled order, no refund, no reason given. I want my money back immediately.",
        ],
        "positive": [
            "Refund was processed within a day without me asking. Very impressed with the service.",
            "Got my refund instantly on cancellation, no follow up needed. Smooth experience.",
        ],
        "neutral": ["Refund came through after 4 days, slower than promised but it arrived."],
    },
    "Billing": {
        "negative": [
            "I was charged twice for the same order. Invoice shows one charge but my UPI shows two. Please reverse.",
            "Surge fees and handling charges appear at checkout only, hidden from the price shown earlier. Misleading.",
            "My {product} subscription renewed without any reminder and I was charged ₹{amount}. I never opted for auto-renew.",
            "Overcharged for items that were marked on discount. The bill was {amount} more than the cart total.",
            "The invoice does not match the amount charged. Support says 'some taxes' but nothing is itemised.",
            "Prime membership was charged even after I cancelled it last month. Please refund the fee.",
        ],
        "positive": ["Pricing is transparent and the invoice matched the cart exactly. No surprise charges."],
        "neutral": ["Charges were correct but the fee breakdown on the invoice is confusing."],
    },
    "Support": {
        "negative": [
            "Customer support is useless, three chats and nobody has responded with a real answer.",
            "The support agent was rude and disconnected the chat when I asked for a supervisor.",
            "Raised a ticket 6 days ago, no response at all. Support keeps transferring me between teams.",
            "Chatbot loops the same answers and there is no option to talk to a human. Unhelpful support.",
            "When I called the helpline I was on hold for 25 minutes and then the call dropped.",
        ],
        "positive": [
            "Support resolved my issue in one chat, the agent was polite and quick. Great customer care.",
            "The agent called me back with an update without me asking. Very responsive support team.",
        ],
        "neutral": ["Support replied after a day and the issue is partly resolved."],
    },
    "Product Quality": {
        "negative": [
            "The {product} was stale and smelled bad. Quality has dropped badly in the last few weeks.",
            "Received a damaged and expired item in fresh produce. This is a health risk, please check your vendors.",
            "The vegetables were rotten and half of the packet was spoiled. Very poor quality check.",
            "Wrong item delivered and it was a damaged duplicate of what I ordered. Disappointed.",
            "Undercooked and burnt at the same time, definitely from a different kitchen than before.",
        ],
        "positive": [
            "The {product} was fresh and the quality was excellent for the price. Will order again.",
            "Everything was fresh, well within expiry and tasted great. Quality is consistent.",
        ],
        "neutral": ["Quality was okay, nothing exceptional. One item was slightly bruised."],
    },
    "Packaging": {
        "negative": [
            "The milk packet leaked inside the bag and spoiled other groceries. Packaging needs a fix urgently.",
            "Packaging was torn, the seal was broken and the delivery bag was leaking all over.",
            "Container was not sealed properly, oil spilled on everything else in the order.",
            "Fragile items were packed with no protection and arrived crushed.",
        ],
        "positive": [
            "Packaging was neat and eco friendly, nothing spilled or crushed. Well done.",
            "Everything arrived sealed and well wrapped, even the glass bottles. Great packing.",
        ],
        "neutral": ["Packaging was fine but very bulky for two small items."],
    },
    "App UX": {
        "negative": [
            "The new UI is confusing, search filters do not work and I cannot find my usual items.",
            "Checkout flow is cluttered with too many steps. The old design was much easier.",
            "Search is broken, it shows unrelated items and the categories are a mess now.",
            "Dark mode is missing and the font is too small to read on the cards. Please improve the interface.",
        ],
        "positive": [
            "The redesigned interface is beautiful and search is finally fast. Great UX.",
            "Love the new dark mode and the cleaner layout. Much easier to reorder favourites.",
        ],
        "neutral": ["The new layout takes getting used to. Some buttons moved but it works."],
    },
    "Performance": {
        "negative": [
            "The app is very laggy, images take ages to load and it drains battery fast.",
            "Home screen takes 2 minutes to load on 4G. Performance has become terrible after the update.",
            "App hangs whenever I scroll the offers page, constant loading spinners.",
            "Battery drain is huge, the app keeps running in background and phone heats up.",
        ],
        "positive": ["App is lightning fast now and loads in a second even on 4G. Great performance."],
        "neutral": ["App performance is fine but the first load of the day is slow."],
    },
    "Payments": {
        "negative": [
            "UPI payment failed but the amount was debited. Transaction shows failed and no order was placed.",
            "Card payment declined three times and then cash on delivery was blocked. Payment gateway issues.",
            "OTP for payment never arrived and the order timed out. Money on hold for 3 days now.",
            "Payment stuck in processing for 2 hours, neither order confirmed nor refund received.",
        ],
        "positive": ["UPI payment went through instantly and the order was confirmed in seconds."],
        "neutral": ["Payment worked but the gateway screen took a while to redirect back to the app."],
    },
}

# Transliterated multilingual feedback (Hinglish / Telugu-English / Tamil-English / Kannada-English)
MULTILINGUAL = [
    ("Delivery bahut late aayi, rider ne call bhi nahi kiya. Khana thanda ho gaya.", "Delivery", "negative", 1),
    ("Mera refund abhi tak nahi aaya, paise wapas karo. Bahut kharab service hai.", "Refund", "negative", 1),
    ("App bar bar crash ho raha hai, cart khulta hi nahi. Please fix karo jaldi.", "App Bug", "negative", 1),
    ("Quality bahut kharab thi, {product} stale tha aur smell bhi aa rahi thi.", "Product Quality", "negative", 1),
    ("Support ne koi jawab nahi diya, 3 din se ticket pending hai. Bahut frustrating.", "Support", "negative", 2),
    ("Mujhe double charge hua hai, do baar paise cut gaye. Refund karo please.", "Billing", "negative", 1),
    ("Packaging kharab thi, milk packet leak ho gaya poore bag mein.", "Packaging", "negative", 1),
    ("Order chala late ayyindi, food antha cold ayyipoyindi. Chala baadha ga undi.", "Delivery", "negative", 1),
    ("Naaku refund ravatam ledu, 10 days ayyindi. Money back ivvandi please.", "Refund", "negative", 1),
    ("App chala slow ga undi, loading chala time teesukuntundi. Sariga pani cheyyatam ledu.", "Performance", "negative", 2),
    ("Delivery chala fast ga vachindi, items fresh ga unnayi. Chala bagundindi!", "Delivery", "positive", 5),
    ("Payment double ayindi, naa account nunchi rendu sarlu cut ayyindi.", "Billing", "negative", 1),
    ("Delivery romba late aachu, items ellam cold aayiduchu. Romba mosam.", "Delivery", "negative", 1),
    ("Refund innum varala, naan romba kashtapadren. Please money back kudunga.", "Refund", "negative", 1),
    ("App romba slow, loading time romba jasthi. Seri illa.", "Performance", "negative", 2),
    ("Delivery thumba late aaythu, aa mele items damaged aagide. Thumba kasta.", "Delivery", "negative", 1),
    ("Refund innu bandilla, naaku dhanyavada heli paisa kodu please.", "Refund", "negative", 1),
]

# extra clauses appended to some rows so the corpus isn't template-identical
EXTRA = {
    "Delivery": ["The rider didn't even apologise.", "This was my third order this week with the same problem.",
                 "Please improve the ETA calculation at least.", "I had to reheat everything."],
    "App Bug": ["Please fix this in the next update.", "I have reported this twice already with screenshots.",
                "Clearing cache did not help either.", "It happens on both Android and iPhone."],
    "Refund": ["Please escalate this, it is urgent.", "I have the payment screenshots if needed.",
               "Nobody from your team has called me back.", "This is the second time this month."],
    "Billing": ["Please check my account history.", "The math simply does not add up.",
                "I have screenshots of both charges.", "Kindly review before charging customers again."],
    "Support": ["Please assign someone senior to this.", "I just want a human to read my message.",
                "Every agent says the same scripted line.", "At this point I am considering switching apps."],
    "Product Quality": ["Please audit your supplier for this item.", "I had to throw the whole thing away.",
                        "This is not the quality I paid for.", "Second time receiving a bad batch."],
    "Packaging": ["Please use better bags and seals.", "Half the order was wasted because of this.",
                  "The delivery bag itself was soaked.", "This keeps happening with liquids."],
    "App UX": ["Please bring back the simpler design.", "You can test this on any older phone.",
               "I spend more time searching than ordering now.", "The old app was much better."],
    "Performance": ["Please optimise the home feed.", "It used to be quick when I first installed it.",
                    "This happens on WiFi as well as mobile data.", "My phone is not old, by the way."],
    "Payments": ["Please confirm where my money is.", "I have bank SMS as proof.",
                 "The support team just closed my ticket.", "Please fix the payment retry flow."],
}

PREFIXES = ["Honestly, ", "Update: ", "Day 3: ", "Seriously, ", "FYI, ", ""]


TYPO_MAP = [("received", "recieved"), ("delivery", "delievery"), ("refund", "refnd"),
            ("payment", "paymnt"), ("customer", "custmer"), ("package", "pakage"),
            ("quality", "qualtiy"), ("wrong", "worng")]
EMOJIS = ["😡", "😤", "🙏", "😊", "👍", "🤬", "😞", "❤️", "🔥", "👎", "😭"]
SHORTHAND = ["pls", "plz", "thx", "bt", "u"]


def fill(t: str) -> str:
    return (t.replace("{product}", random.choice(PRODUCTS).lower())
             .replace("{amount}", str(random.choice([99, 149, 199, 249, 349, 499, 799])))
             .replace("{city}", random.choice(CITIES))
             .replace("{d}", str(random.choice([20, 30, 45, 60, 90]))))


def noise(text: str) -> str:
    r = random.random()
    if r < 0.07:
        for good, bad in TYPO_MAP:
            if good in text:
                text = text.replace(good, bad, 1)
                break
    if r > 0.82:
        text = f"{text} {random.choice(EMOJIS)}"
    if r > 0.92:
        word = random.choice(SHORTHAND)
        text = text.replace("please", word, 1) if "please" in text else f"{word} {text[0].lower()}{text[1:]}"
    if r < 0.03:
        text = text.replace("  ", " ").replace("the", " d", 1)
    return text


def main() -> None:
    rows = []

    # weighted topic distribution — Delivery/Refund/App Bug dominate (realistic for q-commerce)
    topic_weights = [("Delivery", 58), ("App Bug", 46), ("Refund", 42), ("Support", 34),
                     ("Product Quality", 36), ("Billing", 28), ("Packaging", 20),
                     ("App UX", 20), ("Performance", 16), ("Payments", 18)]
    topics = [t for t, w in topic_weights for _ in range(w)]

    sentiment_mix = [("negative", 0.55), ("positive", 0.30), ("neutral", 0.15)]

    n = 300
    for _ in range(n):
        topic = random.choice(topics)
        r = random.random()
        sentiment = "negative" if r < 0.55 else ("positive" if r < 0.85 else "neutral")
        pool = T[topic].get(sentiment) or T[topic]["negative"]
        text = fill(random.choice(pool))
        # combine clauses + prefixes + order refs so the corpus isn't template-identical
        if random.random() < 0.6:
            text = f"{text} {random.choice(EXTRA.get(topic, ['']))}"
        if random.random() < 0.22:
            text = f"{random.choice(PREFIXES)}{text[0].lower()}{text[1:]}"
        ref = f"ZQ{random.randint(10000, 99999)}"
        if random.random() < 0.5:
            text = f"Order #{ref}: {text}"
        elif random.random() < 0.3:
            text = f"{text} (Order #{ref})"
        text = noise(text)
        if sentiment == "negative":
            rating = random.choice([1, 1, 2])
        elif sentiment == "positive":
            rating = random.choice([4, 5, 5])
        else:
            rating = 3
        rows.append({
            "author": random.choice(NAMES),
            "channel": random.choice(CHANNELS),
            "product": random.choice(PRODUCTS) if random.random() < 0.75 else "",
            "rating": rating if random.random() < 0.8 else "",
            "text": text,
        })

    # multilingual rows
    for text, topic, sentiment, rating in MULTILINGUAL:
        rows.append({
            "author": random.choice(NAMES), "channel": random.choice(CHANNELS),
            "product": random.choice(PRODUCTS) if random.random() < 0.6 else "",
            "rating": rating, "text": fill(text),
        })
        if random.random() < 0.6:  # repeat a couple, as real imports do
            rows.append(dict(rows[-1], author=random.choice(NAMES)))

    # exact duplicates (~7%) — these get flagged by the deduplication recipe
    n_dupes = int(len(rows) * 0.07)
    for _ in range(n_dupes):
        src = random.choice(rows)
        rows.append(dict(src, author=random.choice(NAMES)))

    # near duplicates
    for _ in range(15):
        src = random.choice(rows)
        txt = src["text"].replace("very", "really").replace("app", "application")
        rows.append(dict(src, text=txt))

    # dates: 10 months, with a NEGATIVE WAVE in the last ~2 months (delivery/refund/billing/support)
    start = datetime(2025, 12, 1)
    end = datetime(2026, 10, 10)
    span = (end - start).days
    out = []
    for row in rows:
        hot = any(k in row["text"].lower() for k in
                  ["late", "refund", "charged", "support", "leaked", "crash", "laggy", "stale"]) \
            and _is_neg(row)
        if hot and random.random() < 0.72:
            day = random.randint(int(span * 0.80), span)       # recent wave
        else:
            day = random.choices(range(span), weights=[1 + i * 0.12 for i in range(span)])[0] \
                if random.random() < 0.5 else random.randint(0, span)
        ts = start + timedelta(days=day, hours=random.randint(7, 22), minutes=random.randint(0, 59))
        row["date"] = ts.strftime("%Y-%m-%dT%H:%M:%S")
        out.append(row)

    out.sort(key=lambda r: r["date"])
    random.shuffle(out)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["author", "channel", "product", "rating", "date", "text"])
        writer.writeheader()
        writer.writerows(out)

    print(f"Wrote {len(out)} rows → {OUT}")


def _is_neg(row: dict) -> bool:
    return row.get("rating") in (1, 2, 1.0, 2.0)


if __name__ == "__main__":
    main()
