# Stonks
![image](https://github.com/user-attachments/assets/e0089ccf-7a6d-4d85-808e-b90e7eefb4c0)

This project is a cron-job based crawler for selected stock values.

As some symbols/tickers require פליקפלקים באוויר (a phrase in Hebrew means a lot of effort) in order to be fetched, I created this as a one-stop-shop project as a source of stocks information for my Google Sheets investment portfolio document.

Created for personal use. I'm not responsible for any financial loss you may incur by using this project. Use at your own risk.



## Fork it.
I would recommend you to fork this repo to customize it to whatever symbols you're interested in.

The project is set up to be deployed on GitHub Pages. The `main.py` script is scheduled to run every hour using GitHub Actions. The results are published to GitHub Pages every time.

The script looks under the `/symbols` dir, you can find the `.json` files I'm tracking for reference. Each file should contain the following-ish structure:
```json
{
  "id": "ZPRX",
  "type": "etf",
  "source": "justetf",
  "symbol": "IE00BSPLC298",
  "currency": "EUR"
}
```
- The `type` field hints the `main.py` script on how to scrape the symbol values.

Take a look at the `main.py` script to understand how the values are being fetched and stored. You can customize it to your needs to scrape more resources.

To make GitHub Actions work in your forked repository:

First, you'll need to enable GitHub Actions in your fork:
Go to your repository's "Settings" tab
Navigate to "Actions" under "Code and automation"
Select "Allow all actions and reusable workflows"

You'll need to set up GitHub Pages:
In repository settings, go to "Pages"
Under "Source", select "GitHub Actions"
To run the GitHub Actions workflow immediately without waiting for the scheduled time, you can trigger it manually through the GitHub interface:

To run the action manually, go to your repository on GitHub
Click on the "Actions" tab
Select the "cron" workflow (or whatever name you gave it)
Click the "Run workflow" button (it's a dropdown button on the right side)
Click "Run workflow" in the dropdown menu

Since we included workflow_dispatch in the workflow file, this manual trigger option is available. You can then watch the workflow run in real-time and see if there are any errors or if it completes successfully.
The script will process all the JSON files in your symbols directory according to the code. Make sure your JSON files are properly formatted and in the right location before running the workflow.

### URLs
Once your project is deployed on GitHub Pages, the symbol value can be accessed with the following convention:
- symbol recent price - `https://<github username>.github.io/stonks/<symbol id>/price`
- symbol price date - `https://<github username>.github.io/stonks/<symbol id>/date`
- symbol price currency - `https://<github username>.github.io/stonks/<symbol id>/currency`
- general symbol info json - `https://<github username>.github.io/stonks/<symbol id>/info.json`

Let's take the ZPRX symbol for example:
- recent price - https://jossef.github.io/stonks/ZPRX/price
- price date - https://jossef.github.io/stonks/ZPRX/date
- price currency - https://jossef.github.io/stonks/ZPRX/currency
- general symbol info json - https://jossef.github.io/stonks/ZPRX/info.json

### Google Sheets Integration

Within your Google sheets document, you can use the `IMPORTDATA` function to fetch the data from the URLs above.

```
=IMPORTDATA("https://jossef.github.io/stonks/ZPRX/price")
```

or if you want to keep your symbols in a separate column, you can use the `CONCATENATE` function to build the URL dynamically.
```
=IMPORTDATA(CONCATENATE("https://jossef.github.io/stonks/",A2,"/price"))
```


💡 Note - You are expected to see a warning for security reasons, supress it with "Allow access" in Google Sheets to allow the use of `IMPORTDATA` and fetch data from external URLs 

![image](https://github.com/user-attachments/assets/6a631429-9418-4962-9d5a-3f8910334d9c)

### Demo

I created this example spreadsheet: https://docs.google.com/spreadsheets/d/1bo6MEyI9WHOUDB5q21C4e9LLOmTX-fih-JIJPEGJE_Y/edit?usp=sharing

![image](https://github.com/user-attachments/assets/cddf7155-e575-46d2-9929-4c781bfcdd91)

## Short URLs
This is totally optional. I decided to set my GitHub pages deployment with a custom `CNAME` to shorten the URLs. I own the domain `jossef.com` and hooked this up to my subdomain `stonks.jossef.com`.

- From this: https://jossef.github.io/stonks/ZPRX/price
- To this: https://stonks.jossef.com/ZPRX/price


As I always like to say, if it looks stupid but it works, it ain't stupid.
