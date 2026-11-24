# YNAB Amazon Categorizer

> **Project Status: Unmaintained / Archived**
>
> Development on this project has concluded because the original author no longer uses YNAB. This final release is left in a clean, tested, self-contained state for anyone who wishes to use it as-is or fork it to continue maintenance.

A Python CLI tool that assists in categorizing Amazon transactions in YNAB (You Need A Budget) with rich item information, automatic memo generation, tax-aware splitting, and tab-completion for categories.

## Features

When you paste in the text from your Amazon order page:

- **Smart Order Matching**: Automatically matches YNAB transactions with Amazon orders by amount and date
- **Enhanced Memos**: Generates detailed memos with item names and direct Amazon order links
- **Tax-Aware Splitting**: Suggests splitting multi-item transactions and computes sales tax from pre-tax item prices
- **Streamlined Workflow**: Smart defaults, tab completion, and batch memo enrichment
- **Digital & Subscription Orders**: Recognizes physical, digital, and subscription order IDs
- **UTF-8 Support**: Full emoji support in category names (including Windows consoles)
- **Rich Previews**: Shows category names and transaction details before sending updates

The parser supports English-language Amazon order pages with month-first or day-first English dates and `$`, `CA$`, `CDN$`, `US$`, `£`, or `€` totals. Translated order-page labels and comma-decimal totals are not currently supported.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or standard Python tooling
- YNAB account with API access

## Installation

### Method 1: Run with uvx (Recommended)

```bash
# Run directly without installing (fastest and cleanest)
uvx ynab-amazon-categorizer
```

### Method 2: Install as a tool

```bash
# Install globally with uv
uv tool install ynab-amazon-categorizer

# Then run
ynab-amazon-categorizer
```

### Method 3: Development Installation

```bash
# Clone the repository
git clone https://github.com/dizzlkheinz/ynab-amazon-categorizer.git
cd ynab-amazon-categorizer

# Install project and development dependencies
uv sync --extra dev
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture notes, checks, and release instructions.

## Configuration Setup

After installation, set up your YNAB API credentials via a `.env` file or environment variables.

### Configuration File (.env)

Create a `.env` file in your working directory (see [`.env.example`](.env.example)):

```env
YNAB_API_KEY=your_api_key_here
YNAB_BUDGET_ID=your_budget_id_here
YNAB_ACCOUNT_ID=none
```

For predictable credential selection, only the current working directory is checked; parent directories are not searched for `.env` files.

### Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `YNAB_API_KEY` | Yes | — | YNAB Personal Access Token |
| `YNAB_BUDGET_ID` | Yes | — | Target YNAB budget ID |
| `YNAB_ACCOUNT_ID` | No | `none` | Specific YNAB account ID (`none` processes all accounts) |
| `AMAZON_DOMAIN` | No | `amazon.ca` | Amazon domain used when building order links |
| `YNAB_DEFAULT_TAX_RATE` | No | `0.09` | Default sales tax rate for pre-tax split entry (9%) |
| `YNAB_GROCERY_TAX_RATE` | No | `0.045` | Sales tax rate for categories containing `grocery` or `groceries` (4.5%) |
| `YNAB_SKIP_SPLIT_PROMPT_SINGLE_ITEM` | No | `false` | Set to `1`/`true`/`yes`/`y` to skip the split prompt when an order does not have multiple items |

```bash
# Windows (cmd)
set YNAB_API_KEY=your_api_key_here
set YNAB_BUDGET_ID=your_budget_id_here

# Mac/Linux
export YNAB_API_KEY=your_api_key_here
export YNAB_BUDGET_ID=your_budget_id_here
```

## Getting Your YNAB Credentials

### API Key
1. Go to [YNAB Developer Settings](https://app.ynab.com/settings/developer)
2. Click "New Token"
3. Copy the generated token

### Budget ID
1. Open your budget in YNAB
2. Look at the URL: `https://app.ynab.com/[budget_id]/budget`
3. Copy the `budget_id` part

### Account ID (Optional)
1. Click on a specific account in YNAB
2. Look at the URL: `https://app.ynab.com/[budget_id]/accounts/[account_id]`
3. Copy the `account_id` part (or leave as `none` to process all accounts)

## Usage

### Basic Usage

```bash
# Run with uvx (no installation needed)
uvx ynab-amazon-categorizer

# Or if installed as a tool
ynab-amazon-categorizer

# Or run as a Python module
python -m ynab_amazon_categorizer
```

### Dry run

Use `--dry-run` to walk through the full flow and preview every update without sending any changes to YNAB:

```bash
ynab-amazon-categorizer --dry-run
```

The tool still shows the JSON preview for each transaction but skips the API write, so it is safe for trying the tool out or verifying matches.

### Batch mode

Use `--batch` to run non-interactively: for every transaction with a single high-confidence order match (unique exact-amount match within 7 days), the tool sets the memo (items + order link) automatically and **leaves the category unchanged**, so you can still review/categorize later. Transactions with no match or an ambiguous match are skipped.

Existing memo text is preserved and the Amazon context is appended. If the existing memo is too long to retain in full alongside at least the order link, the transaction is skipped rather than truncating user data.

```bash
# Preview what batch mode would enrich
ynab-amazon-categorizer --batch --dry-run

# Apply memo enrichment
ynab-amazon-categorizer --batch
```

You still paste the Amazon orders page once when prompted; `--batch` only removes per-transaction prompting.

### Including reconciled transactions

Uncategorized transactions that are already reconciled are excluded by default. Pass `--include-reconciled` to surface them as well (combine with `--dry-run` to inspect suggested matches without writing to YNAB):

```bash
ynab-amazon-categorizer --include-reconciled --dry-run
```

### Workflow

1. **Provide Amazon Orders Data** (optional but recommended):
   - Copy your Amazon orders page content (e.g., from your Amazon Order History page, select all and copy)
   - Run the tool and paste Amazon order info when prompted
   - The script automatically matches transactions with orders (and auto-skips transactions with no matching order when order data was provided)

2. **Review Matched Transactions**:
   - Shows order details, items, and links before asking to categorize
   - For multiple items, suggests splitting the transaction

3. **Categorize & Split Transactions**:
   - Use tab completion to select categories
   - When splitting, enter a pre-tax base price to have sales tax added automatically (4.5% for grocery categories, 9% otherwise, configurable via env vars), prefix with `=` for an exact charged total without tax math, or press Enter on a blank line to use the full remaining balance as-is
   - Accept suggested memos or customize them
   - Confirm updates with JSON previews

### Keyboard Shortcuts

- **Tab**: Auto-complete category names
- **Enter**: Accept defaults (categorize, use suggested memo, confirm update)
- **Alt+Enter**: Submit multiline input (Amazon orders data, custom memos)
- **`b` or two consecutive blank Enters**: Go back during category selection
- **Ctrl+C**: Cancel current operation

## Example Output

```
  🎯 MATCHED ORDER FOUND:
     Order ID: 702-8237239-1234567
     Total: $57.57
     Date: July 31, 2025
     Order Link: https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID=702-8237239-1234567
     Items:
       - Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
       - Fancy Feast Grilled Wet Cat Food, Salmon & Shrimp Feast in Gravy - 85 g Can (24 Pack)

Action? (c = categorize/split, s = skip, q = quit, default c):
There is more than one item in this transaction.
Split this transaction? (y/n, default n): y
```

## Generated Memos

### Single Item Transaction

```
Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
 https://www.amazon.ca/gp/your-account/order-details?ie=UTF8&orderID=702-8237239-0563450
```

### Split Transaction Main Memo

```
2 Items:
- Fancy Feast Grilled Wet Cat Food, Tuna Feast - 85 g Can (24 Pack)
- Fancy Feast Grilled Wet Cat Food, Salmon & Shrimp Feast in Gravy - 85 g Can (24 Pack)
```

## Security Notes

Never commit your `.env` file to version control.

- Credentials are loaded from environment variables or a `.env` file in the current working directory
- Your API key is never hardcoded in the script
- `.env` is listed in `.gitignore`

## Troubleshooting

### "No orders could be parsed"
- Make sure you're copying the full English Amazon orders page content
- Try copying from a different browser or clearing browser cache

### "API Key not found"
- Verify your `.env` file exists in the current working directory and has the correct format
- Check that your API key is valid in YNAB Developer Settings

### "No transactions found"
- Ensure you have uncategorized Amazon transactions in YNAB
- Check that the payee names contain `amazon`, `amzn`, or `amz`

### Emoji display issues
- Use `python -X utf8` on Windows if running directly via Python
- Ensure your terminal supports UTF-8 encoding

## Contributing & Maintenance

This repository is archived and no longer actively maintained. If you want to adapt or extend it for your own workflow, you are welcome to fork the repository under the GPL-3.0 license. Prospective maintainers can find setup, testing, and release instructions in [DEVELOPMENT.md](DEVELOPMENT.md).

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

Please respect YNAB's API terms of service when using this software.
