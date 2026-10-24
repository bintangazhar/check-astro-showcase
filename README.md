# astro-showcase

CLI tool to check which page a site appears on in [Astro.build Showcase](https://astro.build/showcase/) and verify if a site uses Astro.

## Install

**Download binary (Linux/macOS/Windows):**
- [Latest Release](https://github.com/bintangazhar/check-astro-showcase/releases)

**Or build from source:**
```bash
git clone https://github.com/bintangazhar/check-astro-showcase.git
cd check-astro-showcase
pip install -r requirements.txt  # or: pip install aiohttp
```

## Usage

```bash
# Check specific sites + verify Astro usage
astro-showcase mainbranch.dev bintang.me nusantarapost.news --check-astro

# Output as JSON
astro-showcase site1.com site2.com --check-astro --output json

# List all sites in showcase (slow, scans 109 pages)
astro-showcase --all
```

## Example Output

```
mainbranch.dev                 | Page 29      | ✅ Uses Astro
                                 └─ Generator meta: Astro v7.2.8
                                 └─ Astro island/cid attributes found
                                 └─ Astro asset prefix /_astro/ found
bintang.me                     | Page 56      | ✅ Uses Astro
                                 └─ Astro island/cid attributes found
                                 └─ Astro asset prefix /_astro/ found
nusantarapost.news             | Not found    | ✅ Uses Astro
                                 └─ data-astro-cid attributes found
                                 └─ Astro asset prefix /_astro/ found
```

## How it works

1. Fetches showcase pages (`/showcase/`, `/showcase/2/`, ... `/showcase/109/`)
2. Searches for domain in page HTML
3. Optionally fetches the site and checks for Astro markers:
   - `<meta name="generator" content="Astro vX.Y.Z">`
   - `data-astro-cid` attributes
   - `/_astro/` asset prefix
   - Astro island/hydration scripts

## License

MIT