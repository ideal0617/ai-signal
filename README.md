# Daily Digest

Track the builders shaping AI, energy, and investing — not the influencers.

A centralized feed aggregates raw content from 15+ top podcasts and 20+ curated Twitter/X accounts daily. Your AI agent (Claude Code) pulls the feed and generates a personalized digest based on your preferences.

**No API keys needed for content** — all feeds are fetched centrally and committed to this repo.

## What You Get

A daily digest pushed to Telegram, Feishu, email, or displayed in your chat:

- Podcast episode summaries with key insights and quotes
- Twitter/X highlights from builders, researchers, and executives
- Filtered by your interests (AI, energy, investing)
- In your language (English, Chinese, or bilingual)
- At your preferred depth (highlights, summary, or full analysis)

## Quick Start

### Claude Code

```bash
git clone https://github.com/Benboerba620/daily-digest.git ~/.claude/skills/daily-digest
cd ~/.claude/skills/daily-digest/scripts && pip install -r ../requirements.txt
```

Then tell Claude: **"set up daily digest"** — it will walk you through configuration.

### Manual Run

```bash
# Fetch latest feeds and generate your digest
python scripts/prepare_digest.py | your-llm-of-choice
```

## Customization

Everything is customizable through conversation with your agent:

| Setting | Options | Example |
|---------|---------|---------|
| Language | `en`, `zh`, `bilingual` | "Switch to Chinese" |
| Depth | `highlights`, `summary`, `full` | "Make it more detailed" |
| Domains | `ai`, `energy`, `invest` | "Only show AI" |
| Delivery | Telegram, Feishu, email, chat | "Push to Telegram" |

### Custom Prompts

Control how content is summarized by editing files in `~/.daily-digest/prompts/`:

- `summarize-podcast.md` — how podcast episodes are summarized
- `summarize-tweets.md` — how tweets are distilled
- `digest-intro.md` — overall digest tone and format

These are plain text instructions, not code. Changes take effect on the next run.

## Sources

### Podcasts (15 channels)

| Channel | Domain |
|---------|--------|
| [Dwarkesh Patel](https://www.dwarkesh.com) | AI |
| [Lex Fridman](https://lexfridman.com/podcast/) | AI |
| [Latent Space](https://www.latent.space) | AI |
| [All-In Podcast](https://www.allinpodcast.co) | AI |
| [a16z](https://a16z.com/podcasts/) | AI |
| [No Priors](https://www.youtube.com/@NoPriorsPodcast) | AI |
| [Google DeepMind Podcast](https://deepmind.com/podcast) | AI |
| [Lightcone (YC)](https://www.youtube.com/@ycombinator) | AI |
| [Lenny's Podcast](https://www.lennysnewsletter.com/) | AI |
| [Macro Voices](https://www.macrovoices.com) | Energy |
| [Super-Spiked](https://arjunmurti.substack.com) | Energy |
| [Columbia Energy Exchange](https://www.energypolicy.columbia.edu/podcast) | Energy |
| [Invest Like the Best](https://www.joincolossus.com/episodes) | Invest |
| [Capital Allocators](https://capitalallocators.com/podcast/) | Invest |
| [The Acquirers Podcast](https://acquirersmultiple.com/podcast/) | Invest |

### Twitter/X (20 accounts)

**AI Analysts**: [@karpathy](https://x.com/karpathy), [@swyx](https://x.com/swyx), [@dylanpatel_](https://x.com/dylanpatel_), [@leopoldaob](https://x.com/leopoldaob), [@jimkeller_](https://x.com/jimkeller_)

**AI Executives**: [@sama](https://x.com/sama), [@DarioAmodei](https://x.com/DarioAmodei), Demis Hassabis, Jensen Huang, Satya Nadella

**AI Builders**: [@AmandaAskell](https://x.com/AmandaAskell), [@bcherny](https://x.com/bcherny), [@_catwu](https://x.com/_catwu), [@alexalbert__](https://x.com/alexalbert__), [@rauchg](https://x.com/rauchg), [@amasad](https://x.com/amasad), [@joshwoodward](https://x.com/joshwoodward)

**Energy**: [@ArjunMurti](https://x.com/ArjunMurti), [@DoombergT](https://x.com/DoombergT), [@JavierBlas](https://x.com/JavierBlas)

## How It Works

```
Central (this repo, GitHub Actions daily)
  └── generate_feed.py → raw tweets + podcast transcripts
      → feed-x.json, feed-podcasts.json (committed to repo)

Your machine (Claude Code skill)
  └── prepare_digest.py → pulls feeds from this repo
      → your LLM summarizes per your preferences
      → deliver.py → push to your Telegram / Feishu / email
```

## For Developers

### Run the central feed generator locally

```bash
pip install -r requirements.txt
export TWITTER_COOKIES="..."  # from browser F12
python scripts/generate_feed.py
```

### Add sources

Edit `config/sources.json` to add Twitter accounts or podcast RSS feeds. PRs welcome.

## Privacy

- No API keys needed for content access
- Your config and preferences stay on your machine (`~/.daily-digest/`)
- Only public content is aggregated (public tweets, public podcasts)

## License

MIT
