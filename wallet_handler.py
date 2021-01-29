import os
import logging 
import discord
import asyncio
import requests
from replit import db
from bs4 import BeautifulSoup
from set_ops import union,intersection,difference

import time

# minimum amount (in usd) to trigger update
SIG_CHANGE = 5000

def update_db(wallet_num,holdings_dict): 
  db[wallet_num] = holdings_dict

def get_wallet_nums(): 
  with open('wallets.txt') as f:
      return f.read().splitlines()

def wallet_exists(wallet_num): 
  if wallet_num in db: 
    return True
  else: 
    return False

def calc_token_diff(holding_1,holding_2,price): 
  # we need to put some sore of filter to catch bad data
  price = 0 if not price else price 

  unit_diff = float(holding_1) - float(holding_2) 
  usd_diff  = unit_diff * float(price)

  return unit_diff,usd_diff

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
      units = token[2].text.replace(',','').replace('...','')

      # added new dicttionary value to track usd value of coin
      usd_val = token[3].text[1:].replace(',','').split(' ')[0]

      holdings_dict.update({coin_name:[units, usd_val]})

  return holdings_dict

def detect_wallet_changes(wallet_num,curr_holdings):
  # wallet_diffs[key]: (unit_diff, usd_diff, change_stat)
  wallet_diffs = {}

  # stored_holdings[key]: [amount, usd_value]
  stored_holdings = db[wallet_num]

  holding_union = union(stored_holdings.keys(),curr_holdings.keys())
      
  holding_intersect = intersection(stored_holdings.keys(),curr_holdings.keys())
  holding_dump      = difference(stored_holdings.keys(),curr_holdings.keys())

  for key in holding_union: 
    if key in holding_intersect: 
      unit_diff,usd_diff = calc_token_diff(stored_holdings[key][0],curr_holdings[key][0],curr_holdings[key][1])
      change_stat = ':white_check_mark: ADDED' if unit_diff > 0 else ':no_entry_sign: REMOVED' 
    elif key in holding_dump: 
      unit_diff,usd_diff = calc_token_diff(stored_holdings[key][0],0,stored_holdings[key][1])
      change_stat = ':wastebasket: DUMPED'
    else: 
      unit_diff,usd_diff = calc_token_diff(curr_holdings[key][0],0,curr_holdings[key][1])
      change_stat = ':star: NEW BAG' 

    holding_diff = [unit_diff,usd_diff,change_stat]
    wallet_diffs.update({key:holding_diff})

  return wallet_diffs

async def scan_wallets(client):
  await client.wait_until_ready()
  channel = client.get_channel(int(os.getenv('CHANNEL')))

  while True:
    start_time = time.time()

    wallet_nums = get_wallet_nums()

    for wallet_num in wallet_nums:
      # create message to send to discord with wallet_num as author
      embed = discord.Embed()
      wallet_author = os.getenv('AUTHOR_URL') + wallet_num
      embed.set_author(name=wallet_num, url=wallet_author)

      num_changes = 0
      holdings_dict = get_wallet_holdings(wallet_num)

      if wallet_exists(wallet_num): 
        wallet_diffs = detect_wallet_changes(wallet_num,holdings_dict)

        for key in sorted(wallet_diffs.keys()):
          # difference in native units 
          diff_units = float(abs(wallet_diffs[key][0]))

          # difference in usd value
          diff_usd = float(abs(wallet_diffs[key][1]))

          # overall effect of the transactions to currency
          change_stat = wallet_diffs[key][2]

          if float(diff_usd) > SIG_CHANGE:
            # format commas, 2 floating points
            diff_units = f"{diff_units:,.2f}"
            diff_usd = f"{diff_usd:,.2f}"

            value_field = key + " " + diff_units + " " + " ($" + diff_usd + ")" 
            embed.add_field(name=change_stat, value=value_field,inline=False)
            num_changes += 1
        
        if num_changes > 0:
          await channel.send(embed=embed) 

      update_db(wallet_num,holdings_dict)
    print('total runtime: ' + str(time.time() - start_time))
    await asyncio.sleep(300)