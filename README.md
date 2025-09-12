# YNAB Amazon Categorizer

An enhanced Python package that automatically categorizes Amazon transactions in YNAB (You Need A Budget) with rich item information and automatic memo generation.

## Features

When you paste in the text from your Amazon order page:

🎯 **Smart Order Matching**: Automatically matches YNAB transactions with Amazon orders by amount and date  
📝 **Enhanced Memos**: Generates detailed memos with item names and direct Amazon order links  
🔄 **Intelligent Splitting**: Suggests splitting transactions with multiple items into separate categories  
⚡ **Streamlined Workflow**: Smart defaults and tab completion for fast categorization  
🌍 **UTF-8 Support**: Full emoji support in category names  
📊 **Rich Previews**: Shows category names and transaction details before updating  

## Prerequisites

- Python 3.7+
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

# Install in development mode
uv pip install -e .
```

## Configuration Setup

After installation, you'll need to set up your YNAB API credentials:

### Configuration File (.env)
Create a `.env` file in your working directory with your credentials:
```
YNAB_API_KEY=your_api_key_here
YNAB_BUDGET_ID=your_budget_id_here
YNAB_ACCOUNT_ID=none
```

### Alternative: Environment Variables
```bash
# Windows
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
3. Copy the budget_id part

### Account ID (Optional)
1. Click on a specific account in YNAB
2. Look at the URL: `https://app.ynab.com/[budget_id]/accounts/[account_id]`
3. Copy the account_id part (or leave as 'none' to process all accounts)

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

### Workflow
1. **Provide Amazon Orders Data** (optional but recommended):
   - Copy your Amazon orders page content
     - For example go to https://www.amazon.ca/gp/css/order-history?ref_=nav_orders_first and select all and copy the text
   - Run the tool and paste Amazon order info when prompted 
   - The script will automatically match transactions with orders

2. **Review Matched Transactions**:
   - The script shows order details, items, and links before asking to categorize
   - For multiple items, it suggests splitting the transaction

3. **Categorize Transactions**:
   - Use tab completion to select categories
   - Accept suggested memos or customize them
   - Confirm updates with enhanced previews

### Keyboard Shortcuts
- **Tab**: Auto-complete category names
- **Enter**: Accept defaults (categorize, use suggested memo, confirm update)
- **Alt+Enter**: Submit multiline input (Amazon orders data, custom memos)
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

⚠️ **Important**: Never commit your `.env` file to version control!

- The script loads credentials from environment variables or config file
- Your API key is never hardcoded in the script
- Add `.env` to your `.gitignore` if using git

## Troubleshooting

### "No orders could be parsed"
- Make sure you're copying the full Amazon orders page content
- Try copying from a different browser or clearing browser cache

### "API Key not found"
- Verify your `.env` file exists and has the correct format
- Check that your API key is valid in YNAB Developer Settings

### "No transactions found"
- Ensure you have uncategorized Amazon transactions in YNAB
- Check that the payee names contain "amazon", "amzn", or "amz"

### Emoji display issues
- Use `python -X utf8` on Windows for proper emoji support
- Ensure your terminal supports UTF-8 encoding

## Contributing

This package was developed to streamline YNAB Amazon transaction categorization. Feel free to suggest improvements or report issues!

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

Please respect YNAB's API terms of service when using this software.