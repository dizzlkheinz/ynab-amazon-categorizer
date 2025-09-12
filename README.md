# YNAB Amazon Categorizer

An enhanced Python script that automatically categorizes Amazon transactions in YNAB (You Need A Budget) with rich item information and automatic memo generation.

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
- YNAB account with API access
- Required Python packages: `requests`, `prompt_toolkit`

## Installation

Choose one of the following installation methods:

### Method 1: Quick Install (Easiest - Recommended)

**Linux/Mac:**
```bash
curl -sSL https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/install.sh | bash
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest -Uri "https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/install.bat" -OutFile "install.bat"; .\install.bat
```

This will automatically:
- Download the executable for your platform
- Set up the configuration template
- Add the program to your PATH

### Method 2: Download Executable (No Python Required)

1. **Download the executable for your system:**
   - **Windows:** [ynab-amazon-categorizer.exe](https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/ynab-amazon-categorizer.exe)
   - **Linux:** [ynab-amazon-categorizer-linux](https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/ynab-amazon-categorizer-linux)
   - **macOS:** [ynab-amazon-categorizer-macos](https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/ynab-amazon-categorizer-macos)

2. **Download configuration template:** [.env.example](https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/.env.example)

3. **Set up configuration:** Rename `.env.example` to `.env` and edit with your credentials

### Method 3: Python Source Code (For Developers)

1. **Download source code:**
   ```bash
   # Download latest release
   curl -L -o ynab-amazon-categorizer.zip https://github.com/dizzlkheinz/ynab-amazon-categorizer/releases/latest/download/ynab-amazon-categorizer-source.zip
   unzip ynab-amazon-categorizer.zip
   ```

2. **Install required packages:**
   ```bash
   pip install requests prompt_toolkit
   ```

3. **Set up configuration:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Configuration Setup

After installation, you'll need to set up your YNAB API credentials:

### Configuration File (.env)
Edit your `.env` file with your credentials:
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

**If installed via Quick Install or Executable:**
```bash
# All platforms (executable)
ynab-amazon-categorizer
```

**If using Python source code:**
```bash
# Windows (with emoji support)
python -X utf8 ynab_amazon_categorizer.py

# Mac/Linux
python3 ynab_amazon_categorizer.py
```

### Workflow
1. **Provide Amazon Orders Data** (optional but recommended):
   - Copy your Amazon orders page content
     - For example go to https://www.amazon.ca/gp/css/order-history?ref_=nav_orders_first and select all and copy the text
   - Run ynab_amazon_categorizer.py and paste amazon order info when prompted 
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

This script was developed to streamline YNAB Amazon transaction categorization. Feel free to suggest improvements or report issues!

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

Please respect YNAB's API terms of service when using this software.