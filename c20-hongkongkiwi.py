#!/usr/local/bin/python2

# <bitbar.title>Crypto20 BitBar Plugin</bitbar.title>
# <bitbar.version>v0.1</bitbar.version>
# <bitbar.author>Andy Savage</bitbar.author>
# <bitbar.author.github>hongkongkiwi</bitbar.author.github>
# <bitbar.desc>Plugin to show information from the Crypto20 Index Fund. This is hongkongkiwi's version.</bitbar.desc>
# <bitbar.image>https://static.crypto20.com/images/icons/c20-alt-2-darkblue.png</bitbar.image>
# <bitbar.dependencies>python</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/hongkongkiwi/bitbar-c20</bitbar.abouturl>

# To use this script, download and save. Using Terminal.app, change to the
# directory where you saved this file. For example, if you saved to your
# Downloads folder you will type:
#
#   cd ~/Downloads
#
# Then make this script executable by typing:
#
#   chmod +x c20.py
#
# Get BitBar from https://getbitbar.com (currently BitBar-v1.9.2.zip) and run
# it. You will be prompted for a Plugins directory. Set this to the folder where
# you saved c20.py, such as your Downloads folder and you are done.
#

import json,argparse,urllib2,shutil,os,subprocess
import re,sys,errno,time,ConfigParser,yaml,base64,string

from datetime import datetime,timedelta
from urllib import urlopen
from tempfile import NamedTemporaryFile

bitbarc20_dir = "%s/.bitbar_c20" % os.environ.get('HOME')
icons_dir = "%s/cache/icons" % bitbarc20_dir
config_file = "%s/config.yml" % bitbarc20_dir

default_config = {
            'c20_script': {
                'number_of_c20': 1,
                'show_coin_headers': 'yes',
                'show_dashboards': 'yes',
                'show_configuration': 'yes',
                'show_top_icon_color': 'yes',
                'show_nav_usd': 'yes',
                'show_nav_usd_seperator': 'yes',
                'show_nav_btc': 'yes',
                'show_nav_eth': 'yes',
                'show_holdings_usd': 'yes',
                'show_holdings_fiat': 'yes',
                'show_profit': 'yes',
                'show_gain': 'yes',
                'show_fund': 'yes',
                'show_fund_breakdown': 'yes',
                'show_c20_quantity': 'yes',
                'show_market_cap': 'yes',
                'additional_btg': 0,
                'fiat_currency': 'AUD',
                'fiat_spent_on_crypto': 1,
                'c20_status_url': 'https://crypto20.com/status',
                'hide_images_in_terminal': 'yes',
                'hide_url_in_terminal': 'yes',
                'plugin_update_url': 'https://raw.githubusercontent.com/hongkongkiwi/bitbar-c20/master/c20_hongkongkiwi.py',
                'crypto20_contract_address': '0x26e75307fc0c021472feb8f727839531f112f317'
            }
        }

def etherscan_get_tokens(crypto20_address, eth_address):
    opener = urllib2.build_opener()
    # Fake our UserAgent so we can easily pull the tokens from the html
    opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36')]
    url = "https://etherscan.io/token/%s?a=%s" % (crypto20_address,eth_address)
    response = opener.open(url)
    html = response.read()
    c20_token_match = re.search("<td>Token Balance:\n?</td>\n?<td>\n?(.*) C20\n?</td>\n?</tr>", html)
    if not c20_token_match:
        return float(0.0)
    tokens = float(c20_token_match.group(1).replace(',',''))
    return tokens

# This function scans this script to pull the meta info from the comments
def get_version():
    version = None
    title = None
    script_author = None
    plugin_url = None
    with open(__file__, "r") as c20_script:
        for line in c20_script:
            # Skip over comment lines
            if line[0] != "#":
                continue

            version_match = re.search("<bitbar\.version>(.+)</bitbar\.version>", line)
            title_match = re.search("<bitbar\.title>(.+)</bitbar\.title>", line)
            script_author_match = re.search("<bitbar\.author>(.+)</bitbar\.author>", line)
            plugin_url_match = re.search("<bitbar\.abouturl>(.+)</bitbar\.abouturl>", line)
            if version_match:
                version = version_match.group(1)
                continue
            if title_match:
                title = title_match.group(1)
                continue
            if script_author_match:
                script_author = script_author_match.group(1)
                continue
            if plugin_url_match:
                plugin_url = plugin_url_match.group(1)
                continue
            if version and title and script_author and plugin_url:
                break

    return version,title,script_author,plugin_url

def is_bitbar_dark_mode():
    return os.environ.get('BitBarDarkMode') is not None

def is_bitbar():
    print os.environ.get('BitBar')
    return os.environ.get('BitBar') is not None

def merge_two_dicts(x, y):
    if not x:
        x = {}
    if not y:
        y = {}

    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def make_dir_if_not_exist(dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def is_non_zero_file(fpath):
    return os.path.isfile(fpath) and os.path.getsize(fpath) > 0

def get_coin_icons(coins,icon_dir,icon_size=32,force=False):
    make_dir_if_not_exist(icon_dir)
    output = {}
    for coin in coins:
        data = None
        coin_name = coin.lower().strip()
        output_filename = "%s/%s%d.png" % (icon_dir,coin_name,int(icon_size))
        if not is_non_zero_file(output_filename) or force:
            opener = urllib2.build_opener()
            # Fake our UserAgent so we can easily pull the tokens from the html
            opener.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36')]
            if icon_size <> 32:
                url = "https://images.weserv.nl/?url=www.livecoinwatch.com/images/icons32/%s.png&w=%d&h=%d" % (coin_name,icon_size,icon_size)
            else:
                url = "https://www.livecoinwatch.com/images/icons32/%s.png" % (coin_name)

            try:
                response = opener.open(url)
                with open(output_filename, "w") as f:
                    data = response.read()
                    f.write(data)
                # We need to change the DPI of the image to support retina screens
                proc = subprocess.Popen(["/usr/bin/sips",'-s','dpiHeight','144','-s','dpiWidth','144',output_filename], stdout=subprocess.PIPE, shell=False)
                #(out, err) = proc.communicate()
            except urllib2.HTTPError:
                print 'Could not download ' + coin_name
        else:
            with open(output_filename, "rb") as f:
                data = f.read()
        output[coin_name.upper()] = base64.b64encode(data)
    return output

# This method opens a config file and ensures that all our required config values are there
def get_config(config_file,default_cfg):
    # make config dir if it doesn't exist
    make_dir_if_not_exist(os.path.dirname(config_file))
    # Read our config
    with open(config_file, 'a+') as ymlfile:
        # since we are opening with a+ we must seek to beginning
        ymlfile.seek(0)
        try:
            cfg = yaml.load(ymlfile)
        except yaml.YAMLError as exc:
            print(exc)
            cfg = None

    # Handle blank config file case
    if not cfg:
        cfg = {}

    updated = False
    for config_section in default_cfg:
        if not config_section in cfg or not all (k in cfg[config_section] for k in (default_cfg.keys())):
            if config_section in cfg:
                cfg[config_section] = merge_two_dicts(default_cfg[config_section], cfg[config_section])
                updated = True
            else:
                cfg[config_section] = default_cfg[config_section]
                updated = True

    if updated:
        with open(config_file, 'w+') as ymlfile:
            ymlfile.seek(0)
            ymlfile.write( yaml.dump(cfg, default_flow_style=False))

    return cfg

def set_config(config_file,key,value):
    # Read our config
    with open(config_file, 'a+') as ymlfile:
        # since we are opening with a+ we must seek to beginning
        ymlfile.seek(0)
        try:
            cfg = yaml.load(ymlfile)
        except yaml.YAMLError as exc:
            print(exc)
            cfg = {}
    with open(config_file, 'w+') as ymlfile:
        cfg['c20_script'][key] = value
        ymlfile.seek(0)
        ymlfile.write( yaml.dump(cfg, default_flow_style=False))

def ok_dialog(title,msg,icon):
    dialog = "tell application \"System Events\"\n"
    dialog += "activate\n"
    dialog += "display dialog \"%s\" buttons [\"OK\"] with title \"%s\" default button \"OK\" with icon file \":System:Library:CoreServices:CoreTypes.bundle:Contents:Resources:%s.icns\"\n" % (str(msg),str(title),str(icon))
    dialog += "end tell\n"
    proc = subprocess.Popen(["/usr/bin/osascript", '-e',dialog], stdout=subprocess.PIPE, shell=False)
    (out, err) = proc.communicate()
    return out

def input_dialog(title,msg,default_text,icon,buttons,default_button):
    dialog = "tell application \"System Events\"\n"
    dialog += "activate\n"
    dialog += "display dialog \"%s\" with title \"%s\" default answer \"%s\" with icon file \":System:Library:CoreServices:CoreTypes.bundle:Contents:Resources:%s.icns\" buttons {%s} default button \"%s\"\n" % (str(msg),str(title),str(default_text),str(icon),'"' + '","'.join(buttons) + '"',buttons[default_button])
    dialog += "end tell\n"
    proc = subprocess.Popen(["/usr/bin/osascript", '-e',dialog], stdout=subprocess.PIPE, shell=False)
    (out, err) = proc.communicate()
    button_pressed = out.split(', ')[0].split(':')[1]
    value_typed = out.split(', ')[1].split(':')[1].replace("\n",'')
    button_pressed = int(buttons.index(button_pressed))
    if button_pressed == 0:
        value_typed = 0
    return button_pressed, value_typed

def selection_box_multiple(title,msg,items,default_items,set_button_name):
    dialog = "tell application \"System Events\"\n"
    dialog += "activate\n"
    dialog += "choose from list {%s} with prompt \"%s\" OK button name \"%s\" with multiple selections allowed with title \"%s\" default items {%s}\n" % ('"' + '","'.join(items) + '"', msg, set_button_name, title, '"' + '","'.join(default_items) + '"')
    dialog += "end tell\n"
    proc = subprocess.Popen(["/usr/bin/osascript", '-e',dialog], stdout=subprocess.PIPE, shell=False)
    (out, err) = proc.communicate()
    out = out.replace("\n",'')
    return out.split(', ')
    # if out == 'false':
    #     return None
    # else:
    #     return int(items.index(out))

def customize_view_options():
    items = [
        'Coin Headers',
        'Dashboards Menu',
        'Configuration Menu',
        'NAV (USD)',
        'NAV (USD) Seperator',
        'NAV (BTC)',
        'NAV (ETH)',
        'Holdings (USD)',
        'Holdings (Fiat)',
        'Profit',
        'Gain',
        'Fund',
        'Fund Coin Breakdown',
        'C20 Quantity',
        'Market Cap',
        'Colour Icons'
    ]
    print selection_box_multiple("Customize View","Select Items to Show",items,items,"Customize")

def selection_box(title,msg,items,default_item,set_button_name):
    dialog = "tell application \"System Events\"\n"
    dialog += "activate\n"
    dialog += "choose from list {%s} with prompt \"%s\" OK button name \"%s\" with title \"%s\" default items \"%s\"\n" % ('"' + '","'.join(items) + '"', msg, set_button_name, title, items[default_item])
    dialog += "end tell\n"
    proc = subprocess.Popen(["/usr/bin/osascript", '-e',dialog], stdout=subprocess.PIPE, shell=False)
    (out, err) = proc.communicate()
    out = out.replace("\n",'')
    if out == 'false':
        return None
    else:
        return int(items.index(out))

def remote_update(url, local_file):
    req = urllib2.Request(url)

    try:
        r = urllib2.urlopen(req)
    except urllib2.HTTPError as e:
        # Need to check its an 404, 503, 500, 403 etc.
        status_code = e.code
        exit("Failed to Update File! Status Code: %s" % status_code)

    f = NamedTemporaryFile(delete=False)
    #f = open(t.name, 'wb')
    meta = r.info()
    remote_file_size = int(meta.getheaders("Content-Length")[0])

    if args.verbose and not args.quiet:
        print "Downloading: %s Bytes: %s" % (local_file, remote_file_size)

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = r.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / remote_file_size)
        status = status + chr(8)*(len(status)+1)
        if args.verbose and not args.quiet:
            print status,

    if args.verbose and not args.quiet:
        print "\n"
    f.close()
    if args.test:
        if not args.quiet:
            print "# We are in test mode so we will not actually update"
        os.remove(f.name)
    else:
        shutil.move(f.name, "%s/test.py" % os.path.dirname(__file__))
    if not args.quiet:
        print "Update is complete!"

def set_c20_token_amount(existing_amount):
    buttons = ["Cancal", "Set Tokens"]
    button_pressed, value = input_dialog("C20 Token Amount", "Please enter the amount of C20 tokens you own.\nYou may also enter an ethereum address here where your C20 tokens are stored.", existing_amount, "SidebarDropboxFolder", buttons, 1)
    if button_pressed == 0:
        exit()

    # Check whether the return value is an ethereum address
    if value[:2] == '0x' and len(value) == 42:
        value = etherscan_get_tokens(config['crypto20_contract_address'], value)
    try:
        value = float(value)
    except ValueError:
        value = 0
    set_config(config_file,'number_of_c20',value)
    exit()

def set_update_url():
    buttons = ["Cancal", "Set Update Url"]
    button_pressed, value = input_dialog("C20 Update URL", "Please enter an update URL", 1, "SidebarDropboxFolder", buttons, 1)
    if button_pressed == 1:
        print "Update URL: %d" % value
    exit()

def set_fiat_amount(existing_amount):
    buttons = ["Cancal", "Set Fiat Amount"]
    button_pressed, value = input_dialog("Fiat Spent Amount", "Please enter the amount of Fiat that you spent", str(existing_amount), "SidebarAirportExpress", buttons, 1)
    if button_pressed == 1:
        set_config(config_file,'fiat_spent_on_crypto',float(value))
    exit()

def set_fiat_currency(existing_currency):
    items = ["AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB", "TRY", "TWD", "ZAR"]
    try:
        default_item = items.index(existing_currency)
    except ValueError as e:
        default_item = 0

    selection = selection_box("Select Fiat Currency","Pleae choose your fiat display currency",items,default_item,"Set Currency")
    if selection != None:
        item = items[selection]
        set_config(config_file,'fiat_currency',item)
    exit()

version,title,script_author,plugin_url = get_version()

parser = argparse.ArgumentParser(description=title)

parser.add_argument('--update', dest='perform_update', action='store_true', default=False, help='Perform an update of the C20 script')
parser.add_argument('--set-c20-token-amount', action='store_true', default=False)
parser.add_argument('--set-fiat-amount', action='store_true', default=False)
parser.add_argument('--set-fiat-currency', action='store_true', default=False)
parser.add_argument('--set-update-url', action='store_true', default=False)
parser.add_argument('--verbose', '-v', action='store_true', default=False)
parser.add_argument('--quiet', '-q', action='store_true', default=False)
parser.add_argument('--version', action='version', version="%s %s" % (title,version))
parser.add_argument('--test', '-t', action='store_true', default=False)
args = parser.parse_args()

config = get_config(config_file,default_config)['c20_script']

if args.set_c20_token_amount:
    set_c20_token_amount(config['number_of_c20'])
    exit()
elif args.set_fiat_amount:
    set_fiat_amount(config['fiat_spent_on_crypto'])
    exit()
elif args.set_fiat_currency:
    set_fiat_currency(config['fiat_currency'])
    exit()
elif args.set_update_url:
    print "Not Implemented"
    exit()
elif args.perform_update:
    if not args.quiet:
        print "Updating BitBar Script"
    remote_update(config['plugin_update_url'],__file__)
    ok_dialog("C20 BitBar Script", "Update to latest version was successful!", "NetBootVolume")
    exit()

# change this to the number of C20 tokens that you own
number_of_c20 = config['number_of_c20']

# change to the amount of fiat spent to acquire C20
fiat_spent_on_crypto = config['fiat_spent_on_crypto']

status_result = json.loads(urlopen(config['c20_status_url']).read())
top_25_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/?limit=25').read())
crypto_global_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/global/').read())
fiat_result = json.loads(urlopen("https://api.fixer.io/latest?symbols=%s&base=USD" % config['fiat_currency']).read())
eth_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/ethereum/?convert=USD').read())
btc_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert=USD').read())

# parse out price and put here
symbol_price = {}

# loop through prices rather than call api more than once
for c in top_25_result:
    symbol_price[c['symbol']] = float(c['price_usd'])

holdings = []
for holding in status_result['holdings']:
    holdings.append(holding['name'])

symbol_image_map = get_coin_icons(holdings,icons_dir)
# We need to manually add in the C20 icon since it's not on livecoinwatch
symbol_image_map['C20'] = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAlCAYAAAAjt+tHAAAAAXNSR0IArs4c6QAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAACXBIWXMAABYlAAAWJQFJUiTwAAADRGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS40LjAiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iCiAgICAgICAgICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIgogICAgICAgICAgICB4bWxuczpleGlmPSJodHRwOi8vbnMuYWRvYmUuY29tL2V4aWYvMS4wLyI+CiAgICAgICAgIDx4bXA6TW9kaWZ5RGF0ZT4yMDE3LTExLTIwVDA3OjExOjYzPC94bXA6TW9kaWZ5RGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5QaXhlbG1hdG9yIDMuNzwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICAgICA8dGlmZjpSZXNvbHV0aW9uVW5pdD4yPC90aWZmOlJlc29sdXRpb25Vbml0PgogICAgICAgICA8dGlmZjpDb21wcmVzc2lvbj41PC90aWZmOkNvbXByZXNzaW9uPgogICAgICAgICA8ZXhpZjpQaXhlbFhEaW1lbnNpb24+Mjg8L2V4aWY6UGl4ZWxYRGltZW5zaW9uPgogICAgICAgICA8ZXhpZjpDb2xvclNwYWNlPjE8L2V4aWY6Q29sb3JTcGFjZT4KICAgICAgICAgPGV4aWY6UGl4ZWxZRGltZW5zaW9uPjMyPC9leGlmOlBpeGVsWURpbWVuc2lv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'

# symbol to name map
# symbol_path_map = {
#     'BTC': 'bitcoin',
#     'ETH': 'ethereum',
#     'BCH': 'bitcoin-cash',
#     'XRP': 'ripple',
#     'DASH': 'dash',
#     'LTC': 'litecoin',
#     'MIOTA': 'iota',
#     'XMR': 'monero',
#     'NEO': 'neo',
#     'XEM': 'nem',
#     'ETC': 'ethereum-classic',
#     'LSK': 'lisk',
#     'QTUM': 'qtum',
#     'EOS': 'eos',
#     'ZEC': 'zcash',
#     'OMG': 'omisego',
#     'ADA': 'cardano',
#     'HSR': 'hshare',
#     'XLM': 'stellar',
#     'WAVES': 'waves',
#     'PPT': 'populous',
#     'STRAT': 'stratis',
#     'BTS': 'bitshares',
#     'ARK': 'ark',
#     'BTG': 'bitcoin-gold'
# }

# add on top of current nav
net_asset_value = float(status_result['nav_per_token'])
usd_value = net_asset_value * number_of_c20
net_asset_value_eth = net_asset_value / float(eth_result[0]['price_usd'])
net_asset_value_btc = net_asset_value / float(btc_result[0]['price_usd'])

# menu bar icon
print '| templateImage={}'.format(symbol_image_map['C20'])
print '---'

# print nav, value of your coins, and total fund value
fiat_value = fiat_result['rates'][config['fiat_currency']] * usd_value
fiat_profit = fiat_value - fiat_spent_on_crypto
gain = (fiat_value - fiat_spent_on_crypto) / fiat_spent_on_crypto * 100
if config['show_nav_usd']:
    print 'NAV:\t\t${:.4f} | color=#000'.format(net_asset_value)
if config['show_nav_btc']:
    print 'NAV (BTC):\t{:,.8f} | color=#000'.format(net_asset_value_btc)
if config['show_nav_eth']:
    print 'NAV (ETH):\t{:,.18f} | color=#000'.format(net_asset_value_eth)
if config['show_nav_usd_seperator']:
    print "---"
if config['show_holdings_usd']:
    print 'Holdings:\t${:,} | href=https://crypto20.com/users/'.format(int(usd_value))
if config['show_holdings_fiat']:
    print 'Holdings:\t${:,} {} | href=https://crypto20.com/users/'.format(int(fiat_value),str(config['fiat_currency']))
if config['show_profit']:
    print 'Profit:\t\t${:,} {} | href=https://crypto20.com/users/'.format(int(fiat_profit),str(config['fiat_currency']))
if config['show_gain']:
    print 'Gain:\t\t{:,.3f}% | href=https://percentagecalculator.net/'.format(gain)
if config['show_fund']:
    print 'Fund:\t\t${:,} | href=https://crypto20.com/portal/insights/'.format(int(status_result['usd_value']))

if config['show_c20_quantity']:
    # print number of c20 you have
    print 'C20: \t{:,.4f} | href=https://crypto20.com/users/ image={}'.format(number_of_c20, symbol_image_map['C20'])

if config['show_market_cap']:
    # print total crypto market cap
    print 'Market Cap:\t${:,} | href=https://livecoinwatch.com'.format(int(crypto_global_result['total_market_cap_usd']))

if config['show_fund_breakdown']:
    # separator bitbar recognizes and puts everything under it into a menu
    print '---'
    if config['show_coin_headers']:
        print "Name\t\t%\t\tAmount\t\tCoin Price"

    # print holdings
    holdings = status_result['holdings'];
    for holding in holdings:
        crypto_name = holding['name'].upper().strip()
        crypto_full_name = holding['full_name'].replace(' ','').lower()
        crypto_value = float(holding['value'])
        crypto_percentage = crypto_value / float(status_result['usd_value']) * 100
        c20_value = holding['value']
        #crypto_path = symbol_path_map[crypto_name]
        crypto_img = symbol_image_map[crypto_name]
        crypto_price = float(symbol_price[crypto_name])

        print '{:s} \t{:.2f}%\t${:,}\t${:,.2f} | href=https://coinmarketcap.com/currencies/{} image={}'.format(
            crypto_name,
            crypto_percentage,
            c20_value,
            crypto_price,
            crypto_full_name,
            crypto_img)

if config['show_dashboards']:
    print "---"
    print "Dashboards"
    print "--youcan.dance/crypto20 | href=http://youcan.dance/crypto20"
    print "--cryptodash1.firebaseapp | href=https://cryptodash1.firebaseapp.com/"
if config['show_configuration']:
    print "---"
    print "Configuration"
    print "--Plugin Version: %s | href=%s" % (version,plugin_url)
    print "-----"
    print "--Set Token Amount | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-c20-token-amount")
    print "--Set Fiat Amount | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-fiat-amount")
    print "--Set Fiat Currency | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-fiat-currency")
    print "--Customize View | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-custom-view")
    #print "--Set Update URL | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-update-url")
    print "--Edit Config Manually | terminal=false bash=\"%s\" param1=\"%s\"" % ("/usr/bin/open",config_file)
    print "-----"
    print "--Refresh Plugin | refresh=true"
    print "--Update Plugin | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--update")
