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

import json,argparse,urllib2,shutil,os,subprocess,random
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
                'show_holdings_value_in_fiat': 'yes',
                'additional_btg': 0,
                'fiat_currency': 'AUD',
                'fiat_currency_symbol': '$',
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

    for config_key, config_section in cfg.iteritems():
        for key, value in config_section.iteritems():
            if value == 'yes':
                cfg[config_key][key] = True
            elif value == 'no':
                cfg[config_key][key] = False
    return cfg

def set_config_bulk(config_file,values):
    for key, value in values.iteritems():
        if type(value) == type(True):
            values[key] = 'yes'
        elif type(value) == type(False):
            values[key]

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
        cfg['c20_script'] = merge_two_dicts(cfg['c20_script'], values)
        ymlfile.seek(0)
        ymlfile.write( yaml.dump(cfg, default_flow_style=False))


def set_config(config_file,key,value):
    if type(value) == type(True):
        value = 'yes'
    elif type(value) == type(False):
        value = 'no'

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
    items = {
        'Coin Headers': 'show_coin_headers',
        'Dashboards Menu': 'show_dashboards',
        'Configuration Menu': 'show_configuration',
        'NAV (USD)': 'show_nav_usd',
        'NAV (USD) Seperator': 'show_nav_usd_seperator',
        'NAV (BTC)': 'show_nav_btc',
        'NAV (ETH)': 'show_nav_eth',
        'Holdings (USD)': 'show_holdings_usd',
        'Holdings (Fiat)': 'show_holdings_fiat',
        'Profit': 'show_profit',
        'Gain': 'show_gain',
        'Fund': 'show_fund',
        'Fund Coin Breakdown': 'show_fund_breakdown',
        'C20 Quantity': 'show_c20_quantity',
        'Market Cap': 'show_market_cap'
    }
    selected_items = []
    for key, value in items.iteritems():
        if config[value] == 'yes' or config[value] == True:
            selected_items.append(key)

    selected_items = selection_box_multiple("Customize View","Select Items to Show",items.keys(),selected_items,"Customize")

    config_items_selected = {}
    for key, value in items.iteritems():
        if key in selected_items:
            config_items_selected[value] = 'yes'
        else:
            config_items_selected[value] = 'no'

    set_config_bulk(config_file, config_items_selected)

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

def write_to_clipboard(output):
    process = subprocess.Popen(
        '/usr/bin/pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))

version,title,script_author,plugin_url = get_version()

parser = argparse.ArgumentParser(description=title)

parser.add_argument('--update', dest='perform_update', action='store_true', default=False, help='Perform an update of the C20 script')
parser.add_argument('--set-c20-token-amount', action='store_true', default=False)
parser.add_argument('--set-fiat-amount', action='store_true', default=False)
parser.add_argument('--set-fiat-currency', action='store_true', default=False)
parser.add_argument('--set-update-url', action='store_true', default=False)
parser.add_argument('--customize-view', action='store_true', default=False)
parser.add_argument('--verbose', '-v', action='store_true', default=False)
parser.add_argument('--quiet', '-q', action='store_true', default=False)
parser.add_argument('--version', action='version', version="%s %s" % (title,version))
parser.add_argument('--test', '-t', action='store_true', default=False)
parser.add_argument('--donate', '-d', action='store_true', default=False)
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
elif args.donate:
    donation_address = '0x23a30b86709438326333F599F03Ac8077Fa28bD3'
    if not args.quiet:
        print "Thank you for considering donation!"
        print "Ethereum or C20: %s" % donation_address
    write_to_clipboard(donation_address)
    ok_dialog("Thank you for donating!","Thank you so much for appreciating my hard work.\n\nMy Ethereum address has been copied to your clipboard or you can copy from here: %s" % donation_address,"ToolbarFavoritesIcon")
    exit()
elif args.customize_view:
    view_options = customize_view_options()
    print view_options
    exit()


# change this to the number of C20 tokens that you own
number_of_c20 = config['number_of_c20']

# change to the amount of fiat spent to acquire C20
fiat_spent_on_crypto = config['fiat_spent_on_crypto']

status_result = json.loads(urlopen(config['c20_status_url']).read())

top_25_result = None
if config['show_holdings_value_in_fiat']:
    top_25_result = json.loads(urlopen("https://api.coinmarketcap.com/v1/ticker/?convert=%s" % config['fiat_currency']).read())
else:
    top_25_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/?limit=25').read())

crypto_global_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/global/').read())
fiat_result = json.loads(urlopen("https://api.fixer.io/latest?symbols=%s&base=USD" % config['fiat_currency']).read())
eth_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/ethereum/?convert=USD').read())
btc_result = json.loads(urlopen('https://api.coinmarketcap.com/v1/ticker/bitcoin/?convert=USD').read())

# parse out price and put here
symbol_price = {}

# loop through prices rather than call api more than once
for c in top_25_result:
    if config['show_holdings_value_in_fiat']:
        key = 'price_' + config['fiat_currency'].lower()
        symbol_price[c['symbol']] = float(c[key])
    else:
        symbol_price[c['symbol']] = float(c['price_usd'])

holdings = []
for holding in status_result['holdings']:
    holdings.append(holding['name'])

symbol_image_map = get_coin_icons(holdings,icons_dir)
# We need to manually add in the C20 icon since it's not on livecoinwatch
symbol_image_map['C20'] = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAlCAYAAAAjt+tHAAAAAXNSR0IArs4c6QAAACBjSFJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAACXBIWXMAABYlAAAWJQFJUiTwAAADRGlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS40LjAiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iCiAgICAgICAgICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIgogICAgICAgICAgICB4bWxuczpleGlmPSJodHRwOi8vbnMuYWRvYmUuY29tL2V4aWYvMS4wLyI+CiAgICAgICAgIDx4bXA6TW9kaWZ5RGF0ZT4yMDE3LTExLTIwVDA3OjExOjYzPC94bXA6TW9kaWZ5RGF0ZT4KICAgICAgICAgPHhtcDpDcmVhdG9yVG9vbD5QaXhlbG1hdG9yIDMuNzwveG1wOkNyZWF0b3JUb29sPgogICAgICAgICA8dGlmZjpPcmllbnRhdGlvbj4xPC90aWZmOk9yaWVudGF0aW9uPgogICAgICAgICA8dGlmZjpSZXNvbHV0aW9uVW5pdD4yPC90aWZmOlJlc29sdXRpb25Vbml0PgogICAgICAgICA8dGlmZjpDb21wcmVzc2lvbj41PC90aWZmOkNvbXByZXNzaW9uPgogICAgICAgICA8ZXhpZjpQaXhlbFhEaW1lbnNpb24+Mjg8L2V4aWY6UGl4ZWxYRGltZW5zaW9uPgogICAgICAgICA8ZXhpZjpDb2xvclNwYWNlPjE8L2V4aWY6Q29sb3JTcGFjZT4KICAgICAgICAgPGV4aWY6UGl4ZWxZRGltZW5zaW9uPjMyPC9leGlmOlBpeGVsWURpbWVuc2lv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'
symbol_image_map['Golden_C20'] = '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'
symbol_image_map['Beer'] = 'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAAlwSFlzAAAWJQAAFiUBSVIk8AAABdlJREFUWAntV3tsU2UUP/f23nZsa6F7sO7BWjZChD2gLKIDNEJ0jhlDYmaiPBaDAvEZ4z8ucf5BUDTEuAQzJRKMhhiJiw8CEmOCU7aFLBEUZIUx2Ch7dKObo2s71t57ezxfu+7ebn3g/vYktz3f+c7j953vfC8OEhNvKSzfusiQ1iIKgjUQCJ4NBoONLteVPxKbAGRlrShSFJ3o8fQMkp6UTJf1cfEUVqyw5wKIx6rXr3265vENYM5aDE7nMJw+0xbo7ulvfujBkqbW1lZFa7t8uX2NKBo+sBYXbNDrReH2wMi1yUnvQafz4vdavZR8VVWVWFK6/nTzoWaU/G5EZRJR9iCGvDju6sc9u19Hq9XelF9UWZufX9FkKaqos9mqHli3bsvgd9+cQO/YAE7fdWFX+29YW1MvLbOt3ZYyqFbBYqmoa9ixFxUWfGoM0XdH/YITOHyjG+32LUr9Mw34WcvnuP25F7G42D545PCniOiP2DBb9GHX7224unzTBYAyvTZGUn6ppazl6y++ohHTyLXBo/y9cTz702l0O69TkCkcH+jFDdVb8VJXJ2JgQrUhEIF/hrD2yXqf2VxSnCiooO0oLa3aXJCfv9NuXwUQlLVdKq8osOWJTQAy9ft9kJVthjdf3QkFFiob6psljoOgJAMVrxQUQsFZ+RwmBkBQwoa3XttlWrW2AiBwD0DQUaAZpzri+ZmaxRCAjo985PDZHTTNEhV8CCMyCg6iCKe+PQMDgyPtfvet0TlxZ5sxADger3Wc/xNKVtooMIIpIw2s1gLgyOHI8CjcGfPQuom7cGYdMl1JkaC94wJ8efyHfkmS36ZOQhafYrxVVtZkeP2ej/OyDHsLc3jwyWZoPd4MxiUm2PPyuzDYfwnMJj1gQneRdX1jSALXmP+oXuDe6+u7cDt+6Ig0JgOXL//iN1mqj2226/YefMkI+w7LNNWUbopIcwlNOzPg4bIMkCg7iYjN0u5Dd8ExZPjEf/t80uDMRwwAJtBxvIGlMfJRm809zTfP05zTvsVThGgpMP25lKxvri5rzwPAhCzF6QYelKAXuq/1g7XYAqN33JR+AUJUaInHr052Tia/y5azycn8EZEJXu3u7myLNNXfhAAyM3jYUyfCgfc/hBDhrKsKwMoi4+yiUF3E4WgaaAGVUU8e66Vs8ojcK6tXbzzpcHS+o7WIC4ApyDTPT1Wnw/pVtJYlhMIcEy3zZGPXuCW1EU+o0T96/u+otLz80WW0jn+l/yNXrpwbiMrZxCYkVmy5SwQozhNp5GrqDSKrEdVMFDiqFbXNOB3HpWkl9fXnhmga7tLBkq2VJwXA9pq+YRnaLwXCAVhMti+d6ZqG6SCGQbDAXVeD0DsgzwOhDXTqVNUMRD4mjUkBCDSyi70SnGibAoHKm416KoDQctIHHh+GV4Og4+DHjmno7A4C0/+vlBQAc8ZWn0hBtEQbjLYZ3rFZthZCCzRbSKj4Nv8DWFAGYso4fmbvW5oSACs37ZoPt+fIWDStDmvPJaPRSLg5+kIxFZxwJ2QOJNoBN1booaJEpDMew/eNjDQO9r9gArORzgp2UNJmtXtrOiwy0D2A9oYoKSE+zi0I0zlOCER12H9SAOyCk02BcherFyO2LMttAgGKuAkRCGueLnxAMT56GmZn4ublSx8pimgh53Yr2+iQGwEYvxmRRX4TAoimmp2M7KqnzRvbDbVtFphR1IYxegGfp/xMRnrCvXSLhV0OB+1YGkoIgPmc8atRv0+WQLsmYJ/f3fFXKot5AHKNAA6nDA0HJ5JevRI5Zlm46ZKh0AzidXciLVU+D8DEPeTsK3XQuD0z5patmiTnWA0cOO6FvlGZYUlJ8wCgzPtZda8poccMe8+ohZ3SGZt7ZZoVLL1rJG4qtUGcVZBpELodt6SfG4/6aitLebqC3Y+biA4b/cUbCvQOKicLcjzXJxK+BlSfcdNksz22JMTJ+wUB31BVU3PkDOnB9FGaHg709HR6U1sA/AsvQ2xrbvwzBAAAAABJRU5ErkJggg=='
symbol_image_map['Coffee'] = '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'

# add on top of current nav
net_asset_value = float(status_result['nav_per_token'])
usd_value = net_asset_value * number_of_c20
net_asset_value_eth = net_asset_value / float(eth_result[0]['price_usd'])
net_asset_value_btc = net_asset_value / float(btc_result[0]['price_usd'])

# TODO: Implement Golden C20 icon function
golden_c20 = False

# menu bar icon
if golden_c20:
    print '| templateImage={}'.format(symbol_image_map['golden_c20'])
else:
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
        crypto_price = float(symbol_price[crypto_name])
        if config['show_holdings_value_in_fiat']:
            c20_value = int(holding['amount'] * crypto_price)
        else:
            c20_value = int(holding['value'])
        #crypto_path = symbol_path_map[crypto_name]
        crypto_img = symbol_image_map[crypto_name]

        print '{:s} \t{:.2f}%\t${:,}\t{:s}{:,.2f} | href=https://coinmarketcap.com/currencies/{} image={}'.format(
            crypto_name,
            crypto_percentage,
            c20_value,
            config['fiat_currency_symbol'],
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
    donate_number = random.randint(0, 2)
    if donate_number == 0:
        print "--Donate a Beer | refresh=false image=%s terminal=false bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (symbol_image_map['Beer'], sys.executable,__file__,"--donate")
    elif donate_number == 1:
        print "--Donate a Coffee | refresh=false image=%s terminal=false bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (symbol_image_map['Coffee'], sys.executable,__file__,"--donate")
    elif donate_number == 2:
        print "--Donate some Eth | refresh=false image=%s terminal=false bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (symbol_image_map['ETH'], sys.executable,__file__,"--donate")

    print "-----"
    print "--Set Token Amount | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-c20-token-amount")
    print "--Set Fiat Amount | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-fiat-amount")
    print "--Set Fiat Currency | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-fiat-currency")
    print "--Customize View | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--customize-view")
    #print "--Set Update URL | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--set-update-url")
    print "--Edit Config Manually | terminal=false bash=\"%s\" param1=\"%s\"" % ("/usr/bin/open",config_file)
    print "-----"
    print "--Refresh Plugin | refresh=true"
    print "--Update Plugin | terminal=false refresh=true bash=\"%s\" param1=\"%s\" param2=\"%s\"" % (sys.executable,__file__,"--update")
