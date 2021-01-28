import os
import asyncio
import requests
from replit import db
from bs4 import BeautifulSoup

def get_wallet_holdings(wallet_num):
  headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:50.0) Firefox/50.0'}
  url = os.getenv('PREFIX_URL') + wallet_num + os.getenv('SUFFIX_URL')

  raw_html = requests.get(url, headers=headers).text
  parsed_html = BeautifulSoup(raw_html,'html.parser')

  holdings_dict = {}
  for trgt_html in parsed_html.findAll('td',class_='clsShowAlert'):
    token = trgt_html.findAll('td', class_=None)
    if len(token) > 1:
      coin_name = token[1].text
      units = token[2].text.replace(',','')
      holdings_dict.update({coin_name:units})

  return holdings_dict

def wallet_exists(wallet_num): 
  if wallet_num in db: 
    return True
  else: 
    return False

def update_db(wallet_num,holdings_dict): 
  db[wallet_num] = holdings_dict

def detect_wallet_changes(wallet_num,curr_holdings):
  wallet_diffs = {}
  stored_holdings = db[wallet_num]
  for key in stored_holdings: 
    if key in curr_holdings:
      if float(curr_holdings[key]) != float(stored_holdings[key]): 
        holding_diff = float(curr_holdings[key]) - float(stored_holdings[key])
        wallet_diffs.update({key:holding_diff})

  return wallet_diffs 

async def scan_wallets(client):
  await client.wait_until_ready()
  channel = client.get_channel(int(os.getenv('CHANNEL')))

  while True:
    with open('wallets.txt') as f:
      ids = f.read().splitlines()
    for id in ids:
      holdings_dict = get_wallet_holdings(id)

      if wallet_exists(id): 
        wallet_diffs = detect_wallet_changes(id,holdings_dict)
        for key in wallet_diffs: 
          amnt_diff = "{:.5f}".format(abs(wallet_diffs[key]))
          if wallet_diffs[key] > 0: 
            out_msg = '{}    :arrow_up: {}#{}'.format(id,amnt_diff,key)
          else: 
            out_msg = '{}    :arrow_down: {}#{}'.format(id,amnt_diff,key)
          await channel.send(out_msg)
          update_db(id,holdings_dict)
      else: 
        update_db(id,holdings_dict)

    await asyncio.sleep(300)