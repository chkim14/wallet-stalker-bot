import os
import asyncio
import requests
from replit import db
from bs4 import BeautifulSoup

# minimum amount (in usd) to trigger update
SIG_CHANGE = 5000

def get_wallet_holdings(wallet_num):
  headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Firefox/50.0'}
  url = os.getenv('PREFIX_URL') + wallet_num + os.getenv('SUFFIX_URL')

  raw_html = requests.get(url, headers=headers).text
  parsed_html = BeautifulSoup(raw_html,'html.parser')

  # holdings_dict[coin_name]: [amount, usd_value]
  holdings_dict = {}
  for trgt_html in parsed_html.findAll('td',class_='clsShowAlert'):
    token = trgt_html.findAll('td', class_=None)
    if len(token) > 1:
      coin_name = token[1].text
      units = token[2].text.replace(',','')
      # added new dicttionary value to track usd value of coin
      usd_val = token[3].text[1:].replace(',','').split(' ')[0]
      holdings_dict.update({coin_name:[units, usd_val]})

  return holdings_dict

def wallet_exists(wallet_num): 
  if wallet_num in db: 
    return True
  else: 
    return False

def update_db(wallet_num,holdings_dict): 
  db[wallet_num] = holdings_dict
  print("update")

def detect_wallet_changes(wallet_num,curr_holdings):
  # wallet_diffs[key]: (diff_in_units, diff_in_usd)
  wallet_diffs = {}
  stored_holdings = db[wallet_num]
  # stored_holdings[key]: [amount, usd_value]
  for key in stored_holdings: 
    if key in curr_holdings:
      if float(curr_holdings[key][0]) != float(stored_holdings[key][0]):
        # store both diff in units and diff and usd
        diff_units = float(curr_holdings[key][0]) - float(stored_holdings[key][0])
        diff_usd = diff_units * float(curr_holdings[key][1])
        holding_diff = [diff_units, diff_usd]
        wallet_diffs.update({key:holding_diff})
      # wallet owner liquidated all of this coin
      elif key not in curr_holdings:
        print("liquidate coin: ", key, " ", stored_holdings[key][0])
        print(-float(stored_holdings[key][0]))
        # store both diff in units and diff and usd
        diff_units = -float(stored_holdings[key][0])
        diff_usd = -float(stored_holdings[key][0]) * float(stored_holdings[key][1])
        holding_diff = [diff_units, diff_usd]
        wallet_diffs.update({key:holding_diff})

  # check if wallet owner added new coin
  for key in curr_holdings:
    # wallet owner added new coin
    if key not in stored_holdings:
        print("new coin: ", key, " ", stored_holdings[key][0])
        # store both diff in units and diff and usd
        diff_units = float(curr_holdings[key][0])
        diff_usd = float(curr_holdings[key][0]) * float(curr_holdings[key][1])
        holding_diff = [diff_units, diff_usd]
        wallet_diffs.update({key:holding_diff})
  return wallet_diffs 

async def scan_wallets(client):
  await client.wait_until_ready()
  channel = client.get_channel(int(os.getenv('CHANNEL')))

  while True:
    print("loop")
    with open('wallets.txt') as f:
      ids = f.read().splitlines()
    for id in ids:
      holdings_dict = get_wallet_holdings(id)

      if wallet_exists(id): 
        wallet_diffs = detect_wallet_changes(id,holdings_dict)
        for key in wallet_diffs:
          print("loop")
          # difference in native units 
          diff_units = "{:.5f}".format(abs(wallet_diffs[key][0]))
          # difference in usd value
          diff_usd = "{:.2f}".format(abs(wallet_diffs[key][1]))
          if wallet_diffs[key][1] > SIG_CHANGE: 
            print("sending message")
            out_msg = '{}    :arrow_up: {}#{}, {}$USD'.format(id,diff_units,key,diff_usd)
            await channel.send(out_msg)
          elif wallet_diffs[key][1] < -SIG_CHANGE: 
            print("sending message")
            out_msg = '{}    :arrow_down: {}#{}, {}$USD'.format(id,diff_units,key,diff_usd)
            await channel.send(out_msg)
          else:
            # debug, remove line if works
            print(id, ": ", key, ": ", wallet_diffs[key][1])
          
          update_db(id,holdings_dict)
      else: 
        print("else")
        update_db(id,holdings_dict)

    await asyncio.sleep(300)