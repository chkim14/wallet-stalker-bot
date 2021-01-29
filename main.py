from replit import db
import discord 
import os 
from wallet_handler import scan_wallets,get_wallet_nums
from keep_alive import keep_alive

client = discord.Client()

@client.event
async def on_ready(): 
  print('Logged in as {0.user}'.format(client))

@client.event 
async def on_message(message): 
  if message.author == client.user: 
    return 

  if message.content.startswith('!add'): 
    if len(message.content.split('!add ')) > 1:
      new_wallet_num = message.content.split('!add ')[1]

      wallet_nums = get_wallet_nums()
      if new_wallet_num in wallet_nums: 
        await message.channel.send('Wallet id already exists!')
      else: 
        f = open("wallets.txt", "a")
        f.write(new_wallet_num + '\n')
        f.close()
        await message.channel.send('Wallet id added to database!')
    
    else: 
      await message.channel.send('Please add wallet id!')
  
  if message.content.startswith('!list'): 
    if len(message.content.split('!list ')) > 1: 
      ret_num = int(message.content.split('!list ')[1])
    else: 
      ret_num = 5

    ret_str = ''
    count = 1
    for key in list(db.keys())[:ret_num]: 
      ret_str += str(count) + '. ' + key + '\n'
      count+=1

    await message.channel.send(ret_str)

client.loop.create_task(scan_wallets(client))
keep_alive()
client.run(os.getenv('TOKEN'))